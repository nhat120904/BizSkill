from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.db.models.channel import Channel
from app.db.models.video import Video
from app.db.models.segment import Segment
from app.core.security import get_admin_user
from app.schemas import ChannelCreate, ChannelResponse
from app.services.youtube_service import YouTubeService

router = APIRouter()


@router.get("", response_model=List[ChannelResponse])
async def list_channels(
    skip: int = 0,
    limit: int = 50,
    whitelisted_only: bool = False,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """List all channels (admin only)"""
    query = db.query(Channel)
    
    if whitelisted_only:
        query = query.filter(Channel.is_active == True)
    
    channels = query.order_by(Channel.created_at.desc()).offset(skip).limit(limit).all()
    
    # Add counts
    results = []
    for channel in channels:
        video_count = db.query(Video).filter(Video.channel_id == channel.id).count()
        segment_count = db.query(Segment).join(Video).filter(Video.channel_id == channel.id).count()
        
        channel_dict = {
            "id": channel.id,
            "youtube_channel_id": channel.youtube_channel_id,
            "name": channel.name,
            "description": channel.description,
            "thumbnail_url": channel.thumbnail_url,
            "custom_url": channel.custom_url,
            "subscriber_count": channel.subscriber_count,
            "is_active": channel.is_active,
            "last_synced_at": channel.last_synced_at,
            "created_at": channel.created_at,
            "video_count": video_count,
            "segment_count": segment_count,
        }
        results.append(channel_dict)
    
    return results


@router.post("", response_model=ChannelResponse)
async def add_channel(
    channel_data: ChannelCreate,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Add a new channel to monitor (admin only)"""
    youtube = YouTubeService()
    
    # Fetch channel info
    if channel_data.youtube_channel_id:
        channel_info = youtube.get_channel_info(channel_data.youtube_channel_id)
    elif channel_data.handle:
        channel_info = youtube.get_channel_by_handle(channel_data.handle)
    else:
        raise HTTPException(
            status_code=400, 
            detail="Either youtube_channel_id or handle must be provided"
        )
    
    if not channel_info:
        raise HTTPException(status_code=404, detail="Channel not found on YouTube")
    
    # Check if already exists
    existing = db.query(Channel).filter(
        Channel.youtube_channel_id == channel_info['youtube_channel_id']
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Channel already exists")
    
    # Create channel
    channel = Channel(
        youtube_channel_id=channel_info['youtube_channel_id'],
        name=channel_info['name'],
        description=channel_info.get('description'),
        thumbnail_url=channel_info.get('thumbnail_url'),
        custom_url=channel_info.get('custom_url'),
        subscriber_count=channel_info.get('subscriber_count'),
        is_active=True
    )
    
    db.add(channel)
    db.commit()
    db.refresh(channel)
    
    return channel


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Get channel details (admin only)"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    video_count = db.query(Video).filter(Video.channel_id == channel.id).count()
    segment_count = db.query(Segment).join(Video).filter(Video.channel_id == channel.id).count()
    
    return {
        **channel.__dict__,
        "video_count": video_count,
        "segment_count": segment_count,
    }


@router.put("/{channel_id}/whitelist")
async def toggle_whitelist(
    channel_id: str,
    whitelisted: bool,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Toggle channel whitelist status (admin only)"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    channel.is_active = whitelisted
    db.commit()
    
    return {"status": "success", "is_active": whitelisted}


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Delete a channel and all its content (admin only)"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    db.delete(channel)
    db.commit()
    
    return {"status": "deleted"}


@router.post("/{channel_id}/poll")
async def poll_channel_now(
    channel_id: str,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Trigger immediate channel poll (admin only)"""
    from app.workers.tasks import poll_channel
    
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    task = poll_channel.delay(channel_id)
    
    return {"status": "queued", "task_id": task.id}

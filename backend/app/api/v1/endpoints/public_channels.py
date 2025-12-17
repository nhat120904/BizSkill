"""
Public channel endpoints - no authentication required
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.db.models.channel import Channel
from app.db.models.video import Video
from app.db.models.segment import Segment
from pydantic import BaseModel
from datetime import datetime


router = APIRouter()


class PublicChannelResponse(BaseModel):
    id: str
    youtube_channel_id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    custom_url: Optional[str] = None
    subscriber_count: Optional[str] = None
    segment_count: Optional[int] = None

    class Config:
        from_attributes = True


class SegmentInChannel(BaseModel):
    id: str
    generated_title: str
    summary_text: Optional[str] = None
    start_time: int
    end_time: int
    duration: int
    view_count: int
    video_youtube_id: str
    video_thumbnail_url: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/{channel_id}", response_model=PublicChannelResponse)
async def get_channel_public(
    channel_id: str,
    db: Session = Depends(get_db)
):
    """Get channel details (public)"""
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.is_active == True
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    segment_count = db.query(Segment).join(Video).filter(
        Video.channel_id == channel.id
    ).count()
    
    return {
        "id": str(channel.id),
        "youtube_channel_id": channel.youtube_channel_id,
        "name": channel.name,
        "description": channel.description,
        "thumbnail_url": channel.thumbnail_url,
        "custom_url": channel.custom_url,
        "subscriber_count": channel.subscriber_count,
        "segment_count": segment_count,
    }


@router.get("/{channel_id}/segments")
async def get_channel_segments(
    channel_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all segments from a channel (public)"""
    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.is_active == True
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    skip = (page - 1) * limit
    
    segments_query = db.query(Segment).join(Video).filter(
        Video.channel_id == channel.id
    ).order_by(Segment.view_count.desc())
    
    total = segments_query.count()
    segments = segments_query.offset(skip).limit(limit).all()
    
    results = []
    for seg in segments:
        video = seg.video
        results.append({
            "id": str(seg.id),
            "generated_title": seg.generated_title,
            "title": seg.generated_title,
            "summary_text": seg.summary_text,
            "summary": seg.summary_text,
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "duration": seg.end_time - seg.start_time,
            "view_count": seg.view_count or 0,
            "video": {
                "youtube_id": video.youtube_id if video else None,
                "thumbnail_url": video.thumbnail_url if video else None,
                "title": video.original_title if video else None,
            },
            "channel": {
                "id": str(channel.id),
                "name": channel.name,
                "thumbnail_url": channel.thumbnail_url,
                "youtube_channel_id": channel.youtube_channel_id,
            }
        })
    
    return {
        "channel": {
            "id": str(channel.id),
            "youtube_channel_id": channel.youtube_channel_id,
            "name": channel.name,
            "description": channel.description,
            "thumbnail_url": channel.thumbnail_url,
            "custom_url": channel.custom_url,
            "subscriber_count": channel.subscriber_count,
            "segment_count": total,
        },
        "segments": results,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }

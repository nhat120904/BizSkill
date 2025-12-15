from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.video import Video, VideoStatus
from app.db.models.segment import Segment
from app.core.security import get_admin_user
from app.schemas import VideoResponse, VideoProcessRequest

router = APIRouter()


@router.get("", response_model=List[VideoResponse])
async def list_videos(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """List all videos (admin only)"""
    query = db.query(Video)
    
    if status:
        query = query.filter(Video.status == status)
    
    if channel_id:
        query = query.filter(Video.channel_id == channel_id)
    
    videos = query.order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for video in videos:
        segment_count = db.query(Segment).filter(Segment.video_id == video.id).count()
        results.append({
            **{c.name: getattr(video, c.name) for c in video.__table__.columns},
            "segment_count": segment_count,
            "channel": {
                "youtube_channel_id": video.channel.youtube_channel_id,
                "name": video.channel.name,
                "thumbnail_url": video.channel.thumbnail_url,
            } if video.channel else None
        })
    
    return results


@router.post("/process")
async def process_video(
    request: VideoProcessRequest,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Queue a video for processing (admin only)"""
    from app.workers.video_tasks import process_single_video_by_youtube_id
    
    task = process_single_video_by_youtube_id.delay(
        request.youtube_id,
        str(request.channel_id) if request.channel_id else None
    )
    
    return {"status": "queued", "task_id": task.id, "youtube_id": request.youtube_id}


@router.post("/batch-process")
async def batch_process_videos(
    youtube_ids: List[str],
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Queue multiple videos for processing (admin only)"""
    from app.workers.video_tasks import batch_process_videos
    
    task = batch_process_videos.delay(youtube_ids)
    
    return {"status": "queued", "task_id": task.id, "count": len(youtube_ids)}


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Get video details (admin only)"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    segment_count = db.query(Segment).filter(Segment.video_id == video.id).count()
    
    return {
        **{c.name: getattr(video, c.name) for c in video.__table__.columns},
        "segment_count": segment_count,
        "channel": {
            "youtube_channel_id": video.channel.youtube_channel_id,
            "name": video.channel.name,
            "thumbnail_url": video.channel.thumbnail_url,
        } if video.channel else None
    }


@router.post("/{video_id}/reprocess")
async def reprocess_video(
    video_id: str,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Reprocess a failed video (admin only)"""
    from app.workers.tasks import process_video
    
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Reset status
    video.status = VideoStatus.PENDING.value
    video.error_message = None
    db.commit()
    
    # Queue for processing
    task = process_video.delay(video_id)
    
    return {"status": "queued", "task_id": task.id}


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Delete a video and its segments (admin only)"""
    from app.services.embedding_service import EmbeddingService
    
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete embeddings
    embedding_service = EmbeddingService()
    embedding_service.delete_video_embeddings(video_id)
    
    # Delete video (cascades to segments)
    db.delete(video)
    db.commit()
    
    return {"status": "deleted"}

"""
Video Clip Tasks - Celery tasks for processing video segments
"""
from datetime import datetime
from typing import List, Optional
import structlog
from app.core.celery_app import celery_app
from app.db.session import get_db_session

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=2)
def process_segment_clip(self, segment_id: str):
    """
    Process a single segment: download video, cut segment, upload to Cloudinary
    """
    from app.db.models.segment import Segment
    from app.services.video_clip_service import VideoClipService
    
    db = get_db_session()
    
    try:
        segment = db.query(Segment).filter(Segment.id == segment_id).first()
        if not segment:
            logger.error("Segment not found", segment_id=segment_id)
            return {"status": "error", "error": "Segment not found"}
        
        if segment.cloudinary_url:
            logger.info("Segment already has clip", segment_id=segment_id)
            return {"status": "already_processed", "url": segment.cloudinary_url}
        
        # Update status
        segment.clip_status = "processing"
        db.commit()
        
        # Get video info
        youtube_id = segment.video.youtube_id
        categories = [sc.category.name for sc in segment.categories]
        
        # Process the clip
        clip_service = VideoClipService()
        result = clip_service.process_segment(
            youtube_id=youtube_id,
            segment_id=str(segment.id),
            start_time=segment.start_time,
            end_time=segment.end_time,
            title=segment.generated_title,
            categories=categories
        )
        
        # Update segment with Cloudinary info
        segment.cloudinary_url = result['url']
        segment.cloudinary_public_id = result['public_id']
        segment.cloudinary_thumbnail_url = result.get('thumbnail_url')
        segment.clip_status = "ready"
        segment.clip_processed_at = datetime.utcnow()
        db.commit()
        
        logger.info("Segment clip processed successfully",
                   segment_id=segment_id,
                   url=result['url'])
        
        return {
            "status": "success",
            "segment_id": segment_id,
            "url": result['url'],
            "thumbnail_url": result.get('thumbnail_url')
        }
        
    except Exception as e:
        logger.error("Segment clip processing failed",
                    segment_id=segment_id,
                    error=str(e))
        
        # Update status
        try:
            segment = db.query(Segment).filter(Segment.id == segment_id).first()
            if segment:
                segment.clip_status = "failed"
                db.commit()
        except:
            pass
        
        raise self.retry(exc=e)
        
    finally:
        db.close()


@celery_app.task
def process_video_clips(video_id: str):
    """
    Process all segments of a video
    """
    from app.db.models.segment import Segment
    from app.db.models.video import Video
    
    db = get_db_session()
    
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return {"status": "error", "error": "Video not found"}
        
        segments = db.query(Segment).filter(
            Segment.video_id == video_id,
            Segment.clip_status.in_(["pending", "failed"])
        ).all()
        
        tasks = []
        for segment in segments:
            task = process_segment_clip.delay(str(segment.id))
            tasks.append({
                "segment_id": str(segment.id),
                "task_id": task.id
            })
        
        logger.info("Queued segment clips for video",
                   video_id=video_id,
                   count=len(tasks))
        
        return {
            "status": "queued",
            "video_id": video_id,
            "segments_queued": len(tasks),
            "tasks": tasks
        }
        
    finally:
        db.close()


@celery_app.task
def process_all_pending_clips(limit: int = 100):
    """
    Process all pending segment clips
    """
    from app.db.models.segment import Segment
    from app.db.models.video import Video, VideoStatus
    
    db = get_db_session()
    
    try:
        segments = db.query(Segment).join(Video).filter(
            Video.status == VideoStatus.INDEXED.value,
            Segment.clip_status.in_(["pending", None])
        ).limit(limit).all()
        
        tasks = []
        for segment in segments:
            task = process_segment_clip.delay(str(segment.id))
            tasks.append({
                "segment_id": str(segment.id),
                "task_id": task.id
            })
        
        logger.info("Queued pending clips", count=len(tasks))
        
        return {
            "status": "queued",
            "segments_queued": len(tasks)
        }
        
    finally:
        db.close()


@celery_app.task
def cleanup_video_cache():
    """
    Clean up downloaded video files to free disk space
    """
    from app.services.video_clip_service import VideoClipService
    from pathlib import Path
    from datetime import timedelta
    import os
    
    clip_service = VideoClipService()
    temp_dir = clip_service.temp_dir
    
    if not temp_dir.exists():
        return {"cleaned": 0}
    
    cleaned = 0
    cutoff = datetime.now() - timedelta(hours=6)  # Keep for 6 hours
    
    for file_path in temp_dir.glob('*'):
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < cutoff:
                try:
                    os.remove(file_path)
                    cleaned += 1
                    logger.info("Cleaned up video file", path=str(file_path))
                except Exception as e:
                    logger.warning("Failed to clean video file",
                                 path=str(file_path), error=str(e))
    
    logger.info("Video cache cleanup complete", cleaned=cleaned)
    return {"cleaned": cleaned}


@celery_app.task
def get_clip_processing_stats():
    """
    Get statistics on clip processing
    """
    from app.db.models.segment import Segment
    from sqlalchemy import func
    
    db = get_db_session()
    
    try:
        stats = dict(db.query(
            Segment.clip_status,
            func.count(Segment.id)
        ).group_by(Segment.clip_status).all())
        
        total = db.query(func.count(Segment.id)).scalar()
        
        return {
            "total_segments": total,
            "by_status": stats,
            "pending": stats.get("pending", 0) + stats.get(None, 0),
            "processing": stats.get("processing", 0),
            "ready": stats.get("ready", 0),
            "failed": stats.get("failed", 0),
        }
        
    finally:
        db.close()

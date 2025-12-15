import os
from datetime import datetime, timedelta
from pathlib import Path
import structlog
from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import get_db_session

logger = structlog.get_logger()


@celery_app.task
def check_video_availability():
    """Daily task: Check if indexed videos are still available on YouTube"""
    from app.db.models.video import Video, VideoStatus
    from app.services.youtube_service import YouTubeService
    from app.services.embedding_service import EmbeddingService
    
    db = get_db_session()
    youtube = YouTubeService()
    embedding_service = EmbeddingService()
    
    try:
        # Get all indexed videos
        videos = db.query(Video).filter(
            Video.status == VideoStatus.INDEXED.value
        ).all()
        
        removed_count = 0
        checked_count = 0
        
        for video in videos:
            checked_count += 1
            
            # Check if video exists
            if not youtube.check_video_exists(video.youtube_id):
                logger.warning("Video no longer available", 
                             youtube_id=video.youtube_id,
                             title=video.original_title)
                
                # Mark as removed
                video.status = VideoStatus.REMOVED.value
                
                # Delete embeddings for this video
                embedding_service.delete_video_embeddings(str(video.id))
                
                removed_count += 1
            
            # Rate limiting - don't hammer the API
            if checked_count % 50 == 0:
                import time
                time.sleep(1)
        
        db.commit()
        
        logger.info("Video availability check complete",
                   checked=checked_count,
                   removed=removed_count)
        
        return {"checked": checked_count, "removed": removed_count}
        
    except Exception as e:
        logger.error("Video availability check failed", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task
def cleanup_temp_files():
    """Hourly task: Clean up old temporary audio files"""
    temp_dir = Path(settings.temp_audio_dir)
    
    if not temp_dir.exists():
        return {"cleaned": 0}
    
    cleaned = 0
    cutoff = datetime.now() - timedelta(hours=2)
    
    for file_path in temp_dir.glob('*'):
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < cutoff:
                try:
                    os.remove(file_path)
                    cleaned += 1
                    logger.info("Cleaned up temp file", path=str(file_path))
                except Exception as e:
                    logger.warning("Failed to clean temp file", 
                                 path=str(file_path), error=str(e))
    
    logger.info("Temp file cleanup complete", cleaned=cleaned)
    return {"cleaned": cleaned}


@celery_app.task
def cleanup_failed_videos():
    """Clean up videos that have failed too many times"""
    from app.db.models.video import Video, VideoStatus
    
    db = get_db_session()
    
    try:
        # Get videos that have failed 3+ times
        failed_videos = db.query(Video).filter(
            Video.status == VideoStatus.FAILED.value,
            Video.retry_count >= 3
        ).all()
        
        deleted = 0
        for video in failed_videos:
            # Check if it's been more than 7 days since last attempt
            if video.updated_at < datetime.utcnow() - timedelta(days=7):
                db.delete(video)
                deleted += 1
        
        db.commit()
        
        logger.info("Cleaned up failed videos", deleted=deleted)
        return {"deleted": deleted}
        
    except Exception as e:
        logger.error("Failed video cleanup error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task
def update_video_stats():
    """Weekly task: Update view counts and stats for indexed videos"""
    from app.db.models.video import Video, VideoStatus
    from app.services.youtube_service import YouTubeService
    
    db = get_db_session()
    youtube = YouTubeService()
    
    try:
        videos = db.query(Video).filter(
            Video.status == VideoStatus.INDEXED.value
        ).limit(100).all()  # Process in batches
        
        youtube_ids = [v.youtube_id for v in videos]
        
        if not youtube_ids:
            return {"updated": 0}
        
        # Batch fetch updated stats
        details = youtube.get_video_details(youtube_ids)
        
        detail_map = {d['youtube_id']: d for d in details}
        
        updated = 0
        for video in videos:
            if video.youtube_id in detail_map:
                detail = detail_map[video.youtube_id]
                video.view_count = detail.get('view_count')
                updated += 1
        
        db.commit()
        
        logger.info("Updated video stats", updated=updated)
        return {"updated": updated}
        
    except Exception as e:
        logger.error("Stats update failed", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()

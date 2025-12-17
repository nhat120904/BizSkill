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


@celery_app.task
def cleanup_duplicates():
    """Weekly task: Clean up duplicate videos and segments"""
    from app.db.models.video import Video, VideoStatus
    from app.db.models.segment import Segment
    from app.services.embedding_service import EmbeddingService
    from sqlalchemy import func
    
    db = get_db_session()
    
    try:
        stats = {
            "duplicate_videos": 0,
            "duplicate_segments": 0,
            "orphan_segments": 0,
        }
        
        # 1. Find and remove duplicate videos (same youtube_id)
        duplicates = db.query(
            Video.youtube_id,
            func.count(Video.id).label('count')
        ).group_by(Video.youtube_id).having(func.count(Video.id) > 1).all()
        
        for dup in duplicates:
            videos = db.query(Video).filter(
                Video.youtube_id == dup.youtube_id
            ).order_by(Video.created_at).all()
            
            # Keep the one with most segments and INDEXED status
            def score_video(v):
                seg_count = len(v.segments) if v.segments else 0
                is_indexed = 1 if v.status == VideoStatus.INDEXED.value else 0
                return (is_indexed, seg_count, v.created_at)
            
            videos_sorted = sorted(videos, key=score_video, reverse=True)
            to_delete = videos_sorted[1:]
            
            for v in to_delete:
                try:
                    embedding_service = EmbeddingService()
                    embedding_service.delete_video_embeddings(str(v.id))
                except Exception as e:
                    logger.warning("Failed to delete embeddings", video_id=str(v.id), error=str(e))
                
                db.delete(v)
                stats["duplicate_videos"] += 1
        
        # 2. Find and remove duplicate segments
        dup_segments = db.query(
            Segment.video_id,
            Segment.start_time,
            Segment.end_time,
            func.count(Segment.id).label('count')
        ).group_by(
            Segment.video_id, 
            Segment.start_time, 
            Segment.end_time
        ).having(func.count(Segment.id) > 1).all()
        
        for dup in dup_segments:
            segments = db.query(Segment).filter(
                Segment.video_id == dup.video_id,
                Segment.start_time == dup.start_time,
                Segment.end_time == dup.end_time
            ).order_by(Segment.created_at).all()
            
            for seg in segments[1:]:  # Keep first, delete rest
                if seg.embedding_id:
                    try:
                        embedding_service = EmbeddingService()
                        embedding_service.delete_segment_embedding(seg.embedding_id)
                    except:
                        pass
                db.delete(seg)
                stats["duplicate_segments"] += 1
        
        # 3. Find and remove orphan segments
        orphans = db.query(Segment).outerjoin(Video).filter(Video.id == None).all()
        for seg in orphans:
            if seg.embedding_id:
                try:
                    embedding_service = EmbeddingService()
                    embedding_service.delete_segment_embedding(seg.embedding_id)
                except:
                    pass
            db.delete(seg)
            stats["orphan_segments"] += 1
        
        db.commit()
        
        logger.info("Duplicate cleanup complete", **stats)
        return stats
        
    except Exception as e:
        logger.error("Duplicate cleanup failed", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task
def get_database_stats():
    """Get database statistics for admin dashboard"""
    from app.db.models.video import Video, VideoStatus
    from app.db.models.segment import Segment
    from app.db.models.channel import Channel
    from sqlalchemy import func
    
    db = get_db_session()
    
    try:
        # Video stats by status
        status_counts = dict(db.query(
            Video.status,
            func.count(Video.id)
        ).group_by(Video.status).all())
        
        # Total counts
        total_videos = db.query(func.count(Video.id)).scalar()
        total_segments = db.query(func.count(Segment.id)).scalar()
        total_channels = db.query(func.count(Channel.id)).scalar()
        active_channels = db.query(func.count(Channel.id)).filter(Channel.is_active == True).scalar()
        
        # Segments with embeddings
        segments_with_embedding = db.query(func.count(Segment.id)).filter(
            Segment.embedding_id != None
        ).scalar()
        
        return {
            "total_videos": total_videos,
            "total_segments": total_segments,
            "total_channels": total_channels,
            "active_channels": active_channels,
            "segments_with_embedding": segments_with_embedding,
            "videos_by_status": status_counts,
        }
        
    finally:
        db.close()

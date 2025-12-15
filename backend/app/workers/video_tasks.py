from datetime import datetime
from celery import chain
import structlog
from app.core.celery_app import celery_app
from app.db.session import get_db_session

logger = structlog.get_logger()


@celery_app.task(bind=True)
def process_single_video_by_youtube_id(self, youtube_id: str, channel_id: str = None):
    """Process a single video by YouTube ID (for manual processing)"""
    from app.db.models.video import Video, VideoStatus
    from app.db.models.channel import Channel
    from app.services.youtube_service import YouTubeService
    from app.workers.tasks import process_video
    
    db = get_db_session()
    youtube = YouTubeService()
    
    try:
        # Check if already exists
        existing = db.query(Video).filter(Video.youtube_id == youtube_id).first()
        if existing:
            if existing.status == VideoStatus.INDEXED.value:
                logger.info("Video already indexed", youtube_id=youtube_id)
                return {"status": "already_indexed", "video_id": str(existing.id)}
            elif existing.status == VideoStatus.FAILED.value:
                # Retry failed video
                existing.status = VideoStatus.PENDING.value
                existing.retry_count += 1
                db.commit()
                process_video.delay(str(existing.id))
                return {"status": "retrying", "video_id": str(existing.id)}
            else:
                return {"status": existing.status, "video_id": str(existing.id)}
        
        # Get video details
        details = youtube.get_video_details([youtube_id])
        if not details:
            return {"status": "not_found", "error": "Video not found on YouTube"}
        
        detail = details[0]
        
        # Find or create channel
        if channel_id:
            channel = db.query(Channel).filter(Channel.id == channel_id).first()
        else:
            channel = db.query(Channel).filter(
                Channel.youtube_channel_id == detail['channel_id']
            ).first()
            
            if not channel:
                # Create channel
                channel_info = youtube.get_channel_info(detail['channel_id'])
                if channel_info:
                    channel = Channel(
                        youtube_channel_id=channel_info['youtube_channel_id'],
                        name=channel_info['name'],
                        description=channel_info.get('description'),
                        thumbnail_url=channel_info.get('thumbnail_url'),
                        custom_url=channel_info.get('custom_url'),
                        subscriber_count=channel_info.get('subscriber_count'),
                        is_active=False  # Manual add, not active by default
                    )
                    db.add(channel)
                    db.flush()
        
        if not channel:
            return {"status": "error", "error": "Could not find or create channel"}
        
        # Create video
        video = Video(
            youtube_id=detail['youtube_id'],
            channel_id=channel.id,
            original_title=detail['title'],
            description=detail.get('description'),
            thumbnail_url=detail.get('thumbnail_url'),
            duration_seconds=detail['duration_seconds'],
            publish_date=detail.get('publish_date'),
            view_count=detail.get('view_count'),
            status=VideoStatus.PENDING.value
        )
        db.add(video)
        db.commit()
        
        # Queue for processing
        process_video.delay(str(video.id))
        
        logger.info("Video queued for processing", 
                   youtube_id=youtube_id,
                   video_id=str(video.id))
        
        return {"status": "queued", "video_id": str(video.id)}
        
    except Exception as e:
        logger.error("Failed to queue video", youtube_id=youtube_id, error=str(e))
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task
def batch_process_videos(youtube_ids: list):
    """Process multiple videos"""
    results = []
    for youtube_id in youtube_ids:
        result = process_single_video_by_youtube_id.delay(youtube_id)
        results.append({"youtube_id": youtube_id, "task_id": result.id})
    
    return results

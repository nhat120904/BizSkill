from datetime import datetime
from celery import chain
import structlog
from app.core.celery_app import celery_app
from app.db.session import get_db_session
from app.db.models.channel import Channel
from app.db.models.video import Video, VideoStatus
from app.services.youtube_service import YouTubeService

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3)
def poll_all_channels(self):
    """Scheduled task: Poll all whitelisted channels for new videos"""
    logger.info("Starting channel polling")
    
    db = get_db_session()
    try:
        channels = db.query(Channel).filter(Channel.is_active == True).all()
        
        for channel in channels:
            poll_channel.delay(str(channel.id))
        
        logger.info("Queued channel polls", channel_count=len(channels))
        
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def poll_channel(self, channel_id: str):
    """Poll a single channel for new videos"""
    db = get_db_session()
    youtube = YouTubeService()
    
    try:
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            logger.error("Channel not found", channel_id=channel_id)
            return
        
        logger.info("Polling channel", channel_name=channel.name)
        
        # Get channel info to get uploads playlist
        channel_info = youtube.get_channel_info(channel.youtube_channel_id)
        if not channel_info:
            logger.error("Could not fetch channel info", channel_id=channel_id)
            return
        
        uploads_playlist = channel_info['uploads_playlist_id']
        
        # Get videos since last check
        since = channel.last_synced_at
        videos = youtube.get_latest_videos(
            uploads_playlist,
            max_results=20,
            since=since
        )
        
        new_count = 0
        for video_data in videos:
            # Check if video already exists
            existing = db.query(Video).filter(
                Video.youtube_id == video_data['youtube_id']
            ).first()
            
            if existing:
                continue
            
            # Get full video details
            details = youtube.get_video_details([video_data['youtube_id']])
            if not details:
                continue
            
            detail = details[0]
            
            # Skip very long videos
            from app.core.config import settings
            if detail['duration_seconds'] > settings.max_video_duration_minutes * 60:
                logger.info("Skipping long video", 
                           youtube_id=detail['youtube_id'],
                           duration=detail['duration_seconds'])
                continue
            
            # Create video record
            video = Video(
                youtube_id=detail['youtube_id'],
                channel_id=channel.id,
                original_title=detail['title'],
                description=detail.get('description'),
                thumbnail_url=detail.get('thumbnail_url'),
                duration_seconds=detail['duration_seconds'],
                published_at=detail.get('publish_date'),
                view_count=detail.get('view_count'),
                status=VideoStatus.PENDING.value
            )
            db.add(video)
            db.commit()
            
            # Queue for processing
            process_video.delay(str(video.id))
            new_count += 1
        
        # Update last synced
        channel.last_synced_at = datetime.utcnow()
        db.commit()
        
        logger.info("Channel poll complete", 
                   channel_name=channel.name,
                   new_videos=new_count)
        
    except Exception as e:
        logger.error("Channel poll failed", channel_id=channel_id, error=str(e))
        db.rollback()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def process_video(self, video_id: str):
    """Main video processing pipeline"""
    logger.info("Starting video processing", video_id=video_id)
    
    # Chain the processing tasks
    pipeline = chain(
        download_audio.s(video_id),
        transcribe_audio.s(video_id),
        segment_transcript.s(video_id),
        generate_insights.s(video_id),
        create_embeddings.s(video_id),
        cleanup_and_finalize.s(video_id)
    )
    
    return pipeline.apply_async()


@celery_app.task(bind=True, max_retries=3)
def download_audio(self, video_id: str):
    """Step 1: Download audio from YouTube"""
    from app.services.audio_service import AudioExtractionService
    
    db = get_db_session()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")
        
        video.status = VideoStatus.DOWNLOADING.value
        db.commit()
        
        audio_service = AudioExtractionService()
        audio_path = audio_service.download_audio(video.youtube_id)
        
        logger.info("Audio downloaded", video_id=video_id, path=str(audio_path))
        
        return str(audio_path)
        
    except Exception as e:
        logger.error("Audio download failed", video_id=video_id, error=str(e))
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.FAILED.value
            video.processing_error = f"Audio download failed: {str(e)}"
            db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def transcribe_audio(self, audio_path: str, video_id: str):
    """Step 2: Transcribe audio with Whisper"""
    from pathlib import Path
    from app.services.transcription_service import TranscriptionService
    
    db = get_db_session()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")
        
        video.status = VideoStatus.TRANSCRIBING.value
        db.commit()
        
        transcription_service = TranscriptionService()
        result = transcription_service.transcribe_with_segments(Path(audio_path))
        
        # Save transcript
        video.transcript = result['full_text']
        db.commit()
        
        logger.info("Transcription complete", 
                   video_id=video_id,
                   segments=len(result['segments']),
                   duration=result['duration'])
        
        return {
            'audio_path': audio_path,
            'transcript_segments': result['segments'],
            'full_text': result['full_text'],
            'duration': result['duration']
        }
        
    except Exception as e:
        logger.error("Transcription failed", video_id=video_id, error=str(e))
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.FAILED.value
            video.processing_error = f"Transcription failed: {str(e)}"
            db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def segment_transcript(self, transcript_data: dict, video_id: str):
    """Step 3: Use LLM to identify segments"""
    from app.services.llm_service import LLMSegmentationService
    
    db = get_db_session()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")
        
        video.status = VideoStatus.SEGMENTING.value
        db.commit()
        
        llm_service = LLMSegmentationService()
        segments = llm_service.identify_segments(
            transcript_segments=transcript_data['transcript_segments'],
            video_title=video.original_title,
            video_duration=video.duration_seconds
        )
        
        logger.info("Segmentation complete", 
                   video_id=video_id,
                   segment_count=len(segments))
        
        return {
            **transcript_data,
            'segments': [s.model_dump() for s in segments]
        }
        
    except Exception as e:
        logger.error("Segmentation failed", video_id=video_id, error=str(e))
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.FAILED.value
            video.processing_error = f"Segmentation failed: {str(e)}"
            db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def generate_insights(self, segment_data: dict, video_id: str):
    """Step 4: Generate titles, summaries for each segment"""
    from app.services.llm_service import LLMSegmentationService
    from app.db.models.segment import Segment
    from app.db.models.category import Category, SegmentCategory
    
    db = get_db_session()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")
        
        llm_service = LLMSegmentationService()
        
        created_segments = []
        for seg_info in segment_data['segments']:
            # Extract transcript for this segment
            segment_transcript = llm_service.get_segment_transcript(
                segment_data['transcript_segments'],
                seg_info['start_time'],
                seg_info['end_time']
            )
            
            # Generate insights
            insights = llm_service.extract_insights(
                segment_transcript=segment_transcript,
                segment_topic=seg_info['topic'],
                video_title=video.original_title
            )
            
            # Create segment record
            segment = Segment(
                video_id=video.id,
                start_time=seg_info['start_time'],
                end_time=seg_info['end_time'],
                generated_title=insights.generated_title,
                summary_text=insights.summary_text,
                key_takeaways=insights.key_takeaways,
                relevance_score=insights.relevance_score,
                transcript_chunk=segment_transcript[:2000]  # Limit size
            )
            db.add(segment)
            db.flush()  # Get the ID
            
            # Link categories
            for cat_name in insights.categories:
                category = db.query(Category).filter(
                    Category.name == cat_name
                ).first()
                if category:
                    segment_category = SegmentCategory(
                        segment_id=segment.id,
                        category_id=category.id
                    )
                    db.add(segment_category)
            
            created_segments.append({
                'segment_id': str(segment.id),
                'title': insights.generated_title,
                'summary': insights.summary_text,
                'transcript': segment_transcript,
                'start_time': seg_info['start_time'],
                'end_time': seg_info['end_time'],
                'relevance_score': insights.relevance_score,
                'categories': insights.categories
            })
        
        db.commit()
        
        logger.info("Insights generated", 
                   video_id=video_id,
                   segment_count=len(created_segments))
        
        return {
            'audio_path': segment_data['audio_path'],
            'segments': created_segments
        }
        
    except Exception as e:
        logger.error("Insight generation failed", video_id=video_id, error=str(e))
        db.rollback()
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.FAILED.value
            video.processing_error = f"Insight generation failed: {str(e)}"
            db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def create_embeddings(self, insight_data: dict, video_id: str):
    """Step 5: Generate and store embeddings"""
    from app.services.embedding_service import EmbeddingService
    from app.db.models.segment import Segment
    
    db = get_db_session()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video not found: {video_id}")
        
        video.status = VideoStatus.EMBEDDING.value
        db.commit()
        
        embedding_service = EmbeddingService()
        
        for seg_data in insight_data['segments']:
            segment = db.query(Segment).filter(
                Segment.id == seg_data['segment_id']
            ).first()
            
            if not segment:
                continue
            
            # Store embedding
            point_id = embedding_service.store_segment_embedding(
                segment_id=str(segment.id),
                title=seg_data['title'],
                summary=seg_data['summary'],
                transcript=seg_data['transcript'][:1000],
                video_id=str(video.id),
                youtube_id=video.youtube_id,
                channel_name=video.channel.name,
                start_time=seg_data['start_time'],
                end_time=seg_data['end_time'],
                relevance_score=seg_data['relevance_score'],
                categories=seg_data['categories'],
                thumbnail_url=video.thumbnail_url
            )
            
            # Save embedding reference
            segment.embedding_id = point_id
            db.commit()
        
        logger.info("Embeddings created", 
                   video_id=video_id,
                   count=len(insight_data['segments']))
        
        return insight_data['audio_path']
        
    except Exception as e:
        logger.error("Embedding creation failed", video_id=video_id, error=str(e))
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = VideoStatus.FAILED.value
            video.processing_error = f"Embedding failed: {str(e)}"
            db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task
def cleanup_and_finalize(audio_path: str, video_id: str):
    """Step 6: Clean up and mark as complete"""
    from pathlib import Path
    from app.services.audio_service import AudioExtractionService
    from app.workers.clip_tasks import process_segment_clip
    
    db = get_db_session()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return
        
        # Clean up audio file
        audio_service = AudioExtractionService()
        audio_service.cleanup(Path(audio_path))
        audio_service.cleanup_all(video.youtube_id)
        
        # Mark as indexed
        video.status = VideoStatus.INDEXED.value
        video.processed_at = datetime.utcnow()
        video.processing_error = None
        db.commit()
        
        segment_count = len(video.segments)
        
        # Auto-queue clip processing for all segments
        for segment in video.segments:
            if segment.clip_status == "pending":
                process_segment_clip.delay(str(segment.id))
        
        logger.info("Video processing complete", 
                   video_id=video_id,
                   youtube_id=video.youtube_id,
                   title=video.original_title,
                   segments=segment_count,
                   clips_queued=segment_count)
        
        return {
            'video_id': video_id,
            'status': 'indexed',
            'segments': segment_count,
            'clips_queued': segment_count
        }
        
    except Exception as e:
        logger.error("Cleanup failed", video_id=video_id, error=str(e))
    finally:
        db.close()

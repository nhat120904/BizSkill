from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from app.db.session import get_db
from app.db.models.channel import Channel
from app.db.models.video import Video, VideoStatus
from app.db.models.segment import Segment
from app.db.models.category import Category
from app.core.security import get_admin_user
from app.schemas import StatsResponse
from app.services.embedding_service import EmbeddingService

router = APIRouter()


class InitChannelData(BaseModel):
    youtube_channel_id: str
    name: str
    description: Optional[str] = None


class InitCategoryData(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class InitRequest(BaseModel):
    channels: List[InitChannelData] = []
    categories: List[InitCategoryData] = []


@router.post("/init")
async def initialize_platform(
    data: InitRequest,
    db: Session = Depends(get_db)
):
    """
    Initialize platform with channels and categories.
    This endpoint is only available when the database is empty.
    """
    # Check if already initialized
    existing_channels = db.query(Channel).count()
    existing_categories = db.query(Category).count()
    
    if existing_channels > 0 or existing_categories > 0:
        raise HTTPException(
            status_code=400, 
            detail="Platform already initialized. Use admin endpoints to add more data."
        )
    
    results = {"channels": [], "categories": []}
    
    # Add categories
    for cat_data in data.categories:
        category = Category(
            name=cat_data.name,
            slug=cat_data.slug,
            description=cat_data.description,
            icon=cat_data.icon,
            color=cat_data.color,
        )
        db.add(category)
        results["categories"].append(cat_data.name)
    
    # Add channels
    for ch_data in data.channels:
        channel = Channel(
            youtube_channel_id=ch_data.youtube_channel_id,
            name=ch_data.name,
            description=ch_data.description,
            is_active=True,
        )
        db.add(channel)
        results["channels"].append(ch_data.name)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Initialized with {len(results['channels'])} channels and {len(results['categories'])} categories",
        "channels": results["channels"],
        "categories": results["categories"],
    }


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Get platform statistics (admin only)"""
    total_channels = db.query(Channel).count()
    total_videos = db.query(Video).count()
    total_segments = db.query(Segment).count()
    
    indexed_videos = db.query(Video).filter(
        Video.status == VideoStatus.INDEXED.value
    ).count()
    
    processing_videos = db.query(Video).filter(
        Video.status.in_([
            VideoStatus.PENDING.value,
            VideoStatus.DOWNLOADING.value,
            VideoStatus.TRANSCRIBING.value,
            VideoStatus.SEGMENTING.value,
            VideoStatus.EMBEDDING.value,
        ])
    ).count()
    
    failed_videos = db.query(Video).filter(
        Video.status == VideoStatus.FAILED.value
    ).count()
    
    return StatsResponse(
        total_channels=total_channels,
        total_videos=total_videos,
        total_segments=total_segments,
        indexed_videos=indexed_videos,
        processing_videos=processing_videos,
        failed_videos=failed_videos,
    )


@router.get("/vector-stats")
async def get_vector_stats(
    _admin = Depends(get_admin_user)
):
    """Get vector database statistics (admin only)"""
    embedding_service = EmbeddingService()
    stats = embedding_service.get_collection_stats()
    return stats


@router.post("/seed-channels")
async def seed_famous_channels(
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Seed database with famous business channels (admin only)"""
    from app.services.youtube_service import YouTubeService
    
    # 10 Famous Business/Leadership YouTube Channels
    famous_channels = [
        {"handle": "TED", "description": "Ideas worth spreading"},
        {"handle": "HarvardBusinessReview", "description": "Management tips and leadership insights"},
        {"handle": "Ycombinator", "description": "Startup advice from Y Combinator"},
        {"handle": "GaryVee", "description": "Gary Vaynerchuk - Entrepreneurship & Marketing"},
        {"handle": "SimonSinek", "description": "Leadership and inspiration"},
        {"handle": "TheFuturAcademy", "description": "Business and design education"},
        {"handle": "valuetainment", "description": "Patrick Bet-David - Business advice"},
        {"handle": "AliAbdaal", "description": "Productivity and personal development"},
        {"handle": "MasterClass", "description": "Learn from the world's best"},
        {"handle": "Stanford", "description": "Stanford University lectures"},
    ]
    
    youtube = YouTubeService()
    added = []
    errors = []
    
    for ch in famous_channels:
        try:
            # Check if already exists
            existing = db.query(Channel).filter(
                Channel.custom_url == f"@{ch['handle']}"
            ).first()
            
            if existing:
                continue
            
            # Fetch channel info
            channel_info = youtube.get_channel_by_handle(ch['handle'])
            
            if not channel_info:
                errors.append({"handle": ch['handle'], "error": "Not found"})
                continue
            
            # Check by YouTube ID
            existing = db.query(Channel).filter(
                Channel.youtube_channel_id == channel_info['youtube_channel_id']
            ).first()
            
            if existing:
                continue
            
            # Create channel
            channel = Channel(
                youtube_channel_id=channel_info['youtube_channel_id'],
                name=channel_info['name'],
                description=channel_info.get('description', ch['description']),
                thumbnail_url=channel_info.get('thumbnail_url'),
                custom_url=channel_info.get('custom_url'),
                subscriber_count=channel_info.get('subscriber_count'),
                is_active=True
            )
            db.add(channel)
            added.append(channel_info['name'])
            
        except Exception as e:
            errors.append({"handle": ch['handle'], "error": str(e)})
    
    db.commit()
    
    return {
        "status": "complete",
        "added": added,
        "added_count": len(added),
        "errors": errors
    }


@router.post("/seed-categories")
async def seed_categories(
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Seed default categories (admin only)"""
    from app.db.models.category import Category
    
    categories = [
        {"name": "Leadership", "slug": "leadership", "icon": "👑", "color": "#FFD700"},
        {"name": "Communication", "slug": "communication", "icon": "💬", "color": "#4A90E2"},
        {"name": "Sales", "slug": "sales", "icon": "💰", "color": "#27AE60"},
        {"name": "Marketing", "slug": "marketing", "icon": "📢", "color": "#E74C3C"},
        {"name": "Productivity", "slug": "productivity", "icon": "⚡", "color": "#F39C12"},
        {"name": "Career Growth", "slug": "career-growth", "icon": "📈", "color": "#9B59B6"},
        {"name": "Negotiation", "slug": "negotiation", "icon": "🤝", "color": "#1ABC9C"},
        {"name": "Management", "slug": "management", "icon": "📋", "color": "#3498DB"},
        {"name": "Entrepreneurship", "slug": "entrepreneurship", "icon": "🚀", "color": "#E91E63"},
        {"name": "Personal Finance", "slug": "personal-finance", "icon": "💵", "color": "#4CAF50"},
        {"name": "Networking", "slug": "networking", "icon": "🌐", "color": "#00BCD4"},
        {"name": "Innovation", "slug": "innovation", "icon": "💡", "color": "#FF9800"},
        {"name": "Strategy", "slug": "strategy", "icon": "♟️", "color": "#607D8B"},
        {"name": "Mindset", "slug": "mindset", "icon": "🧠", "color": "#673AB7"},
    ]
    
    added = []
    for cat in categories:
        existing = db.query(Category).filter(Category.slug == cat['slug']).first()
        if not existing:
            category = Category(**cat)
            db.add(category)
            added.append(cat['name'])
    
    db.commit()
    
    return {"status": "complete", "added": added, "count": len(added)}


@router.post("/trigger-poll")
async def trigger_channel_poll(
    _admin = Depends(get_admin_user)
):
    """Trigger immediate poll of all channels (admin only)"""
    from app.workers.tasks import poll_all_channels
    
    task = poll_all_channels.delay()
    
    return {"status": "queued", "task_id": task.id}


@router.post("/dev/sync-all")
async def dev_sync_all_channels(
    db: Session = Depends(get_db)
):
    """
    DEV ONLY: Trigger sync for all active channels without authentication.
    This will queue video download and processing for all channels.
    """
    from app.workers.tasks import poll_channel
    
    channels = db.query(Channel).filter(Channel.is_active == True).all()
    
    if not channels:
        raise HTTPException(status_code=404, detail="No active channels found")
    
    tasks = []
    for channel in channels:
        task = poll_channel.delay(channel.id)
        tasks.append({
            "channel_id": channel.id,
            "channel_name": channel.name,
            "task_id": task.id
        })
    
    return {
        "status": "queued",
        "channels_queued": len(tasks),
        "tasks": tasks
    }


@router.get("/dev/channels")
async def dev_list_channels(
    db: Session = Depends(get_db)
):
    """DEV ONLY: List all channels without authentication."""
    channels = db.query(Channel).all()
    return [
        {
            "id": ch.id,
            "name": ch.name,
            "youtube_channel_id": ch.youtube_channel_id,
            "is_active": ch.is_active,
        }
        for ch in channels
    ]


@router.post("/dev/sync/{channel_id}")
async def dev_sync_channel(
    channel_id: str,
    db: Session = Depends(get_db)
):
    """DEV ONLY: Trigger sync for a specific channel without authentication."""
    from app.workers.tasks import poll_channel
    
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    task = poll_channel.delay(channel.id)
    
    return {
        "status": "queued",
        "channel_id": channel.id,
        "channel_name": channel.name,
        "task_id": task.id
    }


@router.post("/dev/reprocess-pending")
async def dev_reprocess_pending(
    db: Session = Depends(get_db)
):
    """DEV ONLY: Re-queue all pending/downloading videos for processing."""
    from app.workers.tasks import process_video
    
    # Get all videos that are stuck in pending or downloading status
    videos = db.query(Video).filter(
        Video.status.in_([
            VideoStatus.PENDING.value,
            VideoStatus.DOWNLOADING.value,
            VideoStatus.TRANSCRIBING.value,
            VideoStatus.SEGMENTING.value,
            VideoStatus.EMBEDDING.value,
        ])
    ).all()
    
    # Reset status to pending and requeue
    queued = []
    for video in videos:
        video.status = VideoStatus.PENDING.value
        video.processing_error = None
        db.commit()
        
        task = process_video.delay(str(video.id))
        queued.append({
            "video_id": str(video.id),
            "youtube_id": video.youtube_id,
            "task_id": task.id
        })
    
    return {
        "status": "queued",
        "count": len(queued),
        "videos": queued[:20]  # Only return first 20 for brevity
    }


@router.post("/create-admin")
async def create_admin_user(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    """Create an admin user (no auth required - use once during setup)"""
    from app.db.models.user import User
    from app.core.security import get_password_hash
    
    # Check if any admin exists
    existing_admin = db.query(User).filter(User.is_admin == True).first()
    if existing_admin:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400, 
            detail="Admin user already exists. Use the admin panel to create more."
        )
    
    # Check if email exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name="Admin",
        is_admin=True
    )
    db.add(user)
    db.commit()
    
    return {"status": "created", "email": email}


@router.post("/cleanup/duplicates")
async def cleanup_duplicates(
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """
    Clean up duplicate videos and segments (admin only).
    Removes duplicate youtube_ids (keeping best one) and duplicate segments.
    """
    from app.workers.maintenance_tasks import cleanup_duplicates as cleanup_task
    
    task = cleanup_task.delay()
    
    return {
        "status": "queued", 
        "task_id": task.id,
        "message": "Cleanup task queued. Check task status for results."
    }


@router.post("/dev/cleanup")
async def dev_cleanup_duplicates(
    db: Session = Depends(get_db)
):
    """
    DEV ONLY: Run duplicate cleanup synchronously and return results.
    No authentication required for development.
    """
    from sqlalchemy import func
    
    stats = {
        "duplicate_videos": 0,
        "duplicate_segments": 0,
        "orphan_segments": 0,
        "details": []
    }
    
    # 1. Find and remove duplicate videos
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
        keep = videos_sorted[0]
        to_delete = videos_sorted[1:]
        
        for v in to_delete:
            try:
                embedding_service = EmbeddingService()
                embedding_service.delete_video_embeddings(str(v.id))
            except Exception as e:
                pass
            
            stats["details"].append({
                "action": "delete_video",
                "youtube_id": v.youtube_id,
                "reason": f"duplicate (keeping {keep.id[:8]})"
            })
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
        
        for seg in segments[1:]:
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
    
    return {
        "status": "complete",
        "removed": {
            "duplicate_videos": stats["duplicate_videos"],
            "duplicate_segments": stats["duplicate_segments"],
            "orphan_segments": stats["orphan_segments"],
        },
        "details": stats["details"][:20]  # Limit output
    }


@router.get("/dev/duplicates")
async def dev_check_duplicates(
    db: Session = Depends(get_db)
):
    """
    DEV ONLY: Check for duplicates without removing them.
    Returns a report of what would be cleaned.
    """
    from sqlalchemy import func
    
    report = {
        "duplicate_videos": [],
        "duplicate_segments": [],
        "orphan_segments": 0,
        "summary": {}
    }
    
    # 1. Find duplicate videos
    duplicates = db.query(
        Video.youtube_id,
        func.count(Video.id).label('count')
    ).group_by(Video.youtube_id).having(func.count(Video.id) > 1).all()
    
    for dup in duplicates:
        videos = db.query(Video).filter(
            Video.youtube_id == dup.youtube_id
        ).order_by(Video.created_at).all()
        
        report["duplicate_videos"].append({
            "youtube_id": dup.youtube_id,
            "count": dup.count,
            "videos": [
                {
                    "id": v.id[:8],
                    "status": v.status,
                    "segments": len(v.segments) if v.segments else 0,
                    "created_at": str(v.created_at)
                }
                for v in videos
            ]
        })
    
    # 2. Find duplicate segments
    dup_segments = db.query(
        Segment.video_id,
        Segment.start_time,
        Segment.end_time,
        func.count(Segment.id).label('count')
    ).group_by(
        Segment.video_id, 
        Segment.start_time, 
        Segment.end_time
    ).having(func.count(Segment.id) > 1).limit(20).all()
    
    for dup in dup_segments:
        report["duplicate_segments"].append({
            "video_id": dup.video_id[:8] if dup.video_id else None,
            "start_time": dup.start_time,
            "end_time": dup.end_time,
            "count": dup.count
        })
    
    # 3. Count orphan segments
    orphan_count = db.query(func.count(Segment.id)).outerjoin(Video).filter(Video.id == None).scalar()
    report["orphan_segments"] = orphan_count
    
    # Summary
    report["summary"] = {
        "duplicate_videos_count": len(report["duplicate_videos"]),
        "duplicate_segments_count": len(dup_segments),
        "orphan_segments_count": orphan_count,
        "total_issues": len(report["duplicate_videos"]) + len(dup_segments) + orphan_count
    }
    
    return report


@router.get("/dev/stats")
async def dev_get_stats(
    db: Session = Depends(get_db)
):
    """DEV ONLY: Get database statistics without authentication."""
    from sqlalchemy import func
    
    # Video stats by status
    status_counts = dict(db.query(
        Video.status,
        func.count(Video.id)
    ).group_by(Video.status).all())
    
    # Channel stats
    channel_stats = db.query(
        Channel.name,
        func.count(Video.id).label('video_count')
    ).outerjoin(Video).group_by(Channel.id).order_by(
        func.count(Video.id).desc()
    ).limit(10).all()
    
    # Totals
    total_videos = db.query(func.count(Video.id)).scalar()
    total_segments = db.query(func.count(Segment.id)).scalar()
    total_channels = db.query(func.count(Channel.id)).scalar()
    segments_with_embedding = db.query(func.count(Segment.id)).filter(
        Segment.embedding_id != None
    ).scalar()
    
    return {
        "totals": {
            "videos": total_videos,
            "segments": total_segments,
            "channels": total_channels,
            "segments_with_embedding": segments_with_embedding
        },
        "videos_by_status": status_counts,
        "top_channels": [
            {"name": name, "videos": count}
            for name, count in channel_stats
        ]
    }


# ============== VIDEO CLIP PROCESSING (Cloudinary) ==============

@router.get("/clips/stats")
async def get_clip_stats(
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Get video clip processing statistics (admin only)"""
    from sqlalchemy import func
    
    stats = dict(db.query(
        Segment.clip_status,
        func.count(Segment.id)
    ).group_by(Segment.clip_status).all())
    
    total = db.query(func.count(Segment.id)).scalar()
    ready_count = stats.get("ready", 0)
    
    return {
        "total_segments": total,
        "clips_ready": ready_count,
        "clips_pending": stats.get("pending", 0) + stats.get(None, 0),
        "clips_processing": stats.get("processing", 0),
        "clips_failed": stats.get("failed", 0),
        "by_status": stats
    }


@router.post("/clips/process/{segment_id}")
async def process_single_clip(
    segment_id: str,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Process a single segment clip (admin only)"""
    from app.workers.clip_tasks import process_segment_clip
    
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    task = process_segment_clip.delay(segment_id)
    
    return {
        "status": "queued",
        "segment_id": segment_id,
        "task_id": task.id
    }


@router.post("/clips/process-video/{video_id}")
async def process_video_clips(
    video_id: str,
    db: Session = Depends(get_db),
    _admin = Depends(get_admin_user)
):
    """Process all clips for a video (admin only)"""
    from app.workers.clip_tasks import process_video_clips as task_process_video
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    task = task_process_video.delay(video_id)
    
    return {
        "status": "queued",
        "video_id": video_id,
        "task_id": task.id
    }


@router.post("/clips/process-all")
async def process_all_clips(
    limit: int = 100,
    _admin = Depends(get_admin_user)
):
    """Process all pending clips (admin only)"""
    from app.workers.clip_tasks import process_all_pending_clips
    
    task = process_all_pending_clips.delay(limit)
    
    return {
        "status": "queued",
        "limit": limit,
        "task_id": task.id
    }


# DEV endpoints for clip processing (no auth)
@router.get("/dev/clips/stats")
async def dev_get_clip_stats(
    db: Session = Depends(get_db)
):
    """DEV ONLY: Get clip stats without authentication"""
    from sqlalchemy import func
    
    stats = dict(db.query(
        Segment.clip_status,
        func.count(Segment.id)
    ).group_by(Segment.clip_status).all())
    
    total = db.query(func.count(Segment.id)).scalar()
    
    # Get some ready clips as examples
    ready_clips = db.query(Segment).filter(
        Segment.clip_status == "ready"
    ).limit(5).all()
    
    return {
        "total_segments": total,
        "by_status": stats,
        "ready_clips_sample": [
            {
                "id": s.id,
                "title": s.generated_title,
                "cloudinary_url": s.cloudinary_url,
                "thumbnail_url": s.cloudinary_thumbnail_url
            }
            for s in ready_clips
        ]
    }


@router.post("/dev/clips/process/{segment_id}")
async def dev_process_clip(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """DEV ONLY: Process a single clip without authentication"""
    from app.workers.clip_tasks import process_segment_clip
    
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    task = process_segment_clip.delay(segment_id)
    
    return {
        "status": "queued",
        "segment_id": segment_id,
        "title": segment.generated_title,
        "task_id": task.id
    }


@router.post("/dev/clips/process-batch")
async def dev_process_batch(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """DEV ONLY: Process a batch of pending clips"""
    from app.workers.clip_tasks import process_segment_clip
    
    segments = db.query(Segment).join(Video).filter(
        Video.status == VideoStatus.INDEXED.value,
        Segment.clip_status.in_(["pending", None])
    ).limit(limit).all()
    
    tasks = []
    for segment in segments:
        task = process_segment_clip.delay(str(segment.id))
        tasks.append({
            "segment_id": str(segment.id),
            "title": segment.generated_title[:50] if segment.generated_title else None,
            "task_id": task.id
        })
    
    return {
        "status": "queued",
        "count": len(tasks),
        "tasks": tasks
    }


@router.post("/dev/reindex")
async def dev_reindex_embeddings(
    batch_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    DEV ONLY: Re-index all segments with new embedding model.
    This will:
    1. Delete and recreate Qdrant collection with new dimensions
    2. Re-embed all indexed segments using local BGE-M3 model
    """
    import structlog
    logger = structlog.get_logger()
    
    # Get all indexed segments
    segments = db.query(Segment).join(Video).filter(
        Video.status == VideoStatus.INDEXED.value
    ).all()
    
    total = len(segments)
    logger.info("Starting re-index", total_segments=total)
    
    # Recreate collection with correct dimensions
    embedding_service = EmbeddingService()
    embedding_service.recreate_collection()
    
    # Process in batches
    processed = 0
    failed = 0
    
    for i in range(0, total, batch_size):
        batch = segments[i:i+batch_size]
        
        for segment in batch:
            try:
                video = segment.video
                channel = video.channel
                # SegmentCategory is association table, need to access category.name
                categories = [sc.category.name for sc in segment.categories if sc.category] if segment.categories else []
                
                embedding_service.store_segment_embedding(
                    segment_id=str(segment.id),
                    title=segment.generated_title or "",
                    summary=segment.summary_text or "",  # Field is summary_text not summary
                    transcript=segment.transcript_chunk or "",  # Field is transcript_chunk
                    video_id=str(video.id),
                    youtube_id=video.youtube_id,
                    channel_name=channel.name if channel else "",
                    start_time=int(segment.start_time),
                    end_time=int(segment.end_time),
                    relevance_score=int(segment.relevance_score or 5),
                    categories=categories,
                    thumbnail_url=video.thumbnail_url
                )
                processed += 1
                
            except Exception as e:
                logger.error("Failed to re-index segment", 
                           segment_id=str(segment.id), 
                           error=str(e))
                failed += 1
        
        logger.info("Re-index progress", processed=processed, failed=failed, total=total)
    
    return {
        "status": "completed",
        "total": total,
        "processed": processed,
        "failed": failed,
        "embedding_dim": embedding_service.embedding_dim,
        "use_local": embedding_service.use_local
    }


@router.get("/dev/qdrant-info")
async def dev_qdrant_info():
    """DEV ONLY: Get Qdrant collection info"""
    from qdrant_client import QdrantClient
    from app.core.config import settings
    
    client = QdrantClient(url=settings.qdrant_url)
    
    try:
        collection = client.get_collection(settings.qdrant_collection)
        return {
            "collection_name": settings.qdrant_collection,
            "vectors_count": collection.vectors_count,
            "points_count": collection.points_count,
            "config": {
                "size": collection.config.params.vectors.size,
                "distance": str(collection.config.params.vectors.distance)
            }
        }
    except Exception as e:
        return {
            "error": str(e),
            "collection_name": settings.qdrant_collection
        }

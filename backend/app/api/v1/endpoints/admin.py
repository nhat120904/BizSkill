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

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User, UserHistory, SavedSegment, UserInterest
from app.db.models.segment import Segment
from app.db.models.category import Category
from app.core.security import get_current_user_required
from app.schemas import UserResponse, HistoryCreate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user_required)
):
    """Get current user info"""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at
    )


@router.put("/me")
async def update_profile(
    full_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if full_name is not None:
        user.full_name = full_name
    if avatar_url is not None:
        user.avatar_url = avatar_url
    
    db.commit()
    
    return {"status": "updated"}


@router.get("/interests")
async def get_interests(
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get user's interests"""
    interests = db.query(UserInterest).filter(
        UserInterest.user_id == user.id
    ).all()
    
    return {
        "interests": [
            {
                "category_id": i.category_id,
                "category_name": i.category.name,
                "category_slug": i.category.slug,
            }
            for i in interests
        ]
    }


@router.post("/interests")
async def set_interests(
    category_slugs: List[str],
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Set user's interests"""
    # Clear existing interests
    db.query(UserInterest).filter(UserInterest.user_id == user.id).delete()
    
    # Add new interests
    for slug in category_slugs:
        category = db.query(Category).filter(Category.slug == slug).first()
        if category:
            interest = UserInterest(user_id=user.id, category_id=category.id)
            db.add(interest)
    
    db.commit()
    
    return {"status": "updated", "interests_count": len(category_slugs)}


@router.get("/me/history")
async def get_history(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get watch history"""
    history = db.query(UserHistory).filter(
        UserHistory.user_id == user.id
    ).order_by(
        UserHistory.watched_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "history": [
            {
                "id": h.id,
                "segment": {
                    "id": h.segment.id,
                    "title": h.segment.generated_title,
                    "thumbnail_url": h.segment.video.thumbnail_url,
                    "youtube_id": h.segment.video.youtube_id,
                    "start_time": h.segment.start_time,
                    "channel_name": h.segment.video.channel.name,
                },
                "watched_at": h.watched_at,
                "watch_duration": h.watch_duration_seconds,
                "completed": h.completed,
            }
            for h in history
        ]
    }


@router.post("/me/history")
async def add_history(
    data: HistoryCreate,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Add to watch history"""
    segment = db.query(Segment).filter(Segment.id == data.segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    history = UserHistory(
        user_id=user.id,
        segment_id=data.segment_id,
        watch_duration_seconds=data.watch_duration_seconds or 0,
        completed=data.completed or False
    )
    db.add(history)
    db.commit()
    
    return {"status": "added"}


@router.get("/me/saved")
async def get_saved_segments(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get saved segments"""
    saved = db.query(SavedSegment).filter(
        SavedSegment.user_id == user.id
    ).order_by(
        SavedSegment.saved_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "saved": [
            {
                "segment": {
                    "id": s.segment.id,
                    "title": s.segment.generated_title,
                    "summary": s.segment.summary_text,
                    "thumbnail_url": s.segment.video.thumbnail_url,
                    "youtube_id": s.segment.video.youtube_id,
                    "start_time": s.segment.start_time,
                    "end_time": s.segment.end_time,
                    "channel_name": s.segment.video.channel.name,
                },
                "saved_at": s.saved_at,
            }
            for s in saved
        ]
    }


@router.post("/me/saved/{segment_id}")
async def save_segment(
    segment_id: str,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Save a segment"""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    # Check if already saved
    existing = db.query(SavedSegment).filter(
        SavedSegment.user_id == user.id,
        SavedSegment.segment_id == segment_id
    ).first()
    
    if existing:
        return {"status": "already_saved"}
    
    saved = SavedSegment(user_id=user.id, segment_id=segment_id)
    db.add(saved)
    
    # Increment save count on segment
    segment.save_count += 1
    
    db.commit()
    
    return {"status": "saved"}


@router.delete("/me/saved/{segment_id}")
async def unsave_segment(
    segment_id: str,
    user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Remove a saved segment"""
    saved = db.query(SavedSegment).filter(
        SavedSegment.user_id == user.id,
        SavedSegment.segment_id == segment_id
    ).first()
    
    if not saved:
        raise HTTPException(status_code=404, detail="Saved segment not found")
    
    # Decrement save count
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if segment and segment.save_count > 0:
        segment.save_count -= 1
    
    db.delete(saved)
    db.commit()
    
    return {"status": "removed"}

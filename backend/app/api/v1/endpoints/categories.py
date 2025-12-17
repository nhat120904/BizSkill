from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.db.session import get_db
from app.db.models.category import Category, SegmentCategory
from app.db.models.segment import Segment
from app.db.models.video import Video, VideoStatus
from app.schemas import CategoryResponse

router = APIRouter()


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@router.post("")
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db)
):
    """Create a new category"""
    # Check if exists
    existing = db.query(Category).filter(
        (Category.slug == category_data.slug) | (Category.name == category_data.name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Category already exists")
    
    category = Category(
        name=category_data.name,
        slug=category_data.slug,
        description=category_data.description,
        icon=category_data.icon,
        color=category_data.color,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "icon": category.icon,
        "color": category.color,
    }


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    db: Session = Depends(get_db)
):
    """List all categories with segment counts"""
    categories = db.query(Category).order_by(Category.name).all()
    
    results = []
    for cat in categories:
        # Count segments in this category
        segment_count = db.query(SegmentCategory).join(
            Segment, SegmentCategory.segment_id == Segment.id
        ).join(
            Video, Segment.video_id == Video.id
        ).filter(
            SegmentCategory.category_id == cat.id,
            Video.status == VideoStatus.INDEXED.value
        ).count()
        
        results.append({
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "icon": cat.icon,
            "color": cat.color,
            "segment_count": segment_count,
        })
    
    return results


@router.get("/{slug}")
async def get_category(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get category details with top segments"""
    category = db.query(Category).filter(Category.slug == slug).first()
    
    if not category:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get top segments
    top_segments = db.query(Segment).join(
        SegmentCategory, Segment.id == SegmentCategory.segment_id
    ).join(
        Video, Segment.video_id == Video.id
    ).filter(
        SegmentCategory.category_id == category.id,
        Video.status == VideoStatus.INDEXED.value
    ).order_by(
        Segment.relevance_score.desc(),
        Segment.view_count.desc()
    ).limit(10).all()
    
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "icon": category.icon,
        "color": category.color,
        "top_segments": [
            {
                "id": s.id,
                "title": s.generated_title,
                "summary": s.summary_text,
                "relevance_score": s.relevance_score,
                "video": {
                    "youtube_id": s.video.youtube_id,
                    "thumbnail_url": s.video.thumbnail_url,
                },
                "channel": {
                    "id": str(s.video.channel.id),
                    "name": s.video.channel.name,
                }
            }
            for s in top_segments
        ]
    }


@router.get("/{slug}/segments")
async def get_category_segments(
    slug: str,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get paginated segments for a category"""
    category = db.query(Category).filter(Category.slug == slug).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    offset = (page - 1) * limit
    
    # Get total count
    total = db.query(Segment).join(
        SegmentCategory, Segment.id == SegmentCategory.segment_id
    ).join(
        Video, Segment.video_id == Video.id
    ).filter(
        SegmentCategory.category_id == category.id,
        Video.status == VideoStatus.INDEXED.value
    ).count()
    
    # Get paginated segments
    segments = db.query(Segment).join(
        SegmentCategory, Segment.id == SegmentCategory.segment_id
    ).join(
        Video, Segment.video_id == Video.id
    ).filter(
        SegmentCategory.category_id == category.id,
        Video.status == VideoStatus.INDEXED.value
    ).order_by(
        Segment.relevance_score.desc(),
        Segment.view_count.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "category": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "icon": category.icon,
            "color": category.color,
        },
        "segments": [
            {
                "id": str(s.id),
                "title": s.generated_title,
                "summary": s.summary_text,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.end_time - s.start_time if s.end_time and s.start_time else 0,
                "relevance_score": s.relevance_score,
                "view_count": s.view_count,
                "video": {
                    "youtube_id": s.video.youtube_id,
                    "title": s.video.original_title,
                    "thumbnail_url": s.video.thumbnail_url,
                },
                "channel": {
                    "id": str(s.video.channel.id) if s.video.channel else None,
                    "name": s.video.channel.name if s.video.channel else "Unknown",
                    "thumbnail_url": s.video.channel.thumbnail_url if s.video.channel else None,
                }
            }
            for s in segments
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        }
    }

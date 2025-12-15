from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.segment import Segment
from app.db.models.video import Video, VideoStatus
from app.db.models.channel import Channel
from app.db.models.category import SegmentCategory, Category
from app.schemas import SegmentResponse, SegmentDetail

router = APIRouter()


@router.get("", response_model=List[SegmentResponse])
async def list_segments(
    skip: int = 0,
    limit: int = Query(default=20, le=100),
    category: Optional[str] = None,
    min_relevance: int = Query(default=1, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """List segments (public)"""
    query = db.query(Segment).join(Video).join(Channel).filter(
        Video.status == VideoStatus.INDEXED.value,
        Segment.relevance_score >= min_relevance
    )
    
    if category:
        query = query.join(SegmentCategory).join(Category).filter(
            Category.slug == category
        )
    
    query = query.order_by(Segment.relevance_score.desc(), Segment.created_at.desc())
    segments = query.offset(skip).limit(limit).all()
    
    results = []
    for segment in segments:
        categories = [sc.category.name for sc in segment.categories]
        results.append({
            "id": segment.id,
            "generated_title": segment.generated_title,
            "summary_text": segment.summary_text,
            "key_takeaways": segment.key_takeaways or [],
            "relevance_score": segment.relevance_score,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
            "duration": segment.end_time - segment.start_time,
            "view_count": segment.view_count,
            "video": {
                "youtube_id": segment.video.youtube_id,
                "original_title": segment.video.original_title,
                "thumbnail_url": segment.video.thumbnail_url,
                "duration_seconds": segment.video.duration_seconds,
            },
            "channel": {
                "youtube_channel_id": segment.video.channel.youtube_channel_id,
                "name": segment.video.channel.name,
                "thumbnail_url": segment.video.channel.thumbnail_url,
            },
            "categories": categories,
        })
    
    return results


@router.get("/feed")
async def get_feed(
    type: str = Query(default="trending", pattern="^(trending|latest)$"),
    category: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get segment feed (public)"""
    from app.services.embedding_service import EmbeddingService
    from app.services.search_service import SearchService
    
    embedding_service = EmbeddingService()
    search_service = SearchService(db, embedding_service)
    
    offset = (page - 1) * limit
    
    if type == "trending":
        segments = search_service.get_trending_segments(
            limit=limit,
            category=category,
            min_relevance=5
        )
    else:  # latest
        query = db.query(Segment).join(Video).join(Channel).filter(
            Video.status == VideoStatus.INDEXED.value,
            Segment.relevance_score >= 5
        )
        
        if category:
            query = query.join(SegmentCategory).join(Category).filter(
                Category.slug == category
            )
        
        query = query.order_by(Segment.created_at.desc())
        results = query.offset(offset).limit(limit).all()
        
        segments = [
            {
                "id": str(s.id),
                "title": s.generated_title,
                "summary": s.summary_text,
                "key_takeaways": s.key_takeaways or [],
                "relevance_score": s.relevance_score,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.end_time - s.start_time,
                "view_count": s.view_count,
                "video": {
                    "id": str(s.video.id),
                    "youtube_id": s.video.youtube_id,
                    "title": s.video.original_title,
                    "thumbnail_url": s.video.thumbnail_url,
                },
                "channel": {
                    "name": s.video.channel.name,
                    "thumbnail_url": s.video.channel.thumbnail_url,
                },
                "categories": [sc.category.name for sc in s.categories],
            }
            for s in results
        ]
    
    return {
        "type": type,
        "category": category,
        "page": page,
        "limit": limit,
        "results": segments
    }


@router.get("/{segment_id}", response_model=SegmentDetail)
async def get_segment(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """Get segment details (public)"""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    # Increment view count
    segment.view_count += 1
    db.commit()
    
    categories = [sc.category.name for sc in segment.categories]
    
    return {
        "id": segment.id,
        "generated_title": segment.generated_title,
        "summary_text": segment.summary_text,
        "key_takeaways": segment.key_takeaways or [],
        "relevance_score": segment.relevance_score,
        "start_time": segment.start_time,
        "end_time": segment.end_time,
        "duration": segment.end_time - segment.start_time,
        "view_count": segment.view_count,
        "transcript_chunk": segment.transcript_chunk,
        "video": {
            "youtube_id": segment.video.youtube_id,
            "original_title": segment.video.original_title,
            "description": segment.video.description,
            "thumbnail_url": segment.video.thumbnail_url,
            "duration_seconds": segment.video.duration_seconds,
        },
        "channel": {
            "youtube_channel_id": segment.video.channel.youtube_channel_id,
            "name": segment.video.channel.name,
            "description": segment.video.channel.description,
            "thumbnail_url": segment.video.channel.thumbnail_url,
        },
        "categories": categories,
    }


@router.get("/{segment_id}/related", response_model=List[SegmentResponse])
async def get_related_segments(
    segment_id: str,
    limit: int = Query(default=10, le=20),
    db: Session = Depends(get_db)
):
    """Get related segments (public)"""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    # Use semantic search to find related
    from app.services.embedding_service import EmbeddingService
    
    embedding_service = EmbeddingService()
    
    # Search using segment's title and summary
    query_text = f"{segment.generated_title} {segment.summary_text}"
    
    results = embedding_service.semantic_search(
        query=query_text,
        limit=limit + 1,  # +1 to exclude self
        min_score=0.5
    )
    
    # Exclude the current segment
    related_ids = [
        r['segment_id'] for r in results 
        if r['segment_id'] != str(segment_id)
    ][:limit]
    
    if not related_ids:
        return []
    
    # Fetch full segment data
    related = db.query(Segment).filter(Segment.id.in_(related_ids)).all()
    
    return [
        {
            "id": s.id,
            "generated_title": s.generated_title,
            "summary_text": s.summary_text,
            "key_takeaways": s.key_takeaways or [],
            "relevance_score": s.relevance_score,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "duration": s.end_time - s.start_time,
            "view_count": s.view_count,
            "video": {
                "youtube_id": s.video.youtube_id,
                "original_title": s.video.original_title,
                "thumbnail_url": s.video.thumbnail_url,
                "duration_seconds": s.video.duration_seconds,
            },
            "channel": {
                "youtube_channel_id": s.video.channel.youtube_channel_id,
                "name": s.video.channel.name,
                "thumbnail_url": s.video.channel.thumbnail_url,
            },
            "categories": [sc.category.name for sc in s.categories],
        }
        for s in related
    ]

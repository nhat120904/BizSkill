from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import structlog
from app.db.session import get_db
from app.db.models.segment import Segment
from app.db.models.video import Video, VideoStatus
from app.db.models.channel import Channel
from app.db.models.category import SegmentCategory, Category
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService
from app.schemas import SearchResponse

router = APIRouter()
logger = structlog.get_logger()


def fallback_text_search(
    db: Session,
    query: str,
    limit: int = 20,
    category: Optional[str] = None,
    min_relevance: int = 1
) -> list:
    """
    Fallback text search using PostgreSQL LIKE/ILIKE when embedding fails.
    """
    logger.info("Using fallback text search", query=query)
    
    # Build base query
    base_query = db.query(Segment).join(Video).join(Channel).filter(
        Video.status == VideoStatus.INDEXED.value,
        Segment.relevance_score >= min_relevance
    )
    
    # Text search on title, summary, transcript
    search_terms = query.lower().split()
    conditions = []
    for term in search_terms:
        pattern = f"%{term}%"
        conditions.append(
            or_(
                func.lower(Segment.generated_title).like(pattern),
                func.lower(Segment.summary_text).like(pattern),
                func.lower(Segment.transcript_chunk).like(pattern)
            )
        )
    
    if conditions:
        base_query = base_query.filter(or_(*conditions))
    
    # Category filter
    if category:
        base_query = base_query.join(SegmentCategory).join(Category).filter(
            Category.slug == category
        )
    
    # Order by relevance score
    segments = base_query.order_by(
        Segment.relevance_score.desc(),
        Segment.view_count.desc()
    ).limit(limit).all()
    
    # Format results
    results = []
    for i, s in enumerate(segments):
        categories = [sc.category.name for sc in s.categories]
        # Generate a fake search score based on position and relevance
        search_score = 0.9 - (i * 0.05)  # Decreasing score for ranking
        results.append({
            "id": str(s.id),
            "title": s.generated_title,
            "summary": s.summary_text,
            "key_takeaways": s.key_takeaways or [],
            "relevance_score": s.relevance_score,
            "search_score": max(search_score, 0.1),
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
                "id": str(s.video.channel.id),
                "name": s.video.channel.name,
                "thumbnail_url": s.video.channel.thumbnail_url,
            },
            "categories": categories,
            "search_method": "text_fallback"
        })
    
    logger.info("Fallback search results", count=len(results))
    return results


@router.get("", response_model=SearchResponse)
async def search_segments(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category slug"),
    min_relevance: int = Query(1, ge=1, le=10, description="Minimum relevance score"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Results per page"),
    db: Session = Depends(get_db)
):
    """
    Search for video segments using hybrid search (semantic + keyword)
    Falls back to text search if embedding service fails.
    
    Examples:
    - "how to negotiate salary"
    - "dealing with difficult coworkers"
    - "time management tips"
    """
    try:
        embedding_service = EmbeddingService()
        search_service = SearchService(db, embedding_service)
        
        results = search_service.hybrid_search(
            query=q,
            limit=limit,
            category=category,
            min_relevance=min_relevance
        )
    except Exception as e:
        # Fallback to text search when embedding fails
        logger.warning("Semantic search failed, using fallback", error=str(e))
        results = fallback_text_search(
            db=db,
            query=q,
            limit=limit,
            category=category,
            min_relevance=min_relevance
        )
    
    return SearchResponse(
        query=q,
        total=len(results),
        page=page,
        limit=limit,
        results=results
    )


@router.get("/text")
async def text_search_segments(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category slug"),
    min_relevance: int = Query(1, ge=1, le=10, description="Minimum relevance score"),
    limit: int = Query(20, ge=1, le=50, description="Results per page"),
    db: Session = Depends(get_db)
):
    """
    Text-only search (no embeddings required).
    Use this endpoint when embedding service is unavailable.
    """
    results = fallback_text_search(
        db=db,
        query=q,
        limit=limit,
        category=category,
        min_relevance=min_relevance
    )
    
    return {
        "query": q,
        "total": len(results),
        "method": "text_search",
        "results": results
    }


@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on existing segment titles"""
    # Simple prefix matching on titles
    suggestions = db.query(
        Segment.generated_title
    ).join(Video).filter(
        Video.status == VideoStatus.INDEXED.value,
        func.lower(Segment.generated_title).contains(q.lower())
    ).distinct().limit(limit).all()
    
    return {
        "query": q,
        "suggestions": [s[0] for s in suggestions]
    }

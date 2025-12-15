from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService
from app.schemas import SearchResponse

router = APIRouter()


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
    
    Examples:
    - "how to negotiate salary"
    - "dealing with difficult coworkers"
    - "time management tips"
    """
    embedding_service = EmbeddingService()
    search_service = SearchService(db, embedding_service)
    
    results = search_service.hybrid_search(
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


@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on existing segment titles"""
    from app.db.models.segment import Segment
    from app.db.models.video import Video, VideoStatus
    from sqlalchemy import func
    
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

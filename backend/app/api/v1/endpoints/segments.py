from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
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
                "id": str(segment.video.channel.id),
                "youtube_channel_id": segment.video.channel.youtube_channel_id,
                "name": segment.video.channel.name,
                "thumbnail_url": segment.video.channel.thumbnail_url,
            },
            "categories": categories,
        })
    
    return results


@router.get("/feed")
async def get_feed(
    type: str = Query(default="trending", pattern="^(trending|latest|random)$"),
    category: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get segment feed (public)"""
    from app.services.embedding_service import EmbeddingService
    from app.services.search_service import SearchService
    from sqlalchemy.sql.expression import func as sql_func
    
    embedding_service = EmbeddingService()
    search_service = SearchService(db, embedding_service)
    
    offset = (page - 1) * limit
    
    if type == "trending":
        segments = search_service.get_trending_segments(
            limit=limit,
            category=category,
            min_relevance=5
        )
    elif type == "random":
        # Random segments
        query = db.query(Segment).join(Video).join(Channel).filter(
            Video.status == VideoStatus.INDEXED.value,
            Segment.relevance_score >= 5
        )
        
        if category:
            query = query.join(SegmentCategory).join(Category).filter(
                Category.slug == category
            )
        
        # Order randomly
        query = query.order_by(sql_func.random())
        results = query.limit(limit).all()
        
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
                    "id": str(s.video.channel.id),
                    "name": s.video.channel.name,
                    "thumbnail_url": s.video.channel.thumbnail_url,
                },
                "categories": [sc.category.name for sc in s.categories],
            }
            for s in results
        ]
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
                    "id": str(s.video.channel.id),
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
            "id": str(segment.video.channel.id),
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
                "id": str(s.video.channel.id),
                "youtube_channel_id": s.video.channel.youtube_channel_id,
                "name": s.video.channel.name,
                "thumbnail_url": s.video.channel.thumbnail_url,
            },
            "categories": [sc.category.name for sc in s.categories],
        }
        for s in related
    ]


# ============== EXPORT API FOR THIRD PARTY ==============

@router.get("/export/all")
async def export_all_segments(
    format: str = Query(default="json", pattern="^(json|embed)$"),
    category: Optional[str] = None,
    min_relevance: int = Query(default=5, ge=1, le=10),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Export all segments for third-party integration.
    
    **Formats:**
    - `json`: Full segment data with metadata
    - `embed`: Simplified format with YouTube embed URLs
    
    **Usage for embedding videos:**
    Each segment includes `embed_url` which can be used directly in an iframe:
    ```html
    <iframe src="{embed_url}" frameborder="0" allowfullscreen></iframe>
    ```
    """
    query = db.query(Segment).join(Video).join(Channel).filter(
        Video.status == VideoStatus.INDEXED.value,
        Segment.relevance_score >= min_relevance
    )
    
    if category:
        query = query.join(SegmentCategory).join(Category).filter(
            Category.slug == category
        )
    
    segments = query.order_by(
        Segment.relevance_score.desc()
    ).limit(limit).all()
    
    if format == "embed":
        # Simplified format for embedding
        return {
            "count": len(segments),
            "segments": [
                {
                    "id": str(s.id),
                    "title": s.generated_title,
                    "summary": s.summary_text,
                    "youtube_id": s.video.youtube_id,
                    "start_seconds": int(s.start_time),
                    "end_seconds": int(s.end_time),
                    "duration_seconds": int(s.end_time - s.start_time),
                    "embed_url": f"https://www.youtube.com/embed/{s.video.youtube_id}?start={int(s.start_time)}&end={int(s.end_time)}&autoplay=0",
                    "watch_url": f"https://www.youtube.com/watch?v={s.video.youtube_id}&t={int(s.start_time)}s",
                    "thumbnail_url": s.video.thumbnail_url or f"https://img.youtube.com/vi/{s.video.youtube_id}/hqdefault.jpg",
                    "channel_name": s.video.channel.name,
                    "categories": [sc.category.name for sc in s.categories],
                }
                for s in segments
            ]
        }
    
    # Full JSON format
    return {
        "count": len(segments),
        "export_date": datetime.utcnow().isoformat(),
        "segments": [
            {
                "id": str(s.id),
                "title": s.generated_title,
                "summary": s.summary_text,
                "key_takeaways": s.key_takeaways or [],
                "relevance_score": s.relevance_score,
                "categories": [sc.category.name for sc in s.categories],
                "timing": {
                    "start_seconds": int(s.start_time),
                    "end_seconds": int(s.end_time),
                    "duration_seconds": int(s.end_time - s.start_time),
                },
                "youtube": {
                    "video_id": s.video.youtube_id,
                    "video_title": s.video.original_title,
                    "channel_id": s.video.channel.youtube_channel_id,
                    "channel_name": s.video.channel.name,
                    "thumbnail_url": s.video.thumbnail_url,
                    "embed_url": f"https://www.youtube.com/embed/{s.video.youtube_id}?start={int(s.start_time)}&end={int(s.end_time)}",
                    "watch_url": f"https://www.youtube.com/watch?v={s.video.youtube_id}&t={int(s.start_time)}s",
                },
                "stats": {
                    "view_count": s.view_count,
                    "video_views": s.video.view_count,
                },
                "transcript": s.transcript_chunk[:500] if s.transcript_chunk else None,
            }
            for s in segments
        ]
    }


@router.get("/export/{segment_id}")
async def export_single_segment(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """
    Export a single segment with all embed information.
    
    Returns complete data needed to embed and display the video segment.
    """
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    youtube_id = segment.video.youtube_id
    start = int(segment.start_time)
    end = int(segment.end_time)
    
    return {
        "id": str(segment.id),
        "title": segment.generated_title,
        "summary": segment.summary_text,
        "key_takeaways": segment.key_takeaways or [],
        "transcript": segment.transcript_chunk,
        "relevance_score": segment.relevance_score,
        "categories": [sc.category.name for sc in segment.categories],
        
        # Timing info
        "timing": {
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": end - start,
            "start_formatted": f"{start // 60}:{start % 60:02d}",
            "end_formatted": f"{end // 60}:{end % 60:02d}",
        },
        
        # YouTube embed info
        "youtube": {
            "video_id": youtube_id,
            "video_title": segment.video.original_title,
            "video_duration": segment.video.duration_seconds,
            "channel_id": segment.video.channel.youtube_channel_id,
            "channel_name": segment.video.channel.name,
            "channel_thumbnail": segment.video.channel.thumbnail_url,
        },
        
        # Ready-to-use URLs
        "urls": {
            "embed": f"https://www.youtube.com/embed/{youtube_id}?start={start}&end={end}&autoplay=0&rel=0",
            "embed_autoplay": f"https://www.youtube.com/embed/{youtube_id}?start={start}&end={end}&autoplay=1&rel=0",
            "watch": f"https://www.youtube.com/watch?v={youtube_id}&t={start}s",
            "thumbnail": segment.video.thumbnail_url or f"https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg",
            "thumbnail_hq": f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg",
            "thumbnail_mq": f"https://img.youtube.com/vi/{youtube_id}/mqdefault.jpg",
        },
        
        # Ready-to-use HTML snippets
        "html": {
            "iframe_responsive": f'''<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;">
  <iframe 
    src="https://www.youtube.com/embed/{youtube_id}?start={start}&end={end}&rel=0" 
    style="position:absolute;top:0;left:0;width:100%;height:100%;" 
    frameborder="0" 
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
    allowfullscreen>
  </iframe>
</div>''',
            "iframe_fixed": f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{youtube_id}?start={start}&end={end}&rel=0" frameborder="0" allowfullscreen></iframe>',
        },
        
        # JavaScript player config
        "player_config": {
            "videoId": youtube_id,
            "playerVars": {
                "start": start,
                "end": end,
                "autoplay": 0,
                "rel": 0,
                "modestbranding": 1,
            }
        }
    }


from datetime import datetime

@router.get("/export/download/json")
async def download_segments_json(
    category: Optional[str] = None,
    min_relevance: int = Query(default=5, ge=1, le=10),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """
    Download segments as a JSON file.
    
    This endpoint returns a downloadable JSON file with all segment data.
    """
    query = db.query(Segment).join(Video).join(Channel).filter(
        Video.status == VideoStatus.INDEXED.value,
        Segment.relevance_score >= min_relevance
    )
    
    if category:
        query = query.join(SegmentCategory).join(Category).filter(
            Category.slug == category
        )
    
    segments = query.order_by(Segment.relevance_score.desc()).limit(limit).all()
    
    export_data = {
        "export_info": {
            "source": "BizSkill",
            "export_date": datetime.utcnow().isoformat(),
            "total_segments": len(segments),
            "filters": {
                "category": category,
                "min_relevance": min_relevance,
            }
        },
        "segments": [
            {
                "id": str(s.id),
                "title": s.generated_title,
                "summary": s.summary_text,
                "key_takeaways": s.key_takeaways or [],
                "relevance_score": s.relevance_score,
                "categories": [sc.category.name for sc in s.categories],
                "youtube_id": s.video.youtube_id,
                "start_seconds": int(s.start_time),
                "end_seconds": int(s.end_time),
                "duration_seconds": int(s.end_time - s.start_time),
                "embed_url": f"https://www.youtube.com/embed/{s.video.youtube_id}?start={int(s.start_time)}&end={int(s.end_time)}",
                "watch_url": f"https://www.youtube.com/watch?v={s.video.youtube_id}&t={int(s.start_time)}s",
                "thumbnail_url": s.video.thumbnail_url,
                "channel_name": s.video.channel.name,
                "video_title": s.video.original_title,
            }
            for s in segments
        ]
    }
    
    import json
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=bizskill_segments_{datetime.utcnow().strftime('%Y%m%d')}.json"
        }
    )


# ============== CLOUDINARY VIDEO CLIPS EXPORT ==============

@router.get("/export/clips/all")
async def export_cloudinary_clips(
    category: Optional[str] = None,
    min_relevance: int = Query(default=5, ge=1, le=10),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Export all video clips with Cloudinary URLs.
    
    These are actual downloadable/streamable video files hosted on Cloudinary,
    already cut to the segment duration. Perfect for third-party integration.
    
    **Returns:**
    - Direct video URLs (mp4)
    - Thumbnail URLs
    - All segment metadata
    """
    query = db.query(Segment).join(Video).join(Channel).filter(
        Video.status == VideoStatus.INDEXED.value,
        Segment.relevance_score >= min_relevance,
        Segment.clip_status == "ready",
        Segment.cloudinary_url != None
    )
    
    if category:
        query = query.join(SegmentCategory).join(Category).filter(
            Category.slug == category
        )
    
    segments = query.order_by(
        Segment.relevance_score.desc()
    ).limit(limit).all()
    
    return {
        "count": len(segments),
        "export_date": datetime.utcnow().isoformat(),
        "note": "These are direct video file URLs hosted on Cloudinary",
        "clips": [
            {
                "id": str(s.id),
                "title": s.generated_title,
                "summary": s.summary_text,
                "key_takeaways": s.key_takeaways or [],
                "relevance_score": s.relevance_score,
                "categories": [sc.category.name for sc in s.categories],
                "duration_seconds": int(s.end_time - s.start_time),
                
                # Cloudinary URLs (direct video files)
                "video_url": s.cloudinary_url,
                "thumbnail_url": s.cloudinary_thumbnail_url,
                "cloudinary_public_id": s.cloudinary_public_id,
                
                # Original YouTube info (for reference)
                "source": {
                    "youtube_id": s.video.youtube_id,
                    "video_title": s.video.original_title,
                    "channel_name": s.video.channel.name,
                    "start_seconds": int(s.start_time),
                    "end_seconds": int(s.end_time),
                },
            }
            for s in segments
        ]
    }


@router.get("/export/clips/download")
async def download_clips_json(
    category: Optional[str] = None,
    min_relevance: int = Query(default=5, ge=1, le=10),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """
    Download all Cloudinary clips as a JSON file.
    
    Perfect for importing into third-party systems.
    """
    query = db.query(Segment).join(Video).join(Channel).filter(
        Video.status == VideoStatus.INDEXED.value,
        Segment.relevance_score >= min_relevance,
        Segment.clip_status == "ready",
        Segment.cloudinary_url != None
    )
    
    if category:
        query = query.join(SegmentCategory).join(Category).filter(
            Category.slug == category
        )
    
    segments = query.order_by(Segment.relevance_score.desc()).limit(limit).all()
    
    export_data = {
        "export_info": {
            "source": "BizSkill",
            "type": "cloudinary_clips",
            "export_date": datetime.utcnow().isoformat(),
            "total_clips": len(segments),
            "filters": {
                "category": category,
                "min_relevance": min_relevance,
            }
        },
        "clips": [
            {
                "id": str(s.id),
                "title": s.generated_title,
                "summary": s.summary_text,
                "key_takeaways": s.key_takeaways or [],
                "categories": [sc.category.name for sc in s.categories],
                "duration_seconds": int(s.end_time - s.start_time),
                "video_url": s.cloudinary_url,
                "thumbnail_url": s.cloudinary_thumbnail_url,
                "channel_name": s.video.channel.name,
                "source_youtube_id": s.video.youtube_id,
            }
            for s in segments
        ]
    }
    
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=bizskill_clips_{datetime.utcnow().strftime('%Y%m%d')}.json"
        }
    )


@router.get("/export/clips/{segment_id}")
async def export_single_clip(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """
    Export a single video clip with Cloudinary URL.
    
    Returns complete data for embedding or playing the clip.
    """
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    if segment.clip_status != "ready" or not segment.cloudinary_url:
        raise HTTPException(
            status_code=404, 
            detail=f"Clip not ready. Status: {segment.clip_status}"
        )
    
    return {
        "id": str(segment.id),
        "title": segment.generated_title,
        "summary": segment.summary_text,
        "key_takeaways": segment.key_takeaways or [],
        "transcript": segment.transcript_chunk,
        "relevance_score": segment.relevance_score,
        "categories": [sc.category.name for sc in segment.categories],
        "duration_seconds": int(segment.end_time - segment.start_time),
        
        # Cloudinary video
        "cloudinary": {
            "video_url": segment.cloudinary_url,
            "thumbnail_url": segment.cloudinary_thumbnail_url,
            "public_id": segment.cloudinary_public_id,
            "processed_at": segment.clip_processed_at.isoformat() if segment.clip_processed_at else None,
        },
        
        # Ready-to-use HTML
        "html": {
            "video_tag": f'<video src="{segment.cloudinary_url}" controls poster="{segment.cloudinary_thumbnail_url}" width="100%"></video>',
            "video_responsive": f'''<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;">
  <video 
    src="{segment.cloudinary_url}" 
    poster="{segment.cloudinary_thumbnail_url}"
    controls 
    style="position:absolute;top:0;left:0;width:100%;height:100%;">
  </video>
</div>''',
        },
        
        # Source info
        "source": {
            "youtube_id": segment.video.youtube_id,
            "video_title": segment.video.original_title,
            "channel_name": segment.video.channel.name,
            "channel_thumbnail": segment.video.channel.thumbnail_url,
            "original_start": int(segment.start_time),
            "original_end": int(segment.end_time),
            "youtube_watch_url": f"https://www.youtube.com/watch?v={segment.video.youtube_id}&t={int(segment.start_time)}s",
        }
    }

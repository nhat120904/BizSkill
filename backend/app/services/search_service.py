from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import structlog
from app.services.embedding_service import EmbeddingService
from app.db.models.segment import Segment
from app.db.models.video import Video
from app.db.models.channel import Channel
from app.db.models.category import SegmentCategory, Category

logger = structlog.get_logger()


class SearchService:
    """Hybrid search combining semantic and keyword search"""
    
    def __init__(self, db: Session, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service
    
    def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        category: Optional[str] = None,
        min_relevance: int = 1,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining:
        1. Semantic search via Qdrant (vector similarity)
        2. Keyword search via PostgreSQL full-text search
        """
        # Get double the results for merging
        fetch_limit = limit * 2
        
        # 1. Semantic Search
        categories_filter = [category] if category else None
        semantic_results = self.embedding_service.semantic_search(
            query=query,
            limit=fetch_limit,
            min_relevance=min_relevance,
            categories=categories_filter,
            min_score=0.3
        )
        
        # 2. Keyword Search
        keyword_results = self._keyword_search(
            query=query,
            limit=fetch_limit,
            category=category,
            min_relevance=min_relevance
        )
        
        # 3. Merge using Reciprocal Rank Fusion
        merged = self._reciprocal_rank_fusion(
            semantic_results,
            keyword_results,
            semantic_weight,
            keyword_weight
        )
        
        # 4. Enrich with full segment data
        enriched = self._enrich_results(merged[:limit])
        
        return enriched
    
    def _keyword_search(
        self,
        query: str,
        limit: int = 40,
        category: Optional[str] = None,
        min_relevance: int = 1
    ) -> List[Dict[str, Any]]:
        """Full-text search using PostgreSQL"""
        # Build the query
        base_query = self.db.query(
            Segment.id,
            Segment.generated_title,
            Segment.summary_text,
            Segment.relevance_score,
            Segment.video_id,
            Video.youtube_id,
            Channel.name.label('channel_name'),
            # Full text search rank
            func.ts_rank(
                func.to_tsvector('english', 
                    func.coalesce(Segment.generated_title, '') + ' ' + 
                    func.coalesce(Segment.summary_text, '') + ' ' +
                    func.coalesce(Segment.transcript_chunk, '')
                ),
                func.plainto_tsquery('english', query)
            ).label('rank')
        ).join(
            Video, Segment.video_id == Video.id
        ).join(
            Channel, Video.channel_id == Channel.id
        ).filter(
            Video.status == 'indexed',
            Segment.relevance_score >= min_relevance
        )
        
        # Add category filter
        if category:
            base_query = base_query.join(
                SegmentCategory, Segment.id == SegmentCategory.segment_id
            ).join(
                Category, SegmentCategory.category_id == Category.id
            ).filter(
                Category.slug == category
            )
        
        # Add text search filter
        base_query = base_query.filter(
            func.to_tsvector('english', 
                func.coalesce(Segment.generated_title, '') + ' ' + 
                func.coalesce(Segment.summary_text, '')
            ).match(query)
        )
        
        # Order by rank
        results = base_query.order_by(text('rank DESC')).limit(limit).all()
        
        return [
            {
                'segment_id': str(r.id),
                'title': r.generated_title,
                'summary': r.summary_text,
                'relevance_score': r.relevance_score,
                'video_id': str(r.video_id),
                'youtube_id': r.youtube_id,
                'channel_name': r.channel_name,
                'keyword_rank': float(r.rank) if r.rank else 0
            }
            for r in results
        ]
    
    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[Dict],
        keyword_results: List[Dict],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """Merge results using Reciprocal Rank Fusion"""
        scores = {}
        
        # Score semantic results
        for rank, result in enumerate(semantic_results):
            segment_id = result['segment_id']
            rrf_score = semantic_weight / (k + rank + 1)
            scores[segment_id] = {
                'rrf_score': rrf_score,
                'semantic_score': result.get('score', 0),
                **result
            }
        
        # Add keyword results
        for rank, result in enumerate(keyword_results):
            segment_id = result['segment_id']
            rrf_score = keyword_weight / (k + rank + 1)
            
            if segment_id in scores:
                scores[segment_id]['rrf_score'] += rrf_score
                scores[segment_id]['keyword_rank'] = result.get('keyword_rank', 0)
            else:
                scores[segment_id] = {
                    'rrf_score': rrf_score,
                    'keyword_rank': result.get('keyword_rank', 0),
                    **result
                }
        
        # Sort by combined score
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )
        
        return sorted_results
    
    def _enrich_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Enrich search results with full segment and video data"""
        if not results:
            return []
        
        segment_ids = [r['segment_id'] for r in results]
        
        # Fetch full segment data
        segments = self.db.query(
            Segment,
            Video,
            Channel
        ).join(
            Video, Segment.video_id == Video.id
        ).join(
            Channel, Video.channel_id == Channel.id
        ).filter(
            Segment.id.in_(segment_ids)
        ).all()
        
        # Build lookup
        segment_lookup = {
            str(s.Segment.id): {
                'segment': s.Segment,
                'video': s.Video,
                'channel': s.Channel
            }
            for s in segments
        }
        
        # Enrich results
        enriched = []
        for r in results:
            segment_id = r['segment_id']
            if segment_id not in segment_lookup:
                continue
            
            data = segment_lookup[segment_id]
            segment = data['segment']
            video = data['video']
            channel = data['channel']
            
            # Get categories
            categories = [sc.category.name for sc in segment.categories]
            
            enriched.append({
                'id': str(segment.id),
                'title': segment.generated_title,
                'summary': segment.summary_text,
                'key_takeaways': segment.key_takeaways or [],
                'relevance_score': segment.relevance_score,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'duration': segment.end_time - segment.start_time,
                'view_count': segment.view_count,
                'video': {
                    'id': str(video.id),
                    'youtube_id': video.youtube_id,
                    'title': video.original_title,
                    'thumbnail_url': video.thumbnail_url,
                    'duration': video.duration_seconds,
                },
                'channel': {
                    'id': str(channel.id),
                    'name': channel.name,
                    'thumbnail_url': channel.thumbnail_url,
                },
                'categories': categories,
                'search_score': r.get('rrf_score', 0),
            })
        
        return enriched
    
    def get_trending_segments(
        self,
        limit: int = 20,
        category: Optional[str] = None,
        min_relevance: int = 6
    ) -> List[Dict[str, Any]]:
        """Get trending segments based on view count and relevance"""
        query = self.db.query(
            Segment,
            Video,
            Channel
        ).join(
            Video, Segment.video_id == Video.id
        ).join(
            Channel, Video.channel_id == Channel.id
        ).filter(
            Video.status == 'indexed',
            Segment.relevance_score >= min_relevance
        )
        
        if category:
            query = query.join(
                SegmentCategory, Segment.id == SegmentCategory.segment_id
            ).join(
                Category, SegmentCategory.category_id == Category.id
            ).filter(Category.slug == category)
        
        # Order by a combination of recency, views, and relevance
        query = query.order_by(
            (Segment.view_count * Segment.relevance_score).desc(),
            Segment.created_at.desc()
        )
        
        results = query.limit(limit).all()
        
        return [
            {
                'id': str(s.Segment.id),
                'title': s.Segment.generated_title,
                'summary': s.Segment.summary_text,
                'key_takeaways': s.Segment.key_takeaways or [],
                'relevance_score': s.Segment.relevance_score,
                'start_time': s.Segment.start_time,
                'end_time': s.Segment.end_time,
                'duration': s.Segment.end_time - s.Segment.start_time,
                'view_count': s.Segment.view_count,
                'video': {
                    'id': str(s.Video.id),
                    'youtube_id': s.Video.youtube_id,
                    'title': s.Video.original_title,
                    'thumbnail_url': s.Video.thumbnail_url,
                },
                'channel': {
                    'id': str(s.Channel.id),
                    'name': s.Channel.name,
                    'thumbnail_url': s.Channel.thumbnail_url,
                },
                'categories': [sc.category.name for sc in s.Segment.categories],
            }
            for s in results
        ]

from typing import List, Optional, Dict, Any
import uuid
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue, Range,
    SearchParams, SearchRequest
)
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating and storing vector embeddings"""
    
    EMBEDDING_DIM = 1536  # text-embedding-3-small dimensions
    
    def __init__(
        self, 
        openai_api_key: Optional[str] = None,
        qdrant_url: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        self.openai = OpenAI(api_key=openai_api_key or settings.openai_api_key)
        self.qdrant = QdrantClient(url=qdrant_url or settings.qdrant_url)
        self.collection_name = collection_name or settings.qdrant_collection
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create Qdrant collection if it doesn't exist"""
        try:
            collections = self.qdrant.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.EMBEDDING_DIM,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Created Qdrant collection", collection=self.collection_name)
                
                # Create payload index for filtering
                self.qdrant.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="relevance_score",
                    field_schema="integer"
                )
                self.qdrant.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="categories",
                    field_schema="keyword"
                )
        except Exception as e:
            logger.warning("Could not ensure collection", error=str(e))
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        response = self.openai.embeddings.create(
            model=settings.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        response = self.openai.embeddings.create(
            model=settings.embedding_model,
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def store_segment_embedding(
        self,
        segment_id: str,
        title: str,
        summary: str,
        transcript: str,
        video_id: str,
        youtube_id: str,
        channel_name: str,
        start_time: int,
        end_time: int,
        relevance_score: int,
        categories: List[str],
        thumbnail_url: Optional[str] = None
    ) -> str:
        """Generate and store embedding for a segment"""
        # Combine text for semantic search
        combined_text = f"{title}\n\n{summary}\n\n{transcript}"
        embedding = self.generate_embedding(combined_text)
        
        # Generate unique point ID
        point_id = str(uuid.uuid4())
        
        # Store in Qdrant
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "segment_id": segment_id,
                    "title": title,
                    "summary": summary,
                    "video_id": video_id,
                    "youtube_id": youtube_id,
                    "channel_name": channel_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time,
                    "relevance_score": relevance_score,
                    "categories": categories,
                    "thumbnail_url": thumbnail_url,
                }
            )]
        )
        
        logger.info("Stored segment embedding", 
                   segment_id=segment_id, 
                   point_id=point_id)
        
        return point_id
    
    def semantic_search(
        self,
        query: str,
        limit: int = 20,
        min_relevance: int = 1,
        categories: Optional[List[str]] = None,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for similar segments using vector similarity"""
        query_embedding = self.generate_embedding(query)
        
        # Build filter
        filter_conditions = []
        
        if min_relevance > 1:
            filter_conditions.append(
                FieldCondition(
                    key="relevance_score",
                    range=Range(gte=min_relevance)
                )
            )
        
        if categories:
            for cat in categories:
                filter_conditions.append(
                    FieldCondition(
                        key="categories",
                        match=MatchValue(value=cat)
                    )
                )
        
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=min_score
        )
        
        return [
            {
                "point_id": str(hit.id),
                "score": hit.score,
                **hit.payload
            }
            for hit in results
        ]
    
    def delete_segment_embedding(self, point_id: str) -> bool:
        """Delete an embedding by point ID"""
        try:
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
            return True
        except Exception as e:
            logger.error("Failed to delete embedding", point_id=point_id, error=str(e))
            return False
    
    def delete_video_embeddings(self, video_id: str) -> int:
        """Delete all embeddings for a video"""
        try:
            result = self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(
                        key="video_id",
                        match=MatchValue(value=video_id)
                    )]
                )
            )
            logger.info("Deleted video embeddings", video_id=video_id)
            return result.status
        except Exception as e:
            logger.error("Failed to delete video embeddings", video_id=video_id, error=str(e))
            return 0
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        info = self.qdrant.get_collection(self.collection_name)
        return {
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.name,
        }

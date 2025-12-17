from typing import List, Optional, Dict, Any
import uuid
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

# Global model cache
_local_model = None


def get_local_embedding_model():
    """Lazy load local embedding model (BGE-M3)"""
    global _local_model
    if _local_model is None:
        logger.info("Loading local embedding model", model=settings.embedding_model)
        try:
            from FlagEmbedding import BGEM3FlagModel
            _local_model = BGEM3FlagModel(
                settings.embedding_model,
                use_fp16=True,
                device=settings.whisper_device  # cpu, cuda, mps
            )
            logger.info("Local embedding model loaded successfully")
        except ImportError:
            logger.warning("FlagEmbedding not installed, trying sentence-transformers")
            from sentence_transformers import SentenceTransformer
            _local_model = SentenceTransformer(settings.embedding_model)
            logger.info("SentenceTransformer model loaded successfully")
    return _local_model


class EmbeddingService:
    """Service for generating and storing vector embeddings"""
    
    def __init__(
        self, 
        openai_api_key: Optional[str] = None,
        qdrant_url: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        self.use_local = settings.use_local_embedding
        self.embedding_dim = settings.embedding_dim
        
        if not self.use_local:
            from openai import OpenAI
            self.openai = OpenAI(api_key=openai_api_key or settings.openai_api_key)
            self.embedding_dim = 1536  # OpenAI text-embedding-3-small
        
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
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Created Qdrant collection", 
                           collection=self.collection_name,
                           dim=self.embedding_dim)
                
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
    
    def recreate_collection(self):
        """Delete and recreate Qdrant collection with current embedding dimensions"""
        try:
            # Delete existing collection
            try:
                self.qdrant.delete_collection(collection_name=self.collection_name)
                logger.info("Deleted existing collection", collection=self.collection_name)
            except Exception:
                pass  # Collection might not exist
            
            # Create new collection with correct dimensions
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            logger.info("Created new Qdrant collection", 
                       collection=self.collection_name,
                       dim=self.embedding_dim)
            
            # Create payload indexes
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
            self.qdrant.create_payload_index(
                collection_name=self.collection_name,
                field_name="segment_id",
                field_schema="keyword"
            )
            
            return True
        except Exception as e:
            logger.error("Failed to recreate collection", error=str(e))
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        if self.use_local:
            return self._generate_local_embedding(text)
        else:
            return self._generate_openai_embedding(text)
    
    def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local BGE-M3 model"""
        model = get_local_embedding_model()
        
        try:
            # BGE-M3 returns dict with 'dense_vecs'
            if hasattr(model, 'encode'):
                # BGEM3FlagModel
                result = model.encode([text], return_dense=True, return_sparse=False, return_colbert_vecs=False)
                if isinstance(result, dict):
                    return result['dense_vecs'][0].tolist()
                else:
                    return result[0].tolist()
            else:
                # Fallback for sentence-transformers
                return model.encode(text).tolist()
        except Exception as e:
            logger.error("Local embedding failed", error=str(e))
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        response = self.openai.embeddings.create(
            model=settings.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.use_local:
            model = get_local_embedding_model()
            try:
                if hasattr(model, 'encode'):
                    result = model.encode(texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)
                    if isinstance(result, dict):
                        return [vec.tolist() for vec in result['dense_vecs']]
                    else:
                        return [vec.tolist() for vec in result]
                else:
                    return [model.encode(t).tolist() for t in texts]
            except Exception as e:
                logger.error("Batch embedding failed", error=str(e))
                raise
        else:
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
                   point_id=point_id,
                   local=self.use_local)
        
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
            "embedding_dim": self.embedding_dim,
            "use_local": self.use_local,
        }

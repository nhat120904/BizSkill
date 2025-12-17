from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "BizSkill AI"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    
    # Security
    secret_key: str = "super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # Database
    database_url: str = "postgresql://bizskill:bizskill_secret@localhost:5432/bizskill"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "segments"
    
    # OpenAI (for LLM only now)
    openai_api_key: str = ""
    llm_model: str = "gpt-4.1"
    
    # Local Models
    use_local_embedding: bool = True  # Use BGE-M3 instead of OpenAI
    use_local_whisper: bool = True    # Use local Whisper instead of OpenAI API
    embedding_model: str = "BAAI/bge-m3"  # or "text-embedding-3-small" for OpenAI
    embedding_dim: int = 1024  # BGE-M3 dimension (OpenAI is 1536)
    whisper_model: str = "base"  # local whisper: tiny, base, small, medium, large
    whisper_device: str = "cpu"  # cpu, cuda, mps (for Apple Silicon)
    
    # Anthropic (optional)
    anthropic_api_key: Optional[str] = None
    llm_provider: str = "openai"  # openai or anthropic
    
    # YouTube
    youtube_api_key: str = ""
    
    # Processing
    temp_audio_dir: str = "/tmp/bizskill"
    max_video_duration_minutes: int = 120
    min_segment_duration_seconds: int = 30
    max_segment_duration_seconds: int = 300
    
    # Polling
    channel_poll_interval_minutes: int = 30
    
    # Cloudinary
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder: str = "bizskill/segments"
    
    # Video processing
    temp_video_dir: str = "/tmp/bizskill/videos"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

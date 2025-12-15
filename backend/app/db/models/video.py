import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum
from app.db.session import Base


def generate_uuid():
    return str(uuid.uuid4())


class VideoStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    SEGMENTING = "segmenting"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"
    REMOVED = "removed"


class Video(Base):
    __tablename__ = "videos"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    youtube_id = Column(String(20), unique=True, nullable=False, index=True)
    channel_id = Column(String(36), ForeignKey("channels.id"), nullable=False)
    original_title = Column(String(500), nullable=True)
    title = Column(String(500), nullable=True)
    description = Column(Text)
    thumbnail_url = Column(String(500))
    duration_seconds = Column(Integer)
    published_at = Column(DateTime)
    view_count = Column(BigInteger, default=0)
    
    # Processing status
    status = Column(String(20), default=VideoStatus.PENDING.value, index=True)
    transcript = Column(Text)
    transcript_segments = Column(JSONB)
    processing_error = Column(Text)
    processed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    channel = relationship("Channel", back_populates="videos")
    segments = relationship("Segment", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Video {self.youtube_id}: {self.original_title[:50] if self.original_title else 'Untitled'}>"

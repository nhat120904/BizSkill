import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, BigInteger, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.session import Base


def generate_uuid():
    return str(uuid.uuid4())


class Segment(Base):
    __tablename__ = "segments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    
    # Timing
    start_time = Column(Float, nullable=False)  # seconds (float for precision)
    end_time = Column(Float, nullable=False)    # seconds (float for precision)
    
    # AI Generated Content
    generated_title = Column(String(300))  # Nullable - set after insights generated
    summary_text = Column(Text)  # Nullable - set after insights generated
    key_takeaways = Column(JSONB)  # ["point1", "point2", "point3"]
    relevance_score = Column(Float)  # 1-10 (float for precision)
    transcript_chunk = Column(Text)
    
    # Vector embedding reference
    embedding_id = Column(String(100))  # Qdrant point ID
    
    # Stats
    view_count = Column(BigInteger, default=0)
    save_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="segments")
    categories = relationship("SegmentCategory", back_populates="segment", cascade="all, delete-orphan")
    
    @property
    def duration_seconds(self) -> int:
        return self.end_time - self.start_time
    
    def __repr__(self):
        return f"<Segment {self.id}: {self.generated_title[:30]}>"

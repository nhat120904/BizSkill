import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base


def generate_uuid():
    return str(uuid.uuid4())


class Channel(Base):
    __tablename__ = "channels"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    youtube_channel_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    thumbnail_url = Column(Text)
    custom_url = Column(String(100))  # @handle
    subscriber_count = Column(String(50))
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Channel {self.name}>"

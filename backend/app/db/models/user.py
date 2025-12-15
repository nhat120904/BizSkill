import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(200))
    avatar_url = Column(String(500))
    
    # Permissions
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interests = relationship("UserInterest", back_populates="user", cascade="all, delete-orphan")
    history = relationship("UserHistory", back_populates="user", cascade="all, delete-orphan")
    saved_segments = relationship("SavedSegment", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"


class UserInterest(Base):
    __tablename__ = "user_interests"
    
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="interests")
    category = relationship("Category", back_populates="user_interests")


class UserHistory(Base):
    __tablename__ = "user_history"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id = Column(String(36), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False)
    
    watched_at = Column(DateTime, default=datetime.utcnow)
    watch_duration_seconds = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="history")
    segment = relationship("Segment")


class SavedSegment(Base):
    __tablename__ = "saved_segments"
    
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    segment_id = Column(String(36), ForeignKey("segments.id", ondelete="CASCADE"), primary_key=True)
    
    saved_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="saved_segments")
    segment = relationship("Segment")

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


def generate_uuid():
    return str(uuid.uuid4())


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    icon = Column(String(50))  # Emoji or icon name
    color = Column(String(7))  # Hex color code
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    segments = relationship("SegmentCategory", back_populates="category")
    user_interests = relationship("UserInterest", back_populates="category")
    
    def __repr__(self):
        return f"<Category {self.name}>"


class SegmentCategory(Base):
    __tablename__ = "segment_categories"
    
    segment_id = Column(String(36), ForeignKey("segments.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    segment = relationship("Segment", back_populates="categories")
    category = relationship("Category", back_populates="segments")

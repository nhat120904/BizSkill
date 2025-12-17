from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


# Channel Schemas
class ChannelBase(BaseModel):
    youtube_channel_id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    custom_url: Optional[str] = None


class ChannelCreate(BaseModel):
    youtube_channel_id: Optional[str] = None
    handle: Optional[str] = None  # @handle


class ChannelResponse(ChannelBase):
    id: str
    subscriber_count: Optional[str] = None
    is_active: bool = True
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    video_count: Optional[int] = None
    segment_count: Optional[int] = None

    class Config:
        from_attributes = True


# Video Schemas
class VideoBase(BaseModel):
    youtube_id: str
    original_title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None


class VideoResponse(VideoBase):
    id: UUID
    status: str
    publish_date: Optional[datetime] = None
    view_count: Optional[str] = None
    segment_count: Optional[int] = None
    created_at: datetime
    channel: Optional[ChannelBase] = None

    class Config:
        from_attributes = True


class VideoProcessRequest(BaseModel):
    youtube_id: str = Field(..., description="YouTube video ID")
    channel_id: Optional[UUID] = None


# Segment Schemas
class SegmentBase(BaseModel):
    generated_title: str
    summary_text: str
    start_time: int
    end_time: int


class SegmentResponse(BaseModel):
    id: UUID
    generated_title: str
    summary_text: str
    key_takeaways: Optional[List[str]] = None
    relevance_score: Optional[int] = None
    start_time: int
    end_time: int
    duration: int
    view_count: int
    video: VideoBase
    channel: ChannelBase
    categories: List[str] = []

    class Config:
        from_attributes = True


class SegmentDetail(SegmentResponse):
    transcript_chunk: Optional[str] = None


# Search Schemas
class SearchQuery(BaseModel):
    q: str = Field(..., min_length=2, max_length=200)
    category: Optional[str] = None
    min_relevance: Optional[int] = Field(default=1, ge=1, le=10)
    page: Optional[int] = Field(default=1, ge=1)
    limit: Optional[int] = Field(default=20, ge=1, le=50)


class SearchResult(BaseModel):
    id: UUID
    title: str
    summary: str
    key_takeaways: List[str]
    relevance_score: int
    start_time: int
    end_time: int
    duration: int
    view_count: int
    video: dict
    channel: dict
    categories: List[str]
    search_score: float


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    limit: int
    results: List[SearchResult]


# Feed Schemas
class FeedRequest(BaseModel):
    type: str = Field(default="trending", pattern="^(trending|latest|personalized)$")
    category: Optional[str] = None
    page: Optional[int] = Field(default=1, ge=1)
    limit: Optional[int] = Field(default=20, ge=1, le=50)


# Category Schemas
class CategoryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    segment_count: Optional[int] = None

    class Config:
        from_attributes = True


# User Schemas
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# History Schemas
class HistoryCreate(BaseModel):
    segment_id: UUID
    watch_duration_seconds: Optional[int] = None
    completed: Optional[bool] = False


class HistoryResponse(BaseModel):
    id: UUID
    segment: SegmentResponse
    watched_at: datetime
    watch_duration_seconds: int
    completed: bool

    class Config:
        from_attributes = True


# Stats Schemas
class StatsResponse(BaseModel):
    total_channels: int
    total_videos: int
    total_segments: int
    indexed_videos: int
    processing_videos: int
    failed_videos: int


# ============ Learning Path Schemas ============

class SkillAssessmentCreate(BaseModel):
    target_skill: str = Field(..., min_length=2, max_length=200)
    current_level: int = Field(..., ge=1, le=5)
    target_level: int = Field(..., ge=1, le=5)
    goals: Optional[str] = None
    time_commitment_hours: float = Field(default=5.0, ge=0.5, le=40)


class LearningPathCreate(BaseModel):
    target_skill: str = Field(..., min_length=2, max_length=200)
    current_level: int = Field(default=1, ge=1, le=5)
    target_level: int = Field(default=4, ge=1, le=5)
    goals: Optional[str] = None
    time_commitment_hours: float = Field(default=5.0, ge=0.5, le=40)


class LessonResponse(BaseModel):
    id: str
    order: int
    title: Optional[str] = None
    description: Optional[str] = None
    learning_objective: Optional[str] = None
    context_notes: Optional[str] = None
    key_concepts: Optional[List[str]] = None
    is_completed: bool
    is_locked: bool
    completed_at: Optional[datetime] = None
    segment: Optional[SegmentResponse] = None

    class Config:
        from_attributes = True


class LearningPathResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    target_skill: str
    current_level: Optional[str] = None
    target_level: Optional[str] = None
    skill_gap_analysis: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    estimated_hours: Optional[float] = None
    status: str
    progress_percentage: float
    completed_lessons: int
    total_lessons: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LearningPathDetailResponse(LearningPathResponse):
    lessons: List[LessonResponse] = []


class LearningPathListResponse(BaseModel):
    paths: List[LearningPathResponse]
    total: int


class LessonCompleteResponse(BaseModel):
    lesson: LessonResponse
    next_suggestion: Optional[dict] = None
    path_completed: bool


class SkillGapAnalysisResponse(BaseModel):
    current_level: str
    target_level: str
    gap_description: str
    key_areas_to_improve: List[str]
    estimated_learning_hours: float
    recommended_approach: str


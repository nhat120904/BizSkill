from app.db.models.channel import Channel
from app.db.models.video import Video
from app.db.models.segment import Segment
from app.db.models.category import Category, SegmentCategory
from app.db.models.user import User, UserInterest, UserHistory, SavedSegment
from app.db.models.learning_path import LearningPath, LearningPathLesson, SkillAssessment

__all__ = [
    "Channel",
    "Video",
    "Segment",
    "Category",
    "SegmentCategory",
    "User",
    "UserInterest",
    "UserHistory",
    "SavedSegment",
    "LearningPath",
    "LearningPathLesson",
    "SkillAssessment",
]

"""
Learning Path API Endpoints
Provides endpoints for AI-powered learning path creation and management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.db.models import User, LearningPath, LearningPathLesson, Segment
from app.core.security import get_current_user
from app.schemas import (
    LearningPathCreate,
    LearningPathResponse,
    LearningPathDetailResponse,
    LearningPathListResponse,
    LessonResponse,
    LessonCompleteResponse,
    SkillAssessmentCreate,
    SkillGapAnalysisResponse,
    SegmentResponse,
    VideoBase,
    ChannelBase,
)
from app.services.learning_path_agent import learning_path_agent

router = APIRouter()


def build_segment_response(segment: Segment) -> Optional[SegmentResponse]:
    """Build a SegmentResponse from a Segment model"""
    if not segment:
        return None
    
    video_data = None
    channel_data = None
    
    if segment.video:
        video_data = VideoBase(
            youtube_id=segment.video.youtube_id,
            original_title=segment.video.original_title,
            description=segment.video.description,
            thumbnail_url=segment.video.thumbnail_url,
            duration_seconds=segment.video.duration_seconds
        )
        
        if segment.video.channel:
            channel_data = ChannelBase(
                youtube_channel_id=segment.video.channel.youtube_channel_id,
                name=segment.video.channel.name,
                description=segment.video.channel.description,
                thumbnail_url=segment.video.channel.thumbnail_url,
                custom_url=segment.video.channel.custom_url
            )
    
    categories = [sc.category.name for sc in segment.categories if sc.category]
    
    return SegmentResponse(
        id=segment.id,
        generated_title=segment.generated_title,
        summary_text=segment.summary_text,
        key_takeaways=segment.key_takeaways,
        relevance_score=int(segment.relevance_score) if segment.relevance_score else None,
        start_time=int(segment.start_time),
        end_time=int(segment.end_time),
        duration=int(segment.end_time - segment.start_time),
        view_count=segment.view_count or 0,
        video=video_data,
        channel=channel_data,
        categories=categories
    )


def build_lesson_response(lesson: LearningPathLesson) -> LessonResponse:
    """Build a LessonResponse from a LearningPathLesson model"""
    return LessonResponse(
        id=lesson.id,
        order=lesson.order,
        title=lesson.title,
        description=lesson.description,
        learning_objective=lesson.learning_objective,
        context_notes=lesson.context_notes,
        key_concepts=lesson.key_concepts,
        is_completed=lesson.is_completed,
        is_locked=lesson.is_locked,
        completed_at=lesson.completed_at,
        segment=build_segment_response(lesson.segment)
    )


def build_path_response(path: LearningPath) -> LearningPathResponse:
    """Build a LearningPathResponse from a LearningPath model"""
    return LearningPathResponse(
        id=path.id,
        title=path.title,
        description=path.description,
        target_skill=path.target_skill,
        current_level=path.current_level,
        target_level=path.target_level,
        skill_gap_analysis=path.skill_gap_analysis,
        learning_objectives=path.learning_objectives,
        estimated_hours=path.estimated_hours,
        status=path.status,
        progress_percentage=path.progress_percentage or 0,
        completed_lessons=path.completed_lessons or 0,
        total_lessons=path.total_lessons or 0,
        started_at=path.started_at,
        completed_at=path.completed_at,
        last_activity_at=path.last_activity_at,
        created_at=path.created_at
    )


# ============ Learning Path Endpoints ============

@router.post("/", response_model=LearningPathDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_learning_path(
    request: LearningPathCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new AI-generated learning path based on skill gap analysis.
    
    The AI agent will:
    1. Analyze your current skill level
    2. Identify key areas to improve
    3. Select and sequence the most relevant video segments
    4. Create a personalized learning path
    """
    try:
        learning_path = learning_path_agent.create_learning_path(
            db=db,
            user_id=current_user.id,
            target_skill=request.target_skill,
            current_level=request.current_level,
            target_level=request.target_level,
            goals=request.goals,
            time_commitment_hours=request.time_commitment_hours
        )
        
        # Build response with lessons
        lessons = [build_lesson_response(l) for l in learning_path.lessons]
        
        return LearningPathDetailResponse(
            **build_path_response(learning_path).model_dump(),
            lessons=lessons
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create learning path: {str(e)}"
        )


@router.get("/", response_model=LearningPathListResponse)
async def list_learning_paths(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all learning paths for the current user.
    Optionally filter by status: draft, active, completed, paused
    """
    query = db.query(LearningPath).filter(
        LearningPath.user_id == current_user.id
    )
    
    if status_filter:
        query = query.filter(LearningPath.status == status_filter)
    
    paths = query.order_by(desc(LearningPath.created_at)).all()
    
    return LearningPathListResponse(
        paths=[build_path_response(p) for p in paths],
        total=len(paths)
    )


@router.get("/suggested-skills", response_model=List[dict])
async def get_suggested_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get suggested skills to learn based on user's interests and history.
    """
    from app.db.models import Category, UserInterest
    
    # Get user's interests
    user_interests = db.query(UserInterest).filter(
        UserInterest.user_id == current_user.id
    ).all()
    
    interest_category_ids = [ui.category_id for ui in user_interests]
    
    # Get categories user is interested in
    if interest_category_ids:
        categories = db.query(Category).filter(
            Category.id.in_(interest_category_ids)
        ).all()
    else:
        # Default to popular categories
        categories = db.query(Category).limit(10).all()
    
    # Get user's existing paths to exclude
    existing_skills = db.query(LearningPath.target_skill).filter(
        LearningPath.user_id == current_user.id,
        LearningPath.status.in_(["active", "completed"])
    ).all()
    existing_skill_names = [s[0].lower() for s in existing_skills]
    
    suggested = []
    for cat in categories:
        if cat.name.lower() not in existing_skill_names:
            # Count available segments
            segment_count = len(cat.segments) if cat.segments else 0
            
            suggested.append({
                "skill": cat.name,
                "category_id": cat.id,
                "description": cat.description,
                "icon": cat.icon,
                "color": cat.color,
                "available_lessons": segment_count,
                "is_interest": cat.id in interest_category_ids
            })
    
    # Sort by interest first, then by available content
    suggested.sort(key=lambda x: (-x['is_interest'], -x['available_lessons']))
    
    return suggested[:10]


@router.get("/{path_id}", response_model=LearningPathDetailResponse)
async def get_learning_path(
    path_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific learning path including all lessons.
    """
    learning_path = db.query(LearningPath).filter(
        LearningPath.id == path_id,
        LearningPath.user_id == current_user.id
    ).first()
    
    if not learning_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found"
        )
    
    lessons = [build_lesson_response(l) for l in learning_path.lessons]
    
    return LearningPathDetailResponse(
        **build_path_response(learning_path).model_dump(),
        lessons=lessons
    )


@router.delete("/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_path(
    path_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a learning path.
    """
    learning_path = db.query(LearningPath).filter(
        LearningPath.id == path_id,
        LearningPath.user_id == current_user.id
    ).first()
    
    if not learning_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found"
        )
    
    db.delete(learning_path)
    db.commit()
    
    return None


@router.patch("/{path_id}/status")
async def update_path_status(
    path_id: str,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the status of a learning path (pause, resume, etc.)
    Valid statuses: active, paused
    """
    if new_status not in ["active", "paused"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Use 'active' or 'paused'"
        )
    
    learning_path = db.query(LearningPath).filter(
        LearningPath.id == path_id,
        LearningPath.user_id == current_user.id
    ).first()
    
    if not learning_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found"
        )
    
    if learning_path.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change status of a completed path"
        )
    
    learning_path.status = new_status
    db.commit()
    
    return {"status": "updated", "new_status": new_status}


# ============ Lesson Endpoints ============

@router.get("/{path_id}/lessons/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    path_id: str,
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific lesson.
    """
    lesson = db.query(LearningPathLesson).join(LearningPath).filter(
        LearningPathLesson.id == lesson_id,
        LearningPath.id == path_id,
        LearningPath.user_id == current_user.id
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    return build_lesson_response(lesson)


@router.post("/{path_id}/lessons/{lesson_id}/complete", response_model=LessonCompleteResponse)
async def complete_lesson(
    path_id: str,
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a lesson as complete and get AI suggestion for next lesson.
    
    Returns:
    - Updated lesson information
    - AI suggestion for what to learn next
    - Whether the entire path is now complete
    """
    # Verify path belongs to user
    learning_path = db.query(LearningPath).filter(
        LearningPath.id == path_id,
        LearningPath.user_id == current_user.id
    ).first()
    
    if not learning_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found"
        )
    
    try:
        lesson, suggestion = learning_path_agent.complete_lesson(
            db=db,
            user_id=current_user.id,
            lesson_id=lesson_id
        )
        
        # Refresh path to get updated status
        db.refresh(learning_path)
        
        return LessonCompleteResponse(
            lesson=build_lesson_response(lesson),
            next_suggestion=suggestion.model_dump() if suggestion else None,
            path_completed=(learning_path.status == "completed")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete lesson: {str(e)}"
        )


# ============ Skill Assessment Endpoints ============

@router.post("/analyze-skill-gap", response_model=SkillGapAnalysisResponse)
async def analyze_skill_gap(
    request: SkillAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get AI analysis of your skill gap without creating a learning path.
    Useful for previewing what a learning path might look like.
    """
    try:
        analysis = learning_path_agent.analyze_skill_gap(
            db=db,
            user_id=current_user.id,
            target_skill=request.target_skill,
            current_level=request.current_level,
            target_level=request.target_level,
            goals=request.goals,
            time_commitment_hours=request.time_commitment_hours
        )
        
        return SkillGapAnalysisResponse(
            current_level=analysis.current_level,
            target_level=analysis.target_level,
            gap_description=analysis.gap_description,
            key_areas_to_improve=analysis.key_areas_to_improve,
            estimated_learning_hours=analysis.estimated_learning_hours,
            recommended_approach=analysis.recommended_approach
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze skill gap: {str(e)}"
        )

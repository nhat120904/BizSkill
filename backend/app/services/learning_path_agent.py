"""
Learning Path Agent Service
AI-powered agent that creates personalized learning paths based on user's skill gap.
Uses Claude Haiku 4.5 for intelligent path generation with structured outputs.
"""

import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pydantic import BaseModel
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from anthropic import Anthropic
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.config import settings
from app.db.models import (
    User, Segment, Category, SegmentCategory, 
    UserHistory, LearningPath, LearningPathLesson, SkillAssessment
)

logger = structlog.get_logger()


# ============ Pydantic Models for Agent Responses ============

class SkillGapAnalysis(BaseModel):
    current_level: str
    target_level: str
    gap_description: str
    key_areas_to_improve: List[str]
    estimated_learning_hours: float
    recommended_approach: str


class LessonPlan(BaseModel):
    order: int
    segment_id: str
    title: str
    description: str
    learning_objective: str
    context_notes: str
    key_concepts: List[str]
    estimated_minutes: int


class GeneratedLearningPath(BaseModel):
    title: str
    description: str
    skill_gap_analysis: SkillGapAnalysis
    learning_objectives: List[str]
    lessons: List[LessonPlan]
    total_estimated_hours: float


class NextLessonSuggestion(BaseModel):
    segment_id: str
    reason: str
    relevance_score: float
    connects_to_previous: str


# ============ Tool Definitions for Structured Output ============

SKILL_GAP_TOOL = {
    "name": "analyze_skill_gap",
    "description": "Analyze user's skill gap and provide structured recommendations",
    "input_schema": {
        "type": "object",
        "properties": {
            "current_level": {
                "type": "string",
                "description": "Current skill level description (e.g., 'Beginner with limited exposure')"
            },
            "target_level": {
                "type": "string", 
                "description": "Target skill level description (e.g., 'Advanced practitioner')"
            },
            "gap_description": {
                "type": "string",
                "description": "Detailed analysis of the skill gap between current and target levels"
            },
            "key_areas_to_improve": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of key areas the user needs to improve"
            },
            "estimated_learning_hours": {
                "type": "number",
                "description": "Estimated total hours needed to close the skill gap"
            },
            "recommended_approach": {
                "type": "string",
                "description": "Recommended learning strategy and approach"
            }
        },
        "required": ["current_level", "target_level", "gap_description", "key_areas_to_improve", "estimated_learning_hours", "recommended_approach"]
    }
}

LEARNING_PATH_TOOL = {
    "name": "create_learning_path",
    "description": "Create a structured learning path with lessons from available segments",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Catchy title for the learning path"
            },
            "description": {
                "type": "string",
                "description": "Motivating description of what the user will achieve"
            },
            "learning_objectives": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of learning objectives"
            },
            "lessons": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "order": {"type": "integer", "description": "Lesson order (1, 2, 3...)"},
                        "segment_id": {"type": "string", "description": "EXACT segment ID from available segments"},
                        "title": {"type": "string", "description": "Lesson title"},
                        "description": {"type": "string", "description": "Why this lesson matters"},
                        "learning_objective": {"type": "string", "description": "What user will learn"},
                        "context_notes": {"type": "string", "description": "How this connects to the path"},
                        "key_concepts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Key concepts covered"
                        },
                        "estimated_minutes": {"type": "integer", "description": "Duration in minutes"}
                    },
                    "required": ["order", "segment_id", "title", "description", "learning_objective", "context_notes", "key_concepts", "estimated_minutes"]
                },
                "description": "List of lessons in order"
            },
            "total_estimated_hours": {
                "type": "number",
                "description": "Total estimated learning time in hours"
            }
        },
        "required": ["title", "description", "learning_objectives", "lessons", "total_estimated_hours"]
    }
}

NEXT_LESSON_TOOL = {
    "name": "suggest_next_lesson",
    "description": "Suggest the next lesson for the user",
    "input_schema": {
        "type": "object",
        "properties": {
            "segment_id": {
                "type": "string",
                "description": "ID of the suggested segment"
            },
            "reason": {
                "type": "string",
                "description": "Why this is the right next lesson"
            },
            "relevance_score": {
                "type": "number",
                "description": "Relevance score from 0-10"
            },
            "connects_to_previous": {
                "type": "string",
                "description": "How this connects to the completed lesson"
            }
        },
        "required": ["segment_id", "reason", "relevance_score", "connects_to_previous"]
    }
}


# ============ System Prompts ============

SKILL_GAP_ANALYSIS_PROMPT = """You are an expert learning consultant and career coach specializing in professional development.
Your task is to analyze a user's current skill level and create a personalized skill gap analysis.

RULES:
1. Be realistic about skill gaps - don't oversell or undersell
2. Consider the user's available time commitment
3. Prioritize actionable, practical skills
4. Suggest a structured approach from fundamentals to advanced topics
5. Account for content they've already watched
6. Keep current_level and target_level descriptions concise (under 100 characters)

Use the analyze_skill_gap tool to provide your analysis."""


PATH_GENERATION_PROMPT = """You are an expert curriculum designer creating personalized learning paths.
Your task is to select and sequence the most relevant video segments to help the user achieve their learning goals.

RULES:
1. Select 5-10 segments maximum
2. Sequence from foundational to advanced concepts
3. Each lesson should build on previous ones
4. ONLY use segment_id values from the provided available segments list
5. Write clear, motivating descriptions for each lesson
6. Keep descriptions concise

Use the create_learning_path tool to provide your path."""


NEXT_LESSON_PROMPT = """You are a smart learning assistant recommending the next lesson for a user.
Based on what they've just completed and their learning path, suggest the most relevant next segment.

Use the suggest_next_lesson tool to provide your suggestion."""


class LearningPathAgentService:
    """
    AI Agent for creating and managing personalized learning paths.
    Uses Claude Haiku 4.5 with structured outputs (tool use) for reliable JSON responses.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = Anthropic(api_key=api_key or settings.anthropic_api_key)
        self.model = "claude-haiku-4-5-20251001"  # Using Claude Haiku 4.5
    
    # ============ Helper Methods ============
    
    def _safe_rollback(self, db: Session):
        """Safely rollback any failed transaction"""
        try:
            db.rollback()
        except Exception:
            pass
    
    def _get_user_watch_history(self, db: Session, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user's recent watch history with segment details"""
        try:
            history = db.query(UserHistory).filter(
                UserHistory.user_id == user_id
            ).order_by(desc(UserHistory.watched_at)).limit(limit).all()
            
            watched_segments = []
            for h in history:
                if h.segment:
                    watched_segments.append({
                        "segment_id": h.segment_id,
                        "title": h.segment.generated_title,
                        "summary": h.segment.summary_text,
                        "completed": h.completed,
                        "watched_at": h.watched_at.isoformat() if h.watched_at else None
                    })
            
            return watched_segments
        except Exception as e:
            logger.warning("Failed to get watch history", error=str(e))
            self._safe_rollback(db)
            return []
    
    def _get_available_segments(
        self, 
        db: Session, 
        category_slug: Optional[str] = None,
        exclude_ids: Optional[List[str]] = None,
        min_relevance: int = 5,
        limit: int = 100
    ) -> List[Dict]:
        """Get available segments for a category with their details"""
        try:
            query = db.query(Segment).filter(
                Segment.relevance_score >= min_relevance,
                Segment.generated_title.isnot(None)
            )
            
            if category_slug:
                query = query.join(SegmentCategory).join(Category).filter(
                    Category.slug == category_slug
                )
            
            if exclude_ids:
                query = query.filter(~Segment.id.in_(exclude_ids))
            
            segments = query.order_by(desc(Segment.relevance_score)).limit(limit).all()
            
            result = []
            for s in segments:
                categories = [sc.category.name for sc in s.categories if sc.category]
                result.append({
                    "id": str(s.id),
                    "title": s.generated_title,
                    "summary": s.summary_text,
                    "key_takeaways": s.key_takeaways or [],
                    "relevance_score": s.relevance_score,
                    "duration_minutes": round((s.end_time - s.start_time) / 60, 1),
                    "categories": categories,
                    "view_count": s.view_count or 0
                })
            
            return result
        except Exception as e:
            logger.warning("Failed to get available segments", error=str(e))
            self._safe_rollback(db)
            return []
    
    def _get_category_by_skill(self, db: Session, skill_name: str) -> Optional[Category]:
        """Find the category that best matches a skill name"""
        try:
            # Try exact match first
            category = db.query(Category).filter(
                func.lower(Category.name) == func.lower(skill_name)
            ).first()
            
            if not category:
                # Try partial match
                category = db.query(Category).filter(
                    func.lower(Category.name).contains(func.lower(skill_name))
                ).first()
            
            return category
        except Exception as e:
            logger.warning("Failed to get category by skill", error=str(e))
            self._safe_rollback(db)
            return None
    
    # ============ Agent Methods ============
    
    def analyze_skill_gap(
        self,
        db: Session,
        user_id: str,
        target_skill: str,
        current_level: int,  # 1-5
        target_level: int,   # 1-5
        goals: Optional[str] = None,
        time_commitment_hours: float = 5.0  # hours per week
    ) -> SkillGapAnalysis:
        """
        Analyze user's skill gap and generate recommendations using Claude structured output.
        """
        logger.info("Analyzing skill gap", 
                   user_id=user_id, 
                   skill=target_skill,
                   current=current_level,
                   target=target_level)
        
        # Rollback any failed transaction first
        self._safe_rollback(db)
        
        # Get user's watch history
        watch_history = self._get_user_watch_history(db, user_id)
        
        # Get available content for this skill
        category = self._get_category_by_skill(db, target_skill)
        available_content = self._get_available_segments(
            db, 
            category_slug=category.slug if category else None,
            limit=50
        )
        
        level_map = {1: "Beginner", 2: "Elementary", 3: "Intermediate", 4: "Advanced", 5: "Expert"}
        
        prompt = f"""Analyze the skill gap for learning "{target_skill}".

USER PROFILE:
- Current Level: {level_map.get(current_level, 'Unknown')} ({current_level}/5)
- Target Level: {level_map.get(target_level, 'Unknown')} ({target_level}/5)
- Goals: {goals or 'Not specified'}
- Weekly Time Available: {time_commitment_hours} hours

WATCH HISTORY:
{json.dumps([h['title'] for h in watch_history[:10]], indent=2) if watch_history else "No previous watch history"}

AVAILABLE CONTENT:
{json.dumps([c['title'] for c in available_content[:20]], indent=2) if available_content else "Various business topics"}

Use the analyze_skill_gap tool to provide your analysis."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system=SKILL_GAP_ANALYSIS_PROMPT,
                tools=[SKILL_GAP_TOOL],
                tool_choice={"type": "tool", "name": "analyze_skill_gap"}
            )
            
            # Extract tool use result
            for block in response.content:
                if block.type == "tool_use" and block.name == "analyze_skill_gap":
                    return SkillGapAnalysis(**block.input)
            
            raise ValueError("No tool use response from AI")
            
        except Exception as e:
            logger.error("Error analyzing skill gap", error=str(e))
            raise
    
    def generate_learning_path(
        self,
        db: Session,
        user_id: str,
        target_skill: str,
        skill_gap: SkillGapAnalysis,
        max_lessons: int = 10
    ) -> GeneratedLearningPath:
        """
        Generate a complete learning path based on skill gap analysis using Claude structured output.
        """
        logger.info("Generating learning path", 
                   user_id=user_id, 
                   skill=target_skill,
                   max_lessons=max_lessons)
        
        # Get user's watched segment IDs
        watch_history = self._get_user_watch_history(db, user_id)
        watched_ids = [h['segment_id'] for h in watch_history]
        
        # Get available content
        category = self._get_category_by_skill(db, target_skill)
        available_segments = self._get_available_segments(
            db,
            category_slug=category.slug if category else None,
            exclude_ids=watched_ids,
            min_relevance=5,
            limit=30
        )
        
        if not available_segments:
            # Fallback to all segments if category doesn't have enough
            available_segments = self._get_available_segments(
                db,
                exclude_ids=watched_ids,
                min_relevance=5,
                limit=30
            )
        
        # Check if we have any segments to work with
        if not available_segments:
            logger.warning("No segments available for learning path", skill=target_skill)
            # Return a default path structure
            return GeneratedLearningPath(
                title=f"Learning Path: {target_skill.title()}",
                description=f"A personalized learning path to help you master {target_skill}. Content will be added as it becomes available.",
                skill_gap_analysis=skill_gap,
                learning_objectives=skill_gap.key_areas_to_improve[:3] if skill_gap.key_areas_to_improve else ["Master the fundamentals"],
                lessons=[],
                total_estimated_hours=skill_gap.estimated_learning_hours
            )
        
        # Simplify segment data for the prompt to avoid token limits
        simplified_segments = []
        for s in available_segments[:15]:
            simplified_segments.append({
                "id": s["id"],
                "title": s["title"][:100] if s["title"] else "Untitled",
                "duration_minutes": s["duration_minutes"]
            })
        
        prompt = f"""Create a learning path for "{target_skill}".

SKILL GAP:
- Current: {skill_gap.current_level}
- Target: {skill_gap.target_level}
- Key areas: {', '.join(skill_gap.key_areas_to_improve[:5])}

AVAILABLE SEGMENTS (use EXACT id values):
{json.dumps(simplified_segments, indent=2)}

Create a path with {min(max_lessons, len(simplified_segments), 8)} lessons using the create_learning_path tool."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system=PATH_GENERATION_PROMPT,
                tools=[LEARNING_PATH_TOOL],
                tool_choice={"type": "tool", "name": "create_learning_path"}
            )
            
            # Extract tool use result
            for block in response.content:
                if block.type == "tool_use" and block.name == "create_learning_path":
                    path_data = block.input
                    # Add skill_gap_analysis back
                    path_data["skill_gap_analysis"] = skill_gap.model_dump()
                    return GeneratedLearningPath(**path_data)
            
            raise ValueError("No tool use response from AI")
            
        except Exception as e:
            logger.error("Error generating learning path", error=str(e))
            raise
    
    def suggest_next_lesson(
        self,
        db: Session,
        user_id: str,
        learning_path_id: str,
        completed_lesson_id: str
    ) -> NextLessonSuggestion:
        """
        Suggest the next lesson after a user completes one using Claude structured output.
        """
        logger.info("Suggesting next lesson",
                   user_id=user_id,
                   path_id=learning_path_id,
                   completed_lesson=completed_lesson_id)
        
        # Get current path and lessons
        learning_path = db.query(LearningPath).filter(
            LearningPath.id == learning_path_id
        ).first()
        
        if not learning_path:
            raise ValueError("Learning path not found")
        
        completed_lesson = db.query(LearningPathLesson).filter(
            LearningPathLesson.id == completed_lesson_id
        ).first()
        
        # Get remaining lessons in path
        remaining_lessons = db.query(LearningPathLesson).filter(
            LearningPathLesson.learning_path_id == learning_path_id,
            LearningPathLesson.is_completed == False,
            LearningPathLesson.order > (completed_lesson.order if completed_lesson else 0)
        ).order_by(LearningPathLesson.order).limit(5).all()
        
        # If there are remaining lessons, suggest the next one
        if remaining_lessons:
            next_lesson = remaining_lessons[0]
            return NextLessonSuggestion(
                segment_id=next_lesson.segment_id or "",
                reason=f"Continue with the next lesson in your learning path: {next_lesson.title}",
                relevance_score=0.95,
                connects_to_previous=f"This lesson builds directly on {completed_lesson.title if completed_lesson else 'the previous lesson'}"
            )
        
        # Otherwise, get additional relevant segments
        watched_ids = [h.segment_id for h in db.query(UserHistory).filter(
            UserHistory.user_id == user_id
        ).all()]
        path_segment_ids = [l.segment_id for l in learning_path.lessons if l.segment_id]
        exclude_ids = list(set(watched_ids + path_segment_ids))
        
        additional_segments = self._get_available_segments(
            db,
            exclude_ids=exclude_ids,
            min_relevance=7,
            limit=10
        )
        
        if not additional_segments:
            return NextLessonSuggestion(
                segment_id="",
                reason="Congratulations! You've completed all available content for this skill.",
                relevance_score=0.0,
                connects_to_previous="You've mastered this learning path!"
            )
        
        completed_segment = completed_lesson.segment if completed_lesson else None
        
        prompt = f"""A user completed a lesson. Suggest the next one.

PATH: {learning_path.title}
COMPLETED: {completed_lesson.title if completed_lesson else 'Unknown'}
KEY CONCEPTS: {completed_lesson.key_concepts if completed_lesson else []}

AVAILABLE SEGMENTS:
{json.dumps([{'id': s['id'], 'title': s['title']} for s in additional_segments[:5]], indent=2)}

Use the suggest_next_lesson tool to recommend the best next segment."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system=NEXT_LESSON_PROMPT,
                tools=[NEXT_LESSON_TOOL],
                tool_choice={"type": "tool", "name": "suggest_next_lesson"}
            )
            
            for block in response.content:
                if block.type == "tool_use" and block.name == "suggest_next_lesson":
                    return NextLessonSuggestion(**block.input)
            
            # Fallback to first available
            return NextLessonSuggestion(
                segment_id=additional_segments[0]["id"],
                reason="Recommended based on your learning history",
                relevance_score=0.8,
                connects_to_previous="Continues your learning journey"
            )
            
        except Exception as e:
            logger.error("Error suggesting next lesson", error=str(e))
            # Fallback
            if additional_segments:
                return NextLessonSuggestion(
                    segment_id=additional_segments[0]["id"],
                    reason="Recommended based on your learning history",
                    relevance_score=0.8,
                    connects_to_previous="Continues your learning journey"
                )
            raise
    
    # ============ Path Management Methods ============
    
    def create_learning_path(
        self,
        db: Session,
        user_id: str,
        target_skill: str,
        current_level: int = 1,
        target_level: int = 4,
        goals: Optional[str] = None,
        time_commitment_hours: float = 5.0
    ) -> LearningPath:
        """
        Full workflow: Analyze skill gap and create a complete learning path.
        """
        logger.info("Creating complete learning path", user_id=user_id, skill=target_skill)
        
        # Rollback any previous failed transaction
        self._safe_rollback(db)
        
        try:
            # Step 1: Analyze skill gap
            skill_gap = self.analyze_skill_gap(
                db=db,
                user_id=user_id,
                target_skill=target_skill,
                current_level=current_level,
                target_level=target_level,
                goals=goals,
                time_commitment_hours=time_commitment_hours
            )
            
            # Step 2: Generate learning path
            generated_path = self.generate_learning_path(
                db=db,
                user_id=user_id,
                target_skill=target_skill,
                skill_gap=skill_gap
            )
            
            # Step 3: Create database records
            learning_path = LearningPath(
                user_id=user_id,
                title=generated_path.title,
                description=generated_path.description,
                target_skill=target_skill,
                current_level=skill_gap.current_level,
                target_level=skill_gap.target_level,
                skill_gap_analysis=skill_gap.gap_description,
                learning_objectives=generated_path.learning_objectives,
                estimated_hours=generated_path.total_estimated_hours,
                total_lessons=len(generated_path.lessons),
                status="active",
                started_at=datetime.utcnow()
            )
            db.add(learning_path)
            db.flush()  # Get the ID
            
            # Step 4: Create lessons
            for lesson_plan in generated_path.lessons:
                # Verify segment exists
                segment = db.query(Segment).filter(Segment.id == lesson_plan.segment_id).first()
                
                if not segment:
                    logger.warning("Segment not found, skipping lesson", segment_id=lesson_plan.segment_id)
                    continue
                
                lesson = LearningPathLesson(
                    learning_path_id=learning_path.id,
                    segment_id=lesson_plan.segment_id,
                    order=lesson_plan.order,
                    title=lesson_plan.title,
                    description=lesson_plan.description,
                    learning_objective=lesson_plan.learning_objective,
                    context_notes=lesson_plan.context_notes,
                    key_concepts=lesson_plan.key_concepts,
                    is_locked=(lesson_plan.order > 1)  # First lesson unlocked
                )
                db.add(lesson)
            
            # Update total lessons count
            learning_path.total_lessons = len([l for l in generated_path.lessons])
            
            # Step 5: Create skill assessment record
            assessment = SkillAssessment(
                user_id=user_id,
                skill_name=target_skill,
                current_level=current_level,
                target_level=target_level,
                goals=goals,
                time_commitment_hours=time_commitment_hours,
                ai_recommendations=skill_gap.key_areas_to_improve
            )
            db.add(assessment)
            
            db.commit()
            db.refresh(learning_path)
            
            logger.info("Learning path created successfully", 
                       path_id=learning_path.id, 
                       lessons_count=learning_path.total_lessons)
            
            return learning_path
            
        except Exception as e:
            logger.error("Failed to create learning path", error=str(e))
            self._safe_rollback(db)
            raise
    
    def complete_lesson(
        self,
        db: Session,
        user_id: str,
        lesson_id: str
    ) -> Tuple[LearningPathLesson, Optional[NextLessonSuggestion]]:
        """
        Mark a lesson as complete and get next suggestion.
        """
        lesson = db.query(LearningPathLesson).filter(
            LearningPathLesson.id == lesson_id
        ).first()
        
        if not lesson:
            raise ValueError("Lesson not found")
        
        learning_path = lesson.learning_path
        if learning_path.user_id != user_id:
            raise ValueError("Unauthorized")
        
        # Mark lesson as complete
        lesson.is_completed = True
        lesson.completed_at = datetime.utcnow()
        
        # Update path progress
        completed_count = db.query(LearningPathLesson).filter(
            LearningPathLesson.learning_path_id == learning_path.id,
            LearningPathLesson.is_completed == True
        ).count() + 1  # Include this one
        
        learning_path.completed_lessons = completed_count
        learning_path.progress_percentage = (completed_count / learning_path.total_lessons) * 100
        learning_path.last_activity_at = datetime.utcnow()
        
        # Unlock next lesson
        next_lesson = db.query(LearningPathLesson).filter(
            LearningPathLesson.learning_path_id == learning_path.id,
            LearningPathLesson.order == lesson.order + 1
        ).first()
        
        if next_lesson:
            next_lesson.is_locked = False
        
        # Check if path is complete
        if completed_count >= learning_path.total_lessons:
            learning_path.status = "completed"
            learning_path.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(lesson)
        
        # Get next suggestion (unless path is complete)
        suggestion = None
        if learning_path.status != "completed":
            try:
                suggestion = self.suggest_next_lesson(
                    db=db,
                    user_id=user_id,
                    learning_path_id=learning_path.id,
                    completed_lesson_id=lesson_id
                )
            except Exception as e:
                logger.error("Failed to get next suggestion", error=str(e))
        
        return lesson, suggestion


# Singleton instance
learning_path_agent = LearningPathAgentService()

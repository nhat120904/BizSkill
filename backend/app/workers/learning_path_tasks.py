"""
Learning Path Celery Tasks
Async tasks for AI-powered learning path generation and management.
"""

from datetime import datetime
import structlog
from celery import chain
from app.core.celery_app import celery_app
from app.db.session import get_db_session
from app.db.models import User, LearningPath, LearningPathLesson, UserHistory
from app.services.learning_path_agent import learning_path_agent

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3)
def create_learning_path_async(
    self,
    user_id: str,
    target_skill: str,
    current_level: int = 1,
    target_level: int = 4,
    goals: str = None,
    time_commitment_hours: float = 5.0
):
    """
    Async task to create a learning path.
    Use this for heavy path generation that might take time.
    """
    logger.info("Starting async learning path creation",
                user_id=user_id,
                skill=target_skill)
    
    db = get_db_session()
    try:
        learning_path = learning_path_agent.create_learning_path(
            db=db,
            user_id=user_id,
            target_skill=target_skill,
            current_level=current_level,
            target_level=target_level,
            goals=goals,
            time_commitment_hours=time_commitment_hours
        )
        
        logger.info("Learning path created successfully",
                   path_id=learning_path.id,
                   lessons=learning_path.total_lessons)
        
        return {
            "status": "success",
            "path_id": learning_path.id,
            "title": learning_path.title,
            "total_lessons": learning_path.total_lessons
        }
        
    except Exception as e:
        logger.error("Failed to create learning path", error=str(e))
        self.retry(exc=e, countdown=60)
        
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def update_path_progress(self, user_id: str, segment_id: str):
    """
    When a user watches a segment, check if it's part of any learning path
    and update progress automatically.
    """
    logger.info("Updating path progress",
                user_id=user_id,
                segment_id=segment_id)
    
    db = get_db_session()
    try:
        # Find any lessons containing this segment
        lessons = db.query(LearningPathLesson).join(LearningPath).filter(
            LearningPathLesson.segment_id == segment_id,
            LearningPath.user_id == user_id,
            LearningPath.status == "active",
            LearningPathLesson.is_completed == False
        ).all()
        
        for lesson in lessons:
            # Check if user completed watching (from history)
            history = db.query(UserHistory).filter(
                UserHistory.user_id == user_id,
                UserHistory.segment_id == segment_id,
                UserHistory.completed == True
            ).first()
            
            if history:
                # Mark lesson as complete
                lesson.is_completed = True
                lesson.completed_at = datetime.utcnow()
                
                # Update path progress
                path = lesson.learning_path
                completed_count = db.query(LearningPathLesson).filter(
                    LearningPathLesson.learning_path_id == path.id,
                    LearningPathLesson.is_completed == True
                ).count()
                
                path.completed_lessons = completed_count
                path.progress_percentage = (completed_count / path.total_lessons) * 100
                path.last_activity_at = datetime.utcnow()
                
                # Unlock next lesson
                next_lesson = db.query(LearningPathLesson).filter(
                    LearningPathLesson.learning_path_id == path.id,
                    LearningPathLesson.order == lesson.order + 1
                ).first()
                
                if next_lesson:
                    next_lesson.is_locked = False
                
                # Check if path is complete
                if completed_count >= path.total_lessons:
                    path.status = "completed"
                    path.completed_at = datetime.utcnow()
                
                logger.info("Lesson marked complete via auto-tracking",
                           lesson_id=lesson.id,
                           path_progress=path.progress_percentage)
        
        db.commit()
        
    except Exception as e:
        logger.error("Failed to update path progress", error=str(e))
        db.rollback()
        
    finally:
        db.close()


@celery_app.task(bind=True)
def generate_next_suggestions(self, user_id: str, path_id: str, completed_lesson_id: str):
    """
    Generate and cache next lesson suggestions after completion.
    """
    logger.info("Generating next suggestions",
                user_id=user_id,
                path_id=path_id)
    
    db = get_db_session()
    try:
        suggestion = learning_path_agent.suggest_next_lesson(
            db=db,
            user_id=user_id,
            learning_path_id=path_id,
            completed_lesson_id=completed_lesson_id
        )
        
        # Could cache this suggestion in Redis for quick retrieval
        logger.info("Next suggestion generated",
                   suggested_segment=suggestion.segment_id)
        
        return suggestion.model_dump()
        
    except Exception as e:
        logger.error("Failed to generate suggestions", error=str(e))
        
    finally:
        db.close()


@celery_app.task(bind=True)
def check_stale_paths(self):
    """
    Scheduled task: Check for paths that haven't been accessed in a while
    and send reminders or suggestions.
    """
    from datetime import timedelta
    
    logger.info("Checking for stale learning paths")
    
    db = get_db_session()
    try:
        # Find active paths not accessed in 7 days
        stale_threshold = datetime.utcnow() - timedelta(days=7)
        
        stale_paths = db.query(LearningPath).filter(
            LearningPath.status == "active",
            LearningPath.last_activity_at < stale_threshold
        ).all()
        
        for path in stale_paths:
            # Could trigger notification here
            logger.info("Stale path found",
                       path_id=path.id,
                       user_id=path.user_id,
                       last_activity=path.last_activity_at)
            
            # Optionally pause very stale paths
            if path.last_activity_at < datetime.utcnow() - timedelta(days=30):
                path.status = "paused"
        
        db.commit()
        
        logger.info("Stale path check complete", stale_count=len(stale_paths))
        
    except Exception as e:
        logger.error("Failed to check stale paths", error=str(e))
        db.rollback()
        
    finally:
        db.close()


@celery_app.task(bind=True)
def recalculate_all_progress(self):
    """
    Maintenance task: Recalculate progress for all active paths.
    Useful if there are data inconsistencies.
    """
    logger.info("Recalculating all path progress")
    
    db = get_db_session()
    try:
        active_paths = db.query(LearningPath).filter(
            LearningPath.status.in_(["active", "paused"])
        ).all()
        
        for path in active_paths:
            completed_count = db.query(LearningPathLesson).filter(
                LearningPathLesson.learning_path_id == path.id,
                LearningPathLesson.is_completed == True
            ).count()
            
            path.completed_lessons = completed_count
            path.progress_percentage = (completed_count / path.total_lessons * 100) if path.total_lessons > 0 else 0
        
        db.commit()
        
        logger.info("Progress recalculation complete", paths_updated=len(active_paths))
        
    except Exception as e:
        logger.error("Failed to recalculate progress", error=str(e))
        db.rollback()
        
    finally:
        db.close()

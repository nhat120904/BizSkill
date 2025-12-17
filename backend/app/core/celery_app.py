from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "bizskill",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks",
        "app.workers.video_tasks",
        "app.workers.maintenance_tasks",
        "app.workers.clip_tasks",
    ]
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 min soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Periodic Tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Poll channels for new videos every 30 minutes
    "poll-channels-for-new-videos": {
        "task": "app.workers.tasks.poll_all_channels",
        "schedule": crontab(minute=f"*/{settings.channel_poll_interval_minutes}"),
    },
    # Check for dead/removed videos daily
    "check-video-availability": {
        "task": "app.workers.maintenance_tasks.check_video_availability",
        "schedule": crontab(hour=3, minute=0),  # 3 AM UTC
    },
    # Clean up old temporary files hourly
    "cleanup-temp-files": {
        "task": "app.workers.maintenance_tasks.cleanup_temp_files",
        "schedule": crontab(minute=0),  # Every hour
    },
}

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "newsroom",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks.publish_tasks",
        "app.workers.tasks.discovery_tasks",
        "app.workers.tasks.cleanup_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

celery_app.conf.beat_schedule = {
    "auto-discover-trending": {
        "task": "app.workers.tasks.discovery_tasks.periodic_discovery_task",
        "schedule": crontab(minute="*/30"),
    },
    "refresh-expiring-tokens": {
        "task": "app.workers.tasks.publish_tasks.refresh_expiring_tokens",
        "schedule": crontab(hour=3, minute=0),
    },
    "cleanup-old-media": {
        "task": "app.workers.tasks.cleanup_tasks.prune_old_media",
        "schedule": crontab(hour=4, minute=0),
    },
}

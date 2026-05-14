import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.workers.tasks.cleanup_tasks.prune_old_media")
def prune_old_media():
    """Removes social card images older than 7 days. Runs daily at 4am UTC."""
    media_dir = Path(settings.MEDIA_DIR)
    if not media_dir.exists():
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    removed = 0

    for file_path in media_dir.glob("*.jpg"):
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                file_path.unlink()
                removed += 1
        except Exception as exc:
            logger.warning("media_cleanup_error", file=str(file_path), error=str(exc))

    logger.info("media_cleanup_complete", removed=removed)

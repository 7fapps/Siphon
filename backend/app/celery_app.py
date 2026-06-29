from celery import Celery, Task
from celery.signals import task_prerun, task_postrun
from app.config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "siphon",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.download"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Strict concurrency control
    worker_concurrency=settings.celery_concurrency,  # Max 2 concurrent tasks
    task_acks_late=True,  # Ack only after task completes
    task_reject_on_worker_lost=True,
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,
    task_time_limit=600,  # 10 min hard limit
    task_soft_time_limit=540,  # 9 min soft limit
)

celery_app.conf.beat_schedule = {
    "cleanup-orphaned-files": {
        "task": "app.tasks.download.cleanup_orphaned_files",
        "schedule": settings.cleanup_interval_minutes * 60.0,  # seconds
    },
}

# Task state helpers
JOB_STATES = {
    "PENDING": "queued",
    "STARTED": "extracting",
    "PROGRESS": "assembling",  # Custom state
    "SUCCESS": "completed",
    "FAILURE": "failed",
    "RETRY": "queued",
    "REVOKED": "failed",
}

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    logger.info(f"[celery] Task {task_id} ({task.name}) started")

@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    logger.info(f"[celery] Task {task_id} ({task.name}) finished with state={state}")

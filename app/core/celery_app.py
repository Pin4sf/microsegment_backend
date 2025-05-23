# app/core/celery_app.py
from celery import Celery
from app.core.config import settings
import os

# Windows-specific settings
os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

celery_app = Celery(
    "microsegment",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks.data_pull_tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_pool='solo',  # Use solo pool for Windows compatibility
    task_track_started=True,
    task_time_limit=3600,  # 1 hour timeout
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1
)

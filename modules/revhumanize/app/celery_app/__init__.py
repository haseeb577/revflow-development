"""Celery application for background jobs"""
from celery import Celery
import os

celery_app = Celery(
    'humanization_pipeline',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://revflow-redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://revflow-redis:6379/0'),
    include=['app.celery_app.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    worker_prefetch_multiplier=1,
)

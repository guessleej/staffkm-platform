"""Celery 應用實例"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "staffkm_knowledge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.process_document", "app.tasks.web_sync", "app.tasks.build_graph"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
    task_routes={
        "app.tasks.process_document.*": {"queue": "knowledge"},
        "app.tasks.web_sync.*":         {"queue": "knowledge"},
        "app.tasks.build_graph.*":      {"queue": "knowledge"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

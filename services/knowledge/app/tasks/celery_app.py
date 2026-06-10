"""Celery 應用實例"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "staffkm_knowledge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.process_document", "app.tasks.web_sync", "app.tasks.build_graph",
             "app.tasks.reindex_embeddings"],
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
        "app.tasks.reindex_embeddings.*": {"queue": "knowledge"},  # 否則進 default queue、worker(-Q knowledge)收不到
        "app.tasks.wiki_gen.*":         {"queue": "knowledge"},    # v5.13 LLM Wiki 生成
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# v5.12: 卡住文件回收 — beat 每 5 分鐘掃一次（需 worker 帶 --beat；單一 knowledge-worker 嵌入式即可）
celery_app.conf.beat_schedule = {
    "reap-stuck-documents": {
        "task": "app.tasks.process_document.reap_stuck_documents",
        "schedule": 300.0,
    },
}


# v5.12: worker 啟動即補跑一次回收（救上一個 worker 重啟時遺失的任務，不必等第一次 beat）。
#   用 send_task by name 避免 import process_document 造成循環匯入。
from celery.signals import worker_ready  # noqa: E402


@worker_ready.connect
def _reap_on_startup(**_kwargs):
    celery_app.send_task(
        "app.tasks.process_document.reap_stuck_documents",
        queue="knowledge", countdown=15,
    )

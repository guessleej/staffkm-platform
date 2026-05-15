"""MinIO 物件儲存工具"""
import io
import structlog
from minio import Minio
from minio.error import S3Error

from app.config import settings

log = structlog.get_logger()


def _client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def _ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)
        log.info("minio_bucket_created", bucket=settings.MINIO_BUCKET)


def upload_document(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
    client = _client()
    _ensure_bucket(client)
    client.put_object(
        settings.MINIO_BUCKET,
        object_key,
        io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type,
    )
    log.info("minio_upload_ok", key=object_key, bytes=len(file_bytes))
    return object_key


def download_document(object_key: str) -> bytes:
    client = _client()
    response = client.get_object(settings.MINIO_BUCKET, object_key)
    try:
        data = response.read()
        log.info("minio_download_ok", key=object_key, bytes=len(data))
        return data
    finally:
        response.close()
        response.release_conn()


def delete_document(object_key: str) -> None:
    client = _client()
    try:
        client.remove_object(settings.MINIO_BUCKET, object_key)
        log.info("minio_delete_ok", key=object_key)
    except S3Error as e:
        log.warning("minio_delete_failed", key=object_key, error=str(e))

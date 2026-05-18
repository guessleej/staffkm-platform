"""Cross-encoder reranker service — v3.4 P3。

POST /rerank
body: { query: str, documents: list[str], top_n?: int }
resp: { indices: list[int], scores: list[float] }   # 依分數排序，indices 對應原 documents 順序
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

from app.config import settings

log = structlog.get_logger()

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    from sentence_transformers import CrossEncoder
    log.info("reranker_model_loading", name=settings.MODEL_NAME, device=settings.MODEL_DEVICE)
    _model = CrossEncoder(
        settings.MODEL_NAME,
        max_length=settings.MAX_LENGTH,
        device=settings.MODEL_DEVICE,
    )
    log.info("reranker_model_loaded")
    return _model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # lazy load on first request；這裡只 log ready
    log.info("reranker_service_ready", model=settings.MODEL_NAME)
    yield


app = FastAPI(title="StaffKM Reranker", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


class RerankRequest(BaseModel):
    query:     str               = Field(..., min_length=1)
    documents: list[str]         = Field(..., min_length=1, max_length=200)
    top_n:     int | None        = None


class RerankResponse(BaseModel):
    indices: list[int]
    scores:  list[float]


@app.post("/rerank", response_model=RerankResponse)
async def rerank(body: RerankRequest):
    model = _load_model()
    pairs = [[body.query, doc] for doc in body.documents]
    # CrossEncoder.predict 是 sync；用 to_thread 避免阻塞 event loop
    try:
        scores = await asyncio.to_thread(model.predict, pairs, batch_size=settings.BATCH_SIZE)
    except Exception as e:
        log.error("rerank_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"rerank inference failed: {e}")

    # 配對 (index, score) 並依 score desc 排
    ranked = sorted(enumerate(scores), key=lambda x: float(x[1]), reverse=True)
    top_n = body.top_n or settings.DEFAULT_TOP_N
    ranked = ranked[:top_n]
    return RerankResponse(
        indices=[i for i, _ in ranked],
        scores=[float(s) for _, s in ranked],
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "reranker", "model": settings.MODEL_NAME}

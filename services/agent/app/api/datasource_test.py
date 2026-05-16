"""Data Source 連線測試 endpoint（RFC-006 D-3）。

設計：不引入額外驅動依賴（避免 Docker image 膨脹）。
  - rest / graphql：用 httpx 對 config.url 發 GET（或 GraphQL introspection）
  - postgres / mysql / mongo / s3：僅驗證 config 必填欄位完整性，回
    「config OK，實際連線測試需在後續同步 worker 中執行」狀態。

回傳 success + latency + reason，供前端顯示。
"""
import time
import uuid

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member

log = structlog.get_logger()
router = APIRouter()


class TestResult(BaseModel):
    success:    bool
    elapsed_ms: int
    detail:     str
    config_ok:  bool = True
    missing:    list[str] = []


# 各 kind 必填欄位（後續同步 worker 會以此為前提）
_REQUIRED: dict[str, tuple[str, ...]] = {
    "postgres": ("host", "port", "database", "user"),
    "mysql":    ("host", "port", "database", "user"),
    "mongo":    ("connection_string",),
    "rest":     ("url",),
    "graphql":  ("url",),
    "s3":       ("endpoint", "bucket"),
}


def _validate_config(kind: str, config: dict) -> tuple[bool, list[str]]:
    required = _REQUIRED.get(kind, ())
    missing = [k for k in required if not config.get(k)]
    return (len(missing) == 0, missing)


async def _test_http(url: str, timeout: float = 10.0, method: str = "GET") -> TestResult:
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url)
        elapsed = int((time.monotonic() - started) * 1000)
        return TestResult(
            success=resp.status_code < 400,
            elapsed_ms=elapsed,
            detail=f"HTTP {resp.status_code}",
        )
    except httpx.TimeoutException:
        return TestResult(
            success=False,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            detail="連線逾時",
        )
    except Exception as e:
        return TestResult(
            success=False,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            detail=f"連線失敗：{e}",
        )


@router.post(
    "/{ds_id}/test",
    response_model=ApiResponse[TestResult],
    summary="測試 Data Source 連線",
)
async def test_data_source(
    ds_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text(
            "SELECT id, kind, config FROM data_sources "
            "WHERE id = :id AND workspace_id = :ws"
        ),
        {"id": str(ds_id), "ws": str(ctx.workspace_id)},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Data Source 不存在")
    d = dict(r._mapping)
    cfg = d["config"] or {}
    kind = d["kind"]

    # 先驗 config 完整性
    config_ok, missing = _validate_config(kind, cfg)
    if not config_ok:
        return ApiResponse(data=TestResult(
            success=False, elapsed_ms=0,
            detail=f"config 缺欄位：{', '.join(missing)}",
            config_ok=False, missing=missing,
        ))

    # 依 kind 分派實際測試
    if kind in ("rest",):
        result = await _test_http(cfg.get("url"))
    elif kind == "graphql":
        # GraphQL introspection 用 POST
        result = await _test_http(cfg.get("url"), method="POST")
    elif kind in ("postgres", "mysql", "mongo", "s3"):
        # 不引入額外驅動；config 完整性已驗，標示為「待後續同步 worker 驗證」
        result = TestResult(
            success=True, elapsed_ms=0,
            detail=f"config 完整；{kind} 實際連線將由同步 worker 驗證",
        )
    else:
        result = TestResult(
            success=False, elapsed_ms=0,
            detail=f"未支援的 kind：{kind}",
        )

    # 成功則記錄 last_synced_at（這裡用「測試成功」當作弱版同步戳記）
    if result.success and kind in ("rest", "graphql"):
        await session.execute(
            text(
                "UPDATE data_sources SET last_synced_at = now() "
                "WHERE id = :id AND workspace_id = :ws"
            ),
            {"id": str(ds_id), "ws": str(ctx.workspace_id)},
        )

    log.info(
        "data_source_test",
        workspace_id=str(ctx.workspace_id),
        ds_id=str(ds_id), kind=kind,
        success=result.success, elapsed=result.elapsed_ms,
    )
    return ApiResponse(data=result)

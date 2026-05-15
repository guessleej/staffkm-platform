"""反向代理工具 — 將請求轉發至下游微服務"""
import httpx
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse


async def proxy_request(
    request: Request,
    target_url: str,
    timeout: float = 60.0,
    stream: bool = False,
) -> StreamingResponse:
    """將 Gateway 收到的請求代理至指定的下游服務。"""
    headers = dict(request.headers)
    # 注入使用者資訊供下游服務使用
    headers["X-User-ID"] = str(getattr(request.state, "user_id", ""))
    headers["X-User-Roles"] = ",".join(getattr(request.state, "roles", []))
    headers["X-Tenant-ID"] = str(getattr(request.state, "tenant_id", ""))
    headers.pop("host", None)

    body = await request.body()

    target_url = target_url.rstrip("/") if target_url.endswith("/") and target_url.count("/") > 3 else target_url

    if stream:
        # Keep client + response alive until the generator is exhausted
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        try:
            upstream = await client.send(
                client.build_request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    params=dict(request.query_params),
                ),
                stream=True,
            )
        except httpx.ConnectError:
            await client.aclose()
            raise HTTPException(status_code=503, detail="下游服務無法連線，請稍後再試")
        except httpx.TimeoutException:
            await client.aclose()
            raise HTTPException(status_code=504, detail="下游服務回應逾時")

        async def stream_generator():
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()

        return StreamingResponse(
            stream_generator(),
            status_code=upstream.status_code,
            headers=dict(upstream.headers),
            media_type=upstream.headers.get("content-type"),
        )

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )
            return StreamingResponse(
                iter([resp.content]),
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.headers.get("content-type"),
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="下游服務無法連線，請稍後再試")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="下游服務回應逾時")

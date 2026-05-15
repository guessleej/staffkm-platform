"""JWT 驗證 Middleware — 公開路徑例外處理"""
import jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

PUBLIC_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/metrics",
    # LINE / Teams webhook
    "/api/v1/integrations/line/webhook",
    "/api/v1/integrations/teams/webhook",
    # 嵌入式 chatbot 公開端點
    "/api/v1/chat/embed",
}

# 以 prefix 比對的公開路徑（不需要 JWT 驗證）
PUBLIC_PREFIXES = (
    "/api/v1/public/",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "未提供授權憑證"},
            )

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            request.state.user_id = payload.get("sub")
            request.state.roles = payload.get("roles", [])
            request.state.tenant_id = payload.get("tenant_id")
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "憑證已過期，請重新登入"},
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "無效的授權憑證"},
            )

        return await call_next(request)

    @staticmethod
    def _extract_token(request: Request) -> str | None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return request.cookies.get("access_token")

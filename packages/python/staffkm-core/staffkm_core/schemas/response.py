"""標準化 API 回應格式"""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "成功"
    code: int = 0


class PagedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    meta: PageMeta
    message: str = "成功"


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: int
    detail: str | None = None

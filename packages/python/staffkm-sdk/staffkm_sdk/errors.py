class StaffKMError(Exception):
    """Base error for all SDK exceptions."""
    def __init__(self, message: str, status_code: int | None = None, detail: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or {}


class AuthError(StaffKMError):
    """401 / 403."""


class QuotaExceeded(StaffKMError):
    """429 — workspace quota 超額。"""

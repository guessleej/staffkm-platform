"""Exception hierarchy for staffKM SDK."""
from __future__ import annotations


class StaffKMError(Exception):
    """Base error from staffKM API."""

    def __init__(self, message: str, status_code: int | None = None, data: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.data = data or {}


class AuthError(StaffKMError):
    """401 / 403."""


class NotFound(StaffKMError):
    """404."""


class QuotaExceeded(StaffKMError):
    """429."""

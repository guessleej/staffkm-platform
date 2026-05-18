"""staffKM Python SDK — v4.5 Theme E.

New top-level module. The legacy ``staffkm_sdk`` package remains for
backwards compatibility; new code should use ``staffkm.StaffKM``.
"""
from .client import StaffKM, AsyncStaffKM
from .exceptions import StaffKMError, AuthError, QuotaExceeded, NotFound

__all__ = [
    "StaffKM",
    "AsyncStaffKM",
    "StaffKMError",
    "AuthError",
    "QuotaExceeded",
    "NotFound",
]

__version__ = "0.2.0"

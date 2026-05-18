"""Resource modules — one per API family."""
from . import (
    auth,
    workspaces,
    knowledge,
    applications,
    chat,
    quota,
    billing,
    plugins,
)

__all__ = [
    "auth",
    "workspaces",
    "knowledge",
    "applications",
    "chat",
    "quota",
    "billing",
    "plugins",
]

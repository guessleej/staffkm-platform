"""Plugin install API — v4.3。

非 workspace-scoped，admin only。掛在 /api/v1/admin/plugins。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from staffkm_core.schemas.response import ApiResponse

router = APIRouter()


def _require_admin(request: Request) -> None:
    if "admin" not in (getattr(request.state, "roles", []) or []):
        raise HTTPException(403, "admin only")


@router.get("", response_model=ApiResponse, summary="列出已 load plugins")
async def list_plugins(request: Request):
    _require_admin(request)
    from app.core.plugin_loader import get_loaded_plugins

    items = []
    for _name, p in get_loaded_plugins().items():
        items.append(
            {
                "name": p.manifest.name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "author": p.manifest.author,
                "license": p.manifest.license,
                "icon": p.manifest.icon,
                "tags": p.manifest.tags,
                "homepage": p.manifest.homepage,
                "repository": p.manifest.repository,
                "min_platform_version": p.manifest.min_platform_version,
                "nodes": list(p.nodes.keys()),
                "providers": list(p.providers.keys()),
                "hooks_count": len(p.hooks),
            }
        )
    return ApiResponse(data={"items": items, "total": len(items)})


@router.post(
    "/reload",
    response_model=ApiResponse,
    summary="reload all plugins (hot reload)",
)
async def reload_plugins(request: Request):
    _require_admin(request)
    from app.core.plugin_loader import load_all_plugins

    loaded = load_all_plugins()
    return ApiResponse(
        data={"reloaded_count": len(loaded), "names": list(loaded.keys())},
        message="plugins reloaded",
    )

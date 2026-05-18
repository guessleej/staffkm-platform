"""Optional decorators — 讓 plugin 作者可以宣告式註冊。

註冊到 module-level registry；`runtime.load_plugin()` 走 manifest 顯式 entry-point
為主，這裡的 registry 是給 inline/快速原型用。
"""
from __future__ import annotations

from typing import Any

_NODE_REGISTRY: dict[str, type] = {}
_PROVIDER_REGISTRY: dict[str, type] = {}
_HOOK_REGISTRY: list[type] = []


def register_node(cls: type) -> type:
    """Decorator：宣告式註冊 node（需設定 node_type class attr）。"""
    nt = getattr(cls, "node_type", "")
    if not nt:
        raise ValueError(f"{cls.__name__} 缺少 node_type class attribute")
    _NODE_REGISTRY[nt] = cls
    return cls


def register_provider(cls: type) -> type:
    pt = getattr(cls, "provider_type", "")
    if not pt:
        raise ValueError(f"{cls.__name__} 缺少 provider_type class attribute")
    _PROVIDER_REGISTRY[pt] = cls
    return cls


def register_hook(cls: type) -> type:
    _HOOK_REGISTRY.append(cls)
    return cls


def get_registered_nodes() -> dict[str, type]:
    return dict(_NODE_REGISTRY)


def get_registered_providers() -> dict[str, type]:
    return dict(_PROVIDER_REGISTRY)


def get_registered_hooks() -> list[type]:
    return list(_HOOK_REGISTRY)


def clear_registry() -> None:
    """測試用——清空所有 registry。"""
    _NODE_REGISTRY.clear()
    _PROVIDER_REGISTRY.clear()
    _HOOK_REGISTRY.clear()


__all__ = [
    "register_node",
    "register_provider",
    "register_hook",
    "get_registered_nodes",
    "get_registered_providers",
    "get_registered_hooks",
    "clear_registry",
]


# 讓 type checker 知道這幾個 symbol 不是 unused
_unused: Any = None

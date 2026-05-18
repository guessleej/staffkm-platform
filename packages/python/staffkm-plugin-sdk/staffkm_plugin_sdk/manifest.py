"""Plugin manifest schema (yaml/json)。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    """plugin.manifest.yaml schema。"""

    name: str = Field(..., min_length=2, max_length=64)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: str = ""
    author: str = ""
    license: str = "MIT"

    # plugin entry points — "module:ClassName"
    nodes: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    hooks: list[str] = Field(default_factory=list)

    # python dependencies (pip-installable)
    requirements: list[str] = Field(default_factory=list)

    # min platform version
    min_platform_version: str = "4.3.0"

    # marketplace metadata
    icon: str = "package"
    tags: list[str] = Field(default_factory=list)
    homepage: str = ""
    repository: str = ""

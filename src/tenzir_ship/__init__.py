"""Core package exports for tenzir-ship."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as metadata_version
from typing import TYPE_CHECKING, Any

__all__ = ["__version__", "Changelog"]

try:
    __version__ = metadata_version("tenzir-ship")
except PackageNotFoundError:  # pragma: no cover - fallback for editable installs
    __version__ = "0.0.0"

if TYPE_CHECKING:  # pragma: no cover
    from .api import Changelog


def __getattr__(name: str) -> Any:  # pragma: no cover - simple delegation
    if name == "Changelog":
        from .api import Changelog as _Changelog

        return _Changelog
    raise AttributeError(f"module 'tenzir_ship' has no attribute {name!r}")

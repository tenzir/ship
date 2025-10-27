"""Core package exports for tenzir-changelog."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as metadata_version

__all__ = ["__version__"]

try:
    __version__ = metadata_version("tenzir-changelog")
except PackageNotFoundError:  # pragma: no cover - fallback for editable installs
    __version__ = "0.0.0"

"""Release manifest operations for changelog display."""

from __future__ import annotations

from pathlib import Path

from packaging.version import InvalidVersion, Version

from ..modules import Module
from ..entries import Entry
from ..config import Config
from ..releases import (
    ReleaseManifest,
    iter_release_manifests,
    load_release_entry,
)

__all__ = [
    "_get_module_latest_version",
    "_get_sorted_release_manifests",
    "_get_release_manifest_before",
    "_get_latest_release_manifest",
    "_gather_module_released_entries",
]


def _get_module_latest_version(module_root: Path) -> str | None:
    """Get the latest release version for a module."""
    versions: list[tuple[Version, str]] = []
    for manifest in iter_release_manifests(module_root):
        label = manifest.version
        prefix = ""
        if label.startswith("v"):
            prefix = "v"
            label = label[1:]
        try:
            versions.append((Version(label), prefix))
        except InvalidVersion:
            continue
    if not versions:
        return None
    versions.sort(key=lambda x: x[0], reverse=True)
    latest_version, prefix = versions[0]
    return f"{prefix}{latest_version}"


def _get_sorted_release_manifests(project_root: Path) -> list[tuple[Version, ReleaseManifest]]:
    """Get release manifests sorted by version number."""
    manifests: list[tuple[Version, ReleaseManifest]] = []
    for manifest in iter_release_manifests(project_root):
        version_str = manifest.version.lstrip("vV")
        try:
            parsed = Version(version_str)
        except InvalidVersion:
            continue
        manifests.append((parsed, manifest))
    manifests.sort(key=lambda item: item[0])
    return manifests


def _get_release_manifest_before(project_root: Path, target_version: str) -> ReleaseManifest | None:
    """Get the release manifest immediately before the target version."""
    target_value = target_version.lstrip("vV")
    try:
        target_parsed = Version(target_value)
    except InvalidVersion:
        return None
    manifests = _get_sorted_release_manifests(project_root)
    previous: ReleaseManifest | None = None
    for parsed, manifest in manifests:
        if parsed >= target_parsed:
            break
        previous = manifest
    return previous


def _get_latest_release_manifest(project_root: Path) -> ReleaseManifest | None:
    """Get the most recent release manifest by version."""
    manifests = _get_sorted_release_manifests(project_root)
    if not manifests:
        return None
    return manifests[-1][1]


def _gather_module_released_entries(
    modules: list[Module],
    previous_module_versions: dict[str, str] | None = None,
    target_module_versions: dict[str, str] | None = None,
) -> tuple[dict[str, tuple[Config, list[Entry]]], dict[str, str]]:
    """Gather released entries from all modules, keyed by module ID."""
    result: dict[str, tuple[Config, list[Entry]]] = {}
    current_versions: dict[str, str] = {}
    previous_versions = previous_module_versions or {}
    target_versions = target_module_versions or {}

    for module in modules:
        module_id = module.config.id
        previous_version_str = previous_versions.get(module_id)
        target_version_str = target_versions.get(module_id)

        latest_version = _get_module_latest_version(module.root)
        if latest_version:
            current_versions[module_id] = latest_version

        previous_version: Version | None = None
        if previous_version_str:
            version_str = previous_version_str.lstrip("v")
            try:
                previous_version = Version(version_str)
            except InvalidVersion:
                pass

        target_version: Version | None = None
        if target_version_str:
            version_str = target_version_str.lstrip("v")
            try:
                target_version = Version(version_str)
            except InvalidVersion:
                pass

        new_entries: list[Entry] = []
        for manifest in iter_release_manifests(module.root):
            release_version_str = manifest.version.lstrip("v")
            try:
                release_version = Version(release_version_str)
            except InvalidVersion:
                continue

            if previous_version is not None and release_version <= previous_version:
                continue

            if target_version is not None and release_version > target_version:
                continue

            for entry_id in manifest.entries:
                entry = load_release_entry(module.root, manifest, entry_id)
                if entry is not None:
                    new_entries.append(entry)

        if new_entries:
            sorted_entries = sorted(
                new_entries,
                key=lambda e: (e.metadata.get("title", "").lower(), e.entry_id),
            )
            result[module_id] = (module.config, sorted_entries)

    return result, current_versions

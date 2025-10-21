"""Release manifest management."""

from __future__ import annotations

from collections.abc import Iterable as IterableCollection
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import yaml

from .entries import Entry

RELEASE_DIR = Path("releases")


@dataclass
class ReleaseManifest:
    """Representation of a release manifest."""

    version: str
    title: str
    description: str
    project: str
    created: date
    entries: list[str]
    intro: str | None = None
    path: Path | None = None


def release_directory(project_root: Path) -> Path:
    """Return the path containing release manifests."""
    return project_root / RELEASE_DIR


def _parse_frontmatter(path: Path) -> tuple[dict[str, object], str | None]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        data = yaml.safe_load(content) or {}
        return data, None
    _, _, remainder = content.partition("---\n")
    frontmatter, _, body = remainder.partition("\n---\n")
    data = yaml.safe_load(frontmatter) or {}
    intro = body.strip() if body else ""
    return data, intro or None


def _parse_created_date(raw_value: object | None) -> date:
    if raw_value is None:
        return date.today()
    return date.fromisoformat(str(raw_value))


def _normalize_entries_field(raw_value: object | None) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, IterableCollection):
        return [str(item) for item in raw_value]
    return [str(raw_value)]


def iter_release_manifests(project_root: Path) -> Iterable[ReleaseManifest]:
    """Yield release manifests from disk."""
    directory = release_directory(project_root)
    if not directory.exists():
        return

    manifest_paths = sorted(directory.glob("*/manifest.yaml"))
    processed_dirs = {path.parent for path in manifest_paths}

    for path in manifest_paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        raw_description = str(data.get("description", "") or "").strip()
        raw_intro = str(data.get("intro", "") or "").strip()
        project_value = data.get("project") or data.get("product", "")

        created_value = _parse_created_date(data.get("created"))
        entries_value = _normalize_entries_field(data.get("entries"))

        version_value = data.get("version") or path.parent.name

        manifest = ReleaseManifest(
            version=str(version_value),
            title=str(data.get("title", "")),
            description=raw_description,
            project=str(project_value or ""),
            created=created_value,
            entries=entries_value,
            intro=raw_intro or None,
            path=path,
        )
        yield manifest

    markdown_paths = [
        path
        for path in sorted(directory.glob("*/README.md"))
        if path.parent not in processed_dirs
    ]
    legacy_paths = sorted(directory.glob("*.md"))
    yaml_paths = sorted(directory.glob("*.yaml"))

    paths = markdown_paths + [path for path in legacy_paths if path.parent not in processed_dirs]
    if not paths:
        paths = yaml_paths

    for path in paths:
        data, body_text = _parse_frontmatter(path)

        raw_description = str(data.get("description", "") or "").strip()
        raw_intro = str(data.get("intro", "") or "").strip()
        project_value = data.get("project")
        if not project_value:
            project_value = data.get("product", "")

        description = raw_description
        intro = raw_intro

        body_text = (body_text or "").strip()
        if body_text:
            if not description:
                if "\n\n" in body_text:
                    description_part, remainder = body_text.split("\n\n", 1)
                    description = description_part.strip()
                    remainder = remainder.strip()
                    if not intro:
                        intro = remainder
                    elif remainder:
                        intro = "\n\n".join([intro, remainder]).strip()
                else:
                    description = body_text
            elif not intro:
                intro = body_text

        created_value = _parse_created_date(data.get("created"))
        entries_value = _normalize_entries_field(data.get("entries"))

        version_value = data.get("version")
        if not version_value:
            if path.name.lower() == "readme.md":
                version_value = path.parent.name
            else:
                version_value = path.stem

        manifest = ReleaseManifest(
            version=str(version_value),
            title=str(data.get("title", "")),
            description=description,
            project=str(project_value or ""),
            created=created_value,
            entries=entries_value,
            intro=intro,
            path=path,
        )
        yield manifest


def used_entry_ids(project_root: Path) -> set[str]:
    """Return a set containing entry IDs that already belong to a release."""
    used = set()
    for manifest in iter_release_manifests(project_root):
        used.update(manifest.entries)
    return used


def unused_entries(entries: Iterable[Entry], used_ids: set[str]) -> list[Entry]:
    """Filter entries that have not yet been included in a release."""
    return [entry for entry in entries if entry.entry_id not in used_ids]


def write_release_manifest(
    project_root: Path,
    manifest: ReleaseManifest,
    readme_content: str,
) -> Path:
    """Serialize and store a release manifest alongside release notes."""
    directory = release_directory(project_root)
    directory.mkdir(parents=True, exist_ok=True)
    release_dir = directory / manifest.version
    if release_dir.exists():
        raise FileExistsError(f"Release directory {release_dir} already exists")
    release_dir.mkdir(parents=True, exist_ok=False)

    manifest_path = release_dir / "manifest.yaml"
    if manifest_path.exists():
        raise FileExistsError(f"Release manifest {manifest_path} already exists")
    payload: dict[str, object] = {
        "version": manifest.version,
        "title": manifest.title,
        "project": manifest.project,
        "created": manifest.created.isoformat(),
        "entries": list(manifest.entries),
    }
    if manifest.description:
        payload["description"] = manifest.description
    if manifest.intro:
        payload["intro"] = manifest.intro
    manifest_payload = yaml.safe_dump(payload, sort_keys=False)
    manifest_path.write_text(manifest_payload, encoding="utf-8")

    readme_path = release_dir / "README.md"
    normalized_readme = readme_content.strip()
    if normalized_readme:
        readme_path.write_text(normalized_readme + "\n", encoding="utf-8")
    else:
        readme_path.write_text("", encoding="utf-8")

    manifest.path = manifest_path
    return manifest_path


def build_entry_release_index(
    project_root: Path, *, project: Optional[str] = None
) -> dict[str, list[str]]:
    """Return a mapping from entry id to associated release versions."""
    index: dict[str, list[str]] = {}
    for manifest in iter_release_manifests(project_root):
        if project and manifest.project and manifest.project != project:
            continue
        for entry_id in manifest.entries:
            versions = index.setdefault(entry_id, [])
            if manifest.version not in versions:
                versions.append(manifest.version)
    for versions in index.values():
        versions.sort()
    return index

"""Release manifest management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
import re
import shutil
from typing import Iterable, Optional

from packaging.version import InvalidVersion, Version
import yaml
from yaml.nodes import Node

from .entries import Entry, read_entry


def _represent_date(dumper: yaml.SafeDumper, data: date) -> Node:
    return dumper.represent_scalar("tag:yaml.org,2002:timestamp", data.isoformat())


def _represent_datetime(dumper: yaml.SafeDumper, data: datetime) -> Node:
    # Use Z suffix for UTC, otherwise use the offset format
    if data.tzinfo is not None and data.utcoffset() == timezone.utc.utcoffset(None):
        # Format as ISO with Z suffix for UTC
        iso_str = data.strftime("%Y-%m-%dT%H:%M:%S")
        if data.microsecond:
            iso_str += f".{data.microsecond:06d}".rstrip("0")
        iso_str += "Z"
    else:
        iso_str = data.isoformat()
    return dumper.represent_scalar("tag:yaml.org,2002:timestamp", iso_str)


yaml.SafeDumper.add_representer(date, _represent_date)
yaml.SafeDumper.add_representer(datetime, _represent_datetime)


class _FoldedString(str):
    """Marker type for YAML folded (>) scalars."""


def _represent_folded_string(dumper: yaml.SafeDumper, data: _FoldedString) -> Node:
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style=">")


# Register custom representation for folded strings.
yaml.SafeDumper.add_representer(_FoldedString, _represent_folded_string)

NOTES_FILENAME = "notes.md"
RELEASE_DIR = Path("releases")
_RELEASE_VERSION_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-rc\.(?P<rc>[1-9]\d*))?$"
)


@dataclass
class ReleaseSource:
    """Provenance metadata describing how a release snapshot was assembled."""

    mode: str
    previous_stable: str | None = None


@dataclass
class ReleaseManifest:
    """Representation of a release manifest.

    The manifest contains a single free-form `intro` field which may include
    a one-line summary and additional introductory Markdown. Older manifests
    used a `description` field; we continue to read it for compatibility but
    only write `intro` going forward.

    For projects with modules, `modules` tracks which version of each
    module was current at release time, enabling incremental module summaries.
    ``source`` persists provenance so later edits and rendering can preserve
    the original release baseline instead of re-inferring it from current repo
    state.
    """

    version: str
    created: date
    entries: list[str] = field(default_factory=list)
    title: str = ""
    intro: str | None = None
    modules: dict[str, str] = field(default_factory=dict)
    source: ReleaseSource | None = None
    path: Path | None = None


def release_directory(project_root: Path) -> Path:
    """Return the path containing release manifests."""
    return project_root / RELEASE_DIR


def normalize_release_version(version: str) -> str:
    """Return a bare semantic version string without a leading tag prefix."""
    normalized_version = version.strip()
    if normalized_version.startswith(("v", "V")):
        normalized_version = normalized_version[1:]
    return normalized_version


def render_release_tag(version: str) -> str:
    """Return the Git tag name for a release version."""
    return f"v{normalize_release_version(version)}"


def is_valid_release_version(version: str) -> bool:
    """Return whether *version* matches the supported release formats."""
    normalized = normalize_release_version(version)
    return _RELEASE_VERSION_PATTERN.fullmatch(normalized) is not None


def is_release_candidate(version: str) -> bool:
    """Return whether *version* identifies an ``-rc.N`` prerelease."""
    normalized = normalize_release_version(version)
    match = _RELEASE_VERSION_PATTERN.fullmatch(normalized)
    return bool(match and match.group("rc") is not None)


def is_stable_release(version: str) -> bool:
    """Return whether *version* identifies a stable release."""
    return is_valid_release_version(version) and not is_release_candidate(version)


def stable_release_version(version: str) -> str:
    """Return the ``X.Y.Z`` base version for a stable release or release candidate."""
    normalized = normalize_release_version(version)
    match = _RELEASE_VERSION_PATTERN.fullmatch(normalized)
    if match is None:
        raise ValueError(f"Invalid release version: {version!r}")
    return f"{match.group('major')}.{match.group('minor')}.{match.group('patch')}"


def parse_release_version(version: str) -> Version:
    """Parse *version* into a :class:`packaging.version.Version`."""
    normalized = normalize_release_version(version)
    if not is_valid_release_version(normalized):
        raise InvalidVersion(f"Invalid release version: {version!r}")
    return Version(normalized)


def release_manifest_root(project_root: Path, manifest: ReleaseManifest) -> Path:
    """Return the base directory for a release manifest."""
    if manifest.path is None:
        return release_directory(project_root) / render_release_tag(manifest.version)
    path = manifest.path
    if path.is_dir():
        return path
    return path.parent


def release_manifest_dirs(project_root: Path, manifests: list[ReleaseManifest]) -> list[Path]:
    """Return the on-disk directories for the provided release manifests."""
    return [release_manifest_root(project_root, manifest) for manifest in manifests]


def remove_release_directories(release_dirs: list[Path]) -> int:
    """Delete release directories and return how many were removed."""
    removed_count = 0
    for release_dir in release_dirs:
        if not release_dir.exists():
            continue
        shutil.rmtree(release_dir)
        removed_count += 1
    return removed_count


def _parse_created_date(raw_value: object | None) -> date:
    if raw_value is None:
        return date.today()
    return date.fromisoformat(str(raw_value))


def _parse_release_source(raw_value: object | None) -> ReleaseSource | None:
    if not isinstance(raw_value, dict):
        return None
    mode = str(raw_value.get("mode", "") or "").strip()
    previous_stable = str(raw_value.get("previous_stable", "") or "").strip() or None
    if not mode and previous_stable is None:
        return None
    return ReleaseSource(
        mode=mode or "unknown",
        previous_stable=previous_stable,
    )


def iter_release_manifests(project_root: Path) -> Iterable[ReleaseManifest]:
    """Yield release manifests from disk."""
    directory = release_directory(project_root)
    if not directory.exists():
        return

    manifest_paths = sorted(directory.glob("*/manifest.yaml"))

    for path in manifest_paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        # Prefer `intro`; fall back to legacy `description` if present.
        raw_intro = str(data.get("intro", "") or "").strip()
        if not raw_intro:
            raw_intro = str(data.get("description", "") or "").strip()
        created_value = _parse_created_date(data.get("created"))

        version_value = data.get("version") or path.parent.name

        title_value = str(data.get("title", ""))
        if not title_value:
            title_value = render_release_tag(str(version_value))

        entry_values = data.get("entries")
        raw_modules = data.get("modules")
        modules: dict[str, str] = {}
        if isinstance(raw_modules, dict):
            modules = {str(k): str(v) for k, v in raw_modules.items()}
        source = _parse_release_source(data.get("source"))

        manifest = ReleaseManifest(
            version=str(version_value),
            created=created_value,
            title=title_value,
            intro=raw_intro or None,
            modules=modules,
            source=source,
            path=path,
        )
        if isinstance(entry_values, list) and entry_values:
            manifest.entries = [str(entry_id) for entry_id in entry_values]
        else:
            entries_dir = path.parent / "entries"
            entry_files = sorted(entries_dir.glob("*.md"))
            manifest.entries = [entry_file.stem for entry_file in entry_files]
        yield manifest


def used_entry_ids(project_root: Path, *, include_prereleases: bool = True) -> set[str]:
    """Return entry IDs that already belong to releases.

    By default, prerelease manifests are included. Pass ``include_prereleases=False``
    when computing which entries have been consumed by stable releases.
    """
    used = set()
    for manifest in iter_release_manifests(project_root):
        if not include_prereleases and not is_stable_release(manifest.version):
            continue
        used.update(manifest.entries)
    return used


def unused_entries(entries: Iterable[Entry], used_ids: set[str]) -> list[Entry]:
    """Filter entries that have not yet been included in a release."""
    return [entry for entry in entries if entry.entry_id not in used_ids]


def serialize_release_manifest(manifest: ReleaseManifest) -> str:
    """Return the YAML payload for a release manifest."""
    payload: dict[str, object] = {
        "created": manifest.created,
    }
    if manifest.title:
        payload["title"] = manifest.title
    if manifest.intro:
        # Emit `intro` using a folded block scalar for readability.
        payload["intro"] = _FoldedString(manifest.intro)
    if manifest.modules:
        payload["modules"] = manifest.modules
    if manifest.source is not None:
        source_payload: dict[str, str] = {}
        if manifest.source.mode:
            source_payload["mode"] = manifest.source.mode
        if manifest.source.previous_stable:
            source_payload["previous_stable"] = manifest.source.previous_stable
        if source_payload:
            payload["source"] = source_payload
    # Use default wrapping width for readability; preserve key order.
    return yaml.safe_dump(payload, sort_keys=False)


def write_release_manifest(
    project_root: Path,
    manifest: ReleaseManifest,
    readme_content: str,
    *,
    overwrite: bool = False,
) -> Path:
    """Serialize and store a release manifest alongside release notes."""
    directory = release_directory(project_root)
    directory.mkdir(parents=True, exist_ok=True)
    release_dir = release_manifest_root(project_root, manifest)
    if not release_dir.exists():
        release_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = release_dir / "manifest.yaml"
    if manifest_path.exists() and not overwrite:
        raise FileExistsError(f"Release manifest {manifest_path} already exists")

    manifest_payload = serialize_release_manifest(manifest)
    manifest_path.write_text(manifest_payload, encoding="utf-8")

    notes_path = release_dir / NOTES_FILENAME
    normalized_notes = readme_content.strip()
    notes_payload = normalized_notes + "\n" if normalized_notes else ""
    notes_path.write_text(notes_payload, encoding="utf-8")

    manifest.path = manifest_path
    return manifest_path


def resolve_release_entry_path(
    project_root: Path, manifest: ReleaseManifest, entry_id: str
) -> Path | None:
    """Return the path to an entry file belonging to a release, if present."""
    root = release_manifest_root(project_root, manifest)
    entry_path = root / "entries" / f"{entry_id}.md"
    if entry_path.exists():
        return entry_path
    return None


def load_release_entry(
    project_root: Path, manifest: ReleaseManifest, entry_id: str
) -> Entry | None:
    """Load a release entry as an Entry instance."""
    entry_path = resolve_release_entry_path(project_root, manifest, entry_id)
    if entry_path is None:
        return None
    return read_entry(entry_path)


def collect_release_entries(
    project_root: Path, *, include_prereleases: bool = True
) -> dict[str, Entry]:
    """Return a mapping of entry ids to entries across release manifests.

    By default, prerelease manifests are included. Pass
    ``include_prereleases=False`` when only stable releases should contribute to
    shipped entry counts.
    """
    collected: dict[str, Entry] = {}
    for manifest in iter_release_manifests(project_root):
        if not include_prereleases and not is_stable_release(manifest.version):
            continue
        for entry_id in manifest.entries:
            if entry_id in collected:
                continue
            entry = load_release_entry(project_root, manifest, entry_id)
            if entry is not None:
                collected[entry_id] = entry
    return collected


def build_entry_release_index(
    project_root: Path, *, project: Optional[str] = None
) -> dict[str, list[str]]:
    """Return a mapping from entry id to associated release versions."""
    index: dict[str, list[str]] = {}
    for manifest in iter_release_manifests(project_root):
        version = render_release_tag(manifest.version)
        for entry_id in manifest.entries:
            versions = index.setdefault(entry_id, [])
            if version not in versions:
                versions.append(version)

    def _version_sort_key(version: str) -> tuple[int, Version | str]:
        try:
            return (0, parse_release_version(version))
        except InvalidVersion:
            return (1, version)

    for versions in index.values():
        versions.sort(key=_version_sort_key)
    return index

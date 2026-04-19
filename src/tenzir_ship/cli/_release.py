"""Release commands for the changelog CLI."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Literal, NoReturn, Optional, cast

import click
from click.core import ParameterSource
from packaging.version import InvalidVersion, Version
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..config import EXPORT_STYLE_COMPACT, Config
from ..entries import Entry, iter_entries
from ..releases import (
    NOTES_FILENAME,
    ReleaseManifest,
    ReleaseSource,
    is_release_candidate,
    is_stable_release,
    is_valid_release_version,
    iter_release_manifests,
    load_release_entry,
    normalize_release_version,
    parse_release_version,
    release_directory,
    release_manifest_dirs,
    release_manifest_root,
    remove_release_directories,
    render_release_tag,
    serialize_release_manifest,
    stable_release_version,
    write_release_manifest,
)
from ..utils import (
    abort_on_user_interrupt,
    console,
    create_annotated_git_tag,
    create_git_commit,
    emit_output,
    format_bold,
    get_push_branch_info,
    has_staged_changes,
    log_info,
    log_success,
    log_warning,
    push_current_branch,
    push_git_tag,
)
from ..version_files import apply_version_file_updates, plan_version_file_updates
from ._core import (
    CLIContext,
    ENTRY_EXPORT_ORDER,
    ENTRY_TYPE_EMOJIS,
    _enforce_structure_is_valid,
    _warn_on_structure_issues,
    compact_option,
    explicit_links_option,
)
from ._rendering import (
    _print_renderable,
    _compose_release_document,
    _render_release_notes,
    _render_release_notes_compact,
    _render_module_entries_compact,
    _release_entry_sort_key,
)
from ._export import _entry_to_dict
from ._manifests import (
    _find_release_manifest,
    _get_latest_release_manifest,
    _get_previous_stable_manifest,
    _get_release_manifest_before,
)
from ._show import (
    _collect_unused_entries_for_release,
    _gather_module_released_entries,
)


class StepStatus(Enum):
    """Status of a release workflow step."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ReleaseStep:
    """A single step in the release workflow."""

    name: str
    command: str
    status: StepStatus = StepStatus.PENDING


@dataclass
class StepTracker:
    """Tracks progress through release workflow steps."""

    steps: list[ReleaseStep] = field(default_factory=list)

    def add(self, name: str, command: str) -> None:
        """Add a step to track."""
        self.steps.append(ReleaseStep(name, command))

    def complete(self, name: str) -> None:
        """Mark a step as completed."""
        for step in self.steps:
            if step.name == name:
                step.status = StepStatus.COMPLETED

    def skip(self, name: str) -> None:
        """Mark a step as skipped."""
        for step in self.steps:
            if step.name == name:
                step.status = StepStatus.SKIPPED

    def fail(self, name: str) -> None:
        """Mark a step as failed."""
        for step in self.steps:
            if step.name == name:
                step.status = StepStatus.FAILED

    def update_command(self, name: str, command: str) -> None:
        """Update the command string for a step."""
        for step in self.steps:
            if step.name == name:
                step.command = command


def _render_release_progress(tracker: StepTracker) -> None:
    """Render release progress summary to stderr on failure."""
    total = len(tracker.steps)
    done = len([s for s in tracker.steps if s.status == StepStatus.COMPLETED])
    progress = f"{done}/{total}"

    lines: list[str] = []
    for step in tracker.steps:
        if step.status == StepStatus.COMPLETED:
            icon = "[green]\u2714[/green]"
            cmd = f"[dim]{escape(step.command)}[/dim]"
        elif step.status == StepStatus.FAILED:
            icon = "[red]\u2718[/red]"
            cmd = f"[red]{escape(step.command)}[/red]"
        elif step.status == StepStatus.SKIPPED:
            continue  # Don't show skipped steps
        else:  # PENDING
            icon = "[dim]\u25cb[/dim]"
            cmd = f"[dim]{escape(step.command)}[/dim]"
        lines.append(f"{icon} {cmd}")

    if lines:
        content = Text.from_markup("\n".join(lines))
        title = f"Release Progress ({progress})"
        _print_renderable(Panel(content, title=title, border_style="red"))

    for step in tracker.steps:
        if step.status == StepStatus.FAILED:
            console.print()
            console.print("[bold]To retry the failed step, run:[/bold]", highlight=False)
            console.print(f"  {step.command}", highlight=False, markup=False, soft_wrap=True)


__all__ = [
    "build_release_plan_payload",
    "create_release",
    "publish_release",
    "release_group",
    "release_plan_cmd",
    "release_create_cmd",
    "release_version_cmd",
    "release_publish_cmd",
    # Helper functions
    "_find_release_manifest",
    "_github_release_exists",
    "_latest_semver",
    "_bump_version_value",
    "_validate_semver_label",
    "_resolve_release_version",
]

# Status table cells for release create
STATUS_TABLE_CELLS = {
    "existing": Text("•", style="dim"),
    "new": Text("+", style="green bold"),
}

ReleaseBump = Literal["patch", "minor", "major"]
ReleaseVersionSource = Literal["explicit", "manual", "auto"]


@dataclass
class ModuleReleasePlan:
    """Resolved module snapshot and rendered entry selection for a release."""

    entries_by_module: dict[str, tuple[Config, list[Entry]]]
    version_map: dict[str, str]
    previous_release: ReleaseManifest | None


@dataclass
class ReleaseSnapshotPlan:
    """Resolved release snapshot inputs shared by planning and creation."""

    version: str
    tag_version: str
    version_source: ReleaseVersionSource
    release_candidate: bool
    is_prerelease: bool
    release_mode: str
    existing_manifest: ReleaseManifest | None
    active_rc_series: list[ReleaseManifest]
    active_rc_manifest: ReleaseManifest | None
    source_manifest: ReleaseManifest | None
    metadata_source_manifest: ReleaseManifest | None
    previous_release: ReleaseManifest | None
    copy_entries: bool
    selected_entries: list[Entry]
    new_entries: list[Entry]
    entries_sorted: list[Entry]
    cleanup_unreleased_paths: list[Path]
    cleanup_missing_entry_ids: list[str]
    module_plan: ModuleReleasePlan


def _resolve_default_release_metadata(
    config: Config,
    tag_version: str,
    *,
    existing_manifest: ReleaseManifest | None,
    metadata_source_manifest: ReleaseManifest | None,
) -> tuple[str, str | None]:
    """Return the title and intro that release creation would inherit by default."""

    default_release_title = f"{config.name} {tag_version}"
    source_release_title = None
    if metadata_source_manifest is not None:
        source_tag = render_release_tag(metadata_source_manifest.version)
        if metadata_source_manifest.title in {source_tag, f"{config.name} {source_tag}"}:
            source_release_title = default_release_title
        else:
            source_release_title = metadata_source_manifest.title
    release_title = (
        source_release_title
        if source_release_title is not None
        else existing_manifest.title
        if existing_manifest
        else default_release_title
    )
    if metadata_source_manifest is not None:
        release_intro = (
            metadata_source_manifest.intro.strip() if metadata_source_manifest.intro else None
        )
    elif existing_manifest and existing_manifest.intro:
        release_intro = existing_manifest.intro.strip() or None
    else:
        release_intro = None
    return release_title, release_intro


def _count_entries_by_type(entries: list[Entry]) -> dict[str, int]:
    counts = {entry_type: 0 for entry_type in ENTRY_EXPORT_ORDER}
    for entry in entries:
        entry_type = str(entry.metadata.get("type", "change"))
        counts[entry_type] = counts.get(entry_type, 0) + 1
    counts["total"] = len(entries)
    return counts


def _select_highlight_entries(entries: list[Entry], *, limit: int = 3) -> list[Entry]:
    type_priority = {entry_type: index for index, entry_type in enumerate(ENTRY_EXPORT_ORDER)}
    ordered = sorted(
        entries,
        key=lambda entry: (
            type_priority.get(str(entry.metadata.get("type", "change")), len(type_priority)),
            _release_entry_sort_key(entry),
        ),
    )
    return ordered[:limit]


def _build_module_plan_payload(module_plan: ModuleReleasePlan) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for module_id in sorted(module_plan.entries_by_module.keys()):
        module_config, module_entries = module_plan.entries_by_module[module_id]
        payload.append(
            {
                "id": module_id,
                "name": module_config.name,
                "version": module_plan.version_map.get(module_id),
                "entry_counts": _count_entries_by_type(module_entries),
                "entries": [
                    _entry_to_dict(entry, module_config, compact=True) for entry in module_entries
                ],
            }
        )
    return payload


def _plan_release_snapshot(
    ctx: CLIContext,
    *,
    version: str | None,
    version_bump: ReleaseBump | None,
    release_candidate: bool,
) -> ReleaseSnapshotPlan:
    """Resolve the release snapshot that would be created for the current inputs."""

    config = ctx.ensure_config()
    project_root = ctx.project_root
    requested_version = version
    active_rc_series = _get_active_release_candidate_series(project_root)

    preview_entries = _collect_unused_entries_for_release(
        project_root,
        config,
        include_prereleases=False,
    )
    version, version_source = _resolve_requested_release_version(
        project_root,
        version,
        version_bump,
        unreleased_entries=preview_entries,
        release_candidate=release_candidate,
    )
    tag_version = render_release_tag(version)
    existing_manifest = _find_release_manifest(project_root, version)
    if version_source in {"manual", "auto"} and existing_manifest is not None:
        follow_up = (
            "Supply a different bump flag or explicit version."
            if version_source == "manual"
            else "Supply an explicit version or a manual bump flag."
        )
        raise click.ClickException(f"Release '{tag_version}' already exists. {follow_up}")

    active_rc_manifest = active_rc_series[-1] if active_rc_series else None
    active_rc_base = (
        stable_release_version(active_rc_manifest.version)
        if active_rc_manifest is not None
        else None
    )

    source_manifest = None
    if not release_candidate and active_rc_manifest is not None and active_rc_base is not None:
        active_rc_target = parse_release_version(active_rc_base)
        resolved_version = parse_release_version(version)
        if requested_version is None and version_bump is None:
            source_manifest = active_rc_manifest
        elif normalize_release_version(version) == active_rc_base:
            raise click.ClickException(
                f"Release candidates already exist for '{active_rc_base}'. "
                f"Omit the version and bump flags to promote {render_release_tag(active_rc_manifest.version)} automatically, "
                "or use --rc to continue the RC series."
            )
        elif (
            requested_version is not None
            and existing_manifest is None
            and resolved_version < active_rc_target
        ):
            raise click.ClickException(
                f"Cannot create {tag_version} while {render_release_tag(active_rc_manifest.version)} is active because "
                f"it does not advance beyond the active RC target {render_release_tag(active_rc_base)}. "
                "Omit the version and bump flags to promote the latest candidate automatically, "
                "or choose an explicit later version."
            )
        elif version_bump is not None and resolved_version <= active_rc_target:
            raise click.ClickException(
                f"Cannot use --{version_bump} while {render_release_tag(active_rc_manifest.version)} is active because "
                f"it resolves to {tag_version}, which does not advance beyond the active RC target "
                f"{render_release_tag(active_rc_base)}. Omit the bump flag to promote the latest candidate automatically, "
                "or choose a higher bump or explicit later version."
            )
    closing_active_rc_cycle = (
        not release_candidate and existing_manifest is None and active_rc_manifest is not None
    )
    metadata_source_manifest = (
        active_rc_manifest
        if active_rc_manifest is not None and (release_candidate or closing_active_rc_cycle)
        else source_manifest
    )
    is_prerelease = release_candidate
    copy_entries = release_candidate or source_manifest is not None
    release_mode = (
        "snapshot-prerelease"
        if release_candidate
        else "promote-prerelease"
        if source_manifest is not None
        else "sync-stable-queue"
    )

    if release_candidate:
        selected_entries = _build_cumulative_release_candidate_entries(
            project_root, config, active_rc_series
        )
    elif source_manifest is not None:
        selected_entries = _load_manifest_entries(project_root, source_manifest)
    else:
        selected_entries = _collect_unused_entries_for_release(
            project_root,
            config,
            include_prereleases=existing_manifest is not None,
        )

    _, new_entries, entries_sorted = _combine_release_entries(
        existing_manifest, selected_entries, project_root
    )
    cleanup_unreleased_paths: list[Path] = []
    cleanup_missing_entry_ids: list[str] = []
    if source_manifest is not None:
        cleanup_unreleased_paths, cleanup_missing_entry_ids = _plan_promoted_unreleased_cleanup(
            project_root,
            config,
            source_manifest,
        )

    previous_release = _resolve_release_baseline(
        project_root,
        version=version,
        existing_manifest=existing_manifest,
        source_manifest=source_manifest,
    )
    module_plan = _build_module_release_plan(
        ctx,
        project_root,
        existing_manifest=existing_manifest,
        source_manifest=source_manifest,
        is_prerelease=is_prerelease,
        previous_release=previous_release,
    )
    return ReleaseSnapshotPlan(
        version=version,
        tag_version=tag_version,
        version_source=version_source,
        release_candidate=release_candidate,
        is_prerelease=is_prerelease,
        release_mode=release_mode,
        existing_manifest=existing_manifest,
        active_rc_series=active_rc_series,
        active_rc_manifest=active_rc_manifest,
        source_manifest=source_manifest,
        metadata_source_manifest=metadata_source_manifest,
        previous_release=previous_release,
        copy_entries=copy_entries,
        selected_entries=selected_entries,
        new_entries=new_entries,
        entries_sorted=entries_sorted,
        cleanup_unreleased_paths=cleanup_unreleased_paths,
        cleanup_missing_entry_ids=cleanup_missing_entry_ids,
        module_plan=module_plan,
    )


def build_release_plan_payload(
    ctx: CLIContext,
    *,
    version: str | None,
    version_bump: str | None,
    release_candidate: bool,
) -> dict[str, object]:
    """Return a machine-readable description of the next release snapshot."""

    _enforce_structure_is_valid(ctx, action="plan a release")
    config = ctx.ensure_config()
    normalized_bump = _coerce_release_bump(version_bump)
    snapshot = _plan_release_snapshot(
        ctx,
        version=version,
        version_bump=normalized_bump,
        release_candidate=release_candidate,
    )
    resolved_title, resolved_intro = _resolve_default_release_metadata(
        config,
        snapshot.tag_version,
        existing_manifest=snapshot.existing_manifest,
        metadata_source_manifest=snapshot.metadata_source_manifest,
    )
    entry_counts = _count_entries_by_type(snapshot.entries_sorted)
    highlights = _select_highlight_entries(snapshot.entries_sorted)
    return {
        "project": {
            "id": config.id,
            "name": config.name,
            "repository": config.repository,
        },
        "release": {
            "version": snapshot.tag_version,
            "version_source": snapshot.version_source,
            "mode": snapshot.release_mode,
            "prerelease": snapshot.is_prerelease,
            "release_candidate": snapshot.release_candidate,
            "existing": snapshot.existing_manifest is not None,
            "copy_entries": snapshot.copy_entries,
            "resolved_title": resolved_title,
            "resolved_intro": resolved_intro,
            "active_release_candidate": (
                render_release_tag(snapshot.active_rc_manifest.version)
                if snapshot.active_rc_manifest is not None
                else None
            ),
            "source_release_candidate": (
                render_release_tag(snapshot.source_manifest.version)
                if snapshot.source_manifest is not None
                else None
            ),
            "previous_stable": (
                render_release_tag(snapshot.previous_release.version)
                if snapshot.previous_release is not None
                else None
            ),
            "entry_counts": entry_counts,
        },
        "entries": [_entry_to_dict(entry, config) for entry in snapshot.entries_sorted],
        "highlights": [_entry_to_dict(entry, config, compact=True) for entry in highlights],
        "modules": _build_module_plan_payload(snapshot.module_plan),
    }


def _github_release_exists(repository: str, tag_name: str, gh_path: str) -> bool:
    command = [gh_path, "release", "view", tag_name, "--repo", repository]
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError as exc:  # pragma: no cover - handled earlier
        raise click.ClickException("The 'gh' CLI is required but was not found in PATH.") from exc
    except subprocess.CalledProcessError:
        return False


def _latest_semver(project_root: Path, *, stable_only: bool = True) -> Version | None:
    versions: list[Version] = []
    for manifest in iter_release_manifests(project_root):
        if stable_only and is_release_candidate(manifest.version):
            continue
        try:
            parsed = parse_release_version(manifest.version)
        except InvalidVersion:
            continue
        versions.append(parsed)
    if not versions:
        return None
    versions.sort()
    return versions[-1]


def _bump_version_value(base: Version, bump: str) -> Version:
    major, minor, micro = (list(base.release) + [0, 0, 0])[:3]
    if bump == "major":
        major += 1
        minor = 0
        micro = 0
    elif bump == "minor":
        minor += 1
        micro = 0
    else:
        micro += 1
    return Version(f"{major}.{minor}.{micro}")


def _latest_bump_base_semver(project_root: Path) -> Version | None:
    """Return the semantic version used as the base for the next bump.

    Prefer the latest stable release. If the project only has release
    candidates so far, fall back to the newest candidate's base version.
    """
    latest_stable = _latest_semver(project_root)
    if latest_stable is not None:
        return latest_stable
    return _latest_semver(project_root, stable_only=False)


def _next_version_for_bump(
    project_root: Path,
    bump: ReleaseBump,
    *,
    include_prerelease_fallback: bool = True,
) -> str:
    latest = (
        _latest_bump_base_semver(project_root)
        if include_prerelease_fallback
        else _latest_semver(project_root)
    )
    base_version = Version("0.0.0") if latest is None else latest
    next_version = _bump_version_value(base_version, bump)
    return str(next_version)


def _infer_release_bump(unreleased_entries: list[Entry]) -> ReleaseBump | None:
    if not unreleased_entries:
        return None
    if any(entry.type == "breaking" for entry in unreleased_entries):
        return "major"
    if any(entry.type in {"feature", "change"} for entry in unreleased_entries):
        return "minor"
    return "patch"


def _infer_next_release_version(
    project_root: Path,
    unreleased_entries: list[Entry],
    *,
    include_prerelease_fallback: bool = True,
) -> str | None:
    bump = _infer_release_bump(unreleased_entries)
    if bump is None:
        return None
    return _next_version_for_bump(
        project_root,
        bump,
        include_prerelease_fallback=include_prerelease_fallback,
    )


def _validate_semver_label(version: str) -> None:
    value = normalize_release_version(version)
    if is_valid_release_version(value):
        return
    raise click.ClickException(
        "Release version must use X.Y.Z or X.Y.Z-rc.N (for example 1.2.3, v1.2.3, or 1.2.3-rc.1)."
    )


def _is_current_or_newer_release(project_root: Path, version: str) -> bool:
    latest = _latest_semver(project_root)
    if latest is None:
        return True

    try:
        target = parse_release_version(version)
    except InvalidVersion:
        return False
    return target >= latest


def _resolve_release_version(
    project_root: Path,
    explicit: Optional[str],
    bump: ReleaseBump | None,
    *,
    unreleased_entries: list[Entry],
    include_prerelease_fallback: bool = True,
) -> tuple[str, ReleaseVersionSource]:
    if explicit is not None and bump:
        raise click.ClickException("Provide either a version argument or a bump flag, not both.")
    if explicit is not None:
        value = explicit.strip()
        if not value:
            raise click.ClickException("Release version cannot be empty.")
        _validate_semver_label(value)
        return normalize_release_version(value), "explicit"
    if bump:
        return (
            _next_version_for_bump(
                project_root,
                bump,
                include_prerelease_fallback=include_prerelease_fallback,
            ),
            "manual",
        )

    inferred = _infer_next_release_version(
        project_root,
        unreleased_entries,
        include_prerelease_fallback=include_prerelease_fallback,
    )
    if inferred is None:
        raise click.ClickException(
            "Cannot auto-bump release version because no unreleased changelog entries were "
            "found. Provide a version argument or specify one of --patch/--minor/--major."
        )
    return inferred, "auto"


def _resolve_release_candidate_base_version(
    project_root: Path,
    explicit: Optional[str],
    bump: ReleaseBump | None,
    *,
    unreleased_entries: list[Entry],
) -> tuple[str, ReleaseVersionSource]:
    if explicit is None:
        if bump is None:
            active_series = _get_active_release_candidate_series(project_root)
            if active_series:
                return stable_release_version(active_series[-1].version), "auto"
        return _resolve_release_version(
            project_root,
            explicit,
            bump,
            unreleased_entries=unreleased_entries,
            include_prerelease_fallback=False,
        )

    value = explicit.strip()
    if not value:
        raise click.ClickException("Release version cannot be empty.")
    _validate_semver_label(value)
    normalized = normalize_release_version(value)
    if is_release_candidate(normalized):
        raise click.ClickException(
            "Use --rc with a stable base version like 1.2.3, or omit the version "
            "to continue the current RC series."
        )
    return _resolve_release_version(
        project_root,
        explicit,
        bump,
        unreleased_entries=unreleased_entries,
        include_prerelease_fallback=False,
    )


def _next_release_candidate_version(project_root: Path, base_version: str) -> str:
    normalized_base = normalize_release_version(base_version)
    if not is_stable_release(normalized_base):
        raise click.ClickException("Release candidates require a stable base version like 1.2.3.")

    existing_stable = _find_release_manifest(project_root, normalized_base)
    if existing_stable is not None and is_stable_release(existing_stable.version):
        raise click.ClickException(
            f"Stable release '{render_release_tag(normalized_base)}' already exists. "
            "Provide a newer base version or omit --rc."
        )

    active_series = _get_active_release_candidate_series(project_root)
    if active_series and stable_release_version(active_series[-1].version) != normalized_base:
        raise click.ClickException(
            "Outstanding release candidates already exist: "
            f"{render_release_tag(active_series[-1].version)}. Continue the current RC flow with --rc, or "
            "promote the outstanding candidate to a stable release before "
            "starting a different RC series."
        )

    if not active_series:
        return f"{normalized_base}-rc.1"

    latest_candidate = active_series[-1]
    parsed = parse_release_version(latest_candidate.version)
    if parsed.pre is None or parsed.pre[0] != "rc":
        raise click.ClickException(
            f"Unsupported release candidate version: {render_release_tag(latest_candidate.version)}."
        )
    return f"{normalized_base}-rc.{parsed.pre[1] + 1}"


def _resolve_requested_release_version(
    project_root: Path,
    explicit: Optional[str],
    bump: ReleaseBump | None,
    *,
    unreleased_entries: list[Entry],
    release_candidate: bool,
) -> tuple[str, ReleaseVersionSource]:
    if not release_candidate:
        if explicit is not None:
            value = explicit.strip()
            if not value:
                raise click.ClickException("Release version cannot be empty.")
            _validate_semver_label(value)
            normalized = normalize_release_version(value)
            if is_release_candidate(normalized):
                raise click.ClickException(
                    "Release candidate versions must be created with --rc from a stable "
                    "base version like 1.2.3. Use 'release create --rc' to continue the "
                    "current RC series, or omit the version and bump flags to promote "
                    "the latest candidate."
                )
        if explicit is None and bump is None:
            active_series = _get_active_release_candidate_series(project_root)
            if active_series:
                return stable_release_version(active_series[-1].version), "auto"
        return _resolve_release_version(
            project_root,
            explicit,
            bump,
            unreleased_entries=unreleased_entries,
        )

    base_version, version_source = _resolve_release_candidate_base_version(
        project_root,
        explicit,
        bump,
        unreleased_entries=unreleased_entries,
    )
    return _next_release_candidate_version(project_root, base_version), version_source


def _resolve_manual_bump_flags(*, patch: bool, minor: bool, major: bool) -> ReleaseBump | None:
    selected: list[ReleaseBump] = []
    if patch:
        selected.append("patch")
    if minor:
        selected.append("minor")
    if major:
        selected.append("major")
    if len(selected) > 1:
        raise click.ClickException("Use only one of --patch, --minor, or --major.")
    return selected[0] if selected else None


def _coerce_release_bump(value: Optional[str]) -> ReleaseBump | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in {"patch", "minor", "major"}:
        raise click.ClickException("Invalid bump value. Expected one of: patch, minor, or major.")
    return cast(ReleaseBump, normalized)


def _collect_current_unreleased_entries(project_root: Path, config: Config) -> list[Entry]:
    """Return all entries currently present in ``unreleased/`` for this project.

    Unlike ``_collect_unused_entries_for_release``, this intentionally keeps
    entries that already appear in release candidates because RC creation
    snapshots by copying entries instead of consuming them.
    """
    all_entries = list(iter_entries(project_root))
    return [entry for entry in all_entries if entry.project is None or entry.project == config.id]


def _load_manifest_entries(project_root: Path, manifest: ReleaseManifest) -> list[Entry]:
    entries: list[Entry] = []
    for entry_id in manifest.entries:
        entry = load_release_entry(project_root, manifest, entry_id)
        if entry is None:
            raise click.ClickException(
                f"Release '{manifest.version}' is missing entry file for '{entry_id}'. "
                "Recreate or repair the release before reusing it."
            )
        entries.append(entry)
    return entries


def _get_outstanding_release_candidate_series(
    project_root: Path,
) -> dict[str, list[ReleaseManifest]]:
    """Return RC series whose stable release has not been cut yet."""
    stable_versions: set[str] = set()
    candidates_by_base: dict[str, list[tuple[Version, ReleaseManifest]]] = {}
    for manifest in iter_release_manifests(project_root):
        try:
            parsed = parse_release_version(manifest.version)
        except InvalidVersion:
            continue
        base_version = stable_release_version(manifest.version)
        if is_release_candidate(manifest.version):
            candidates_by_base.setdefault(base_version, []).append((parsed, manifest))
        else:
            stable_versions.add(base_version)

    outstanding: dict[str, list[ReleaseManifest]] = {}
    for base_version, candidates in candidates_by_base.items():
        if base_version in stable_versions:
            continue
        candidates.sort(key=lambda item: item[0])
        outstanding[base_version] = [manifest for _, manifest in candidates]
    return outstanding


def _get_active_release_candidate_series(project_root: Path) -> list[ReleaseManifest]:
    """Return the single active RC series sorted from oldest to newest."""
    outstanding = _get_outstanding_release_candidate_series(project_root)
    if not outstanding:
        return []
    if len(outstanding) > 1:
        raise click.ClickException(
            "Multiple release candidate series exist in releases/. Remove stale RC "
            "directories so only one RC cycle remains before continuing."
        )
    return next(iter(outstanding.values()))


def _resolve_release_baseline(
    project_root: Path,
    version: str,
    existing_manifest: ReleaseManifest | None,
    source_manifest: ReleaseManifest | None,
) -> ReleaseManifest | None:
    """Resolve the stable baseline that this release snapshot compares against."""
    baseline_holder = source_manifest or existing_manifest
    if baseline_holder is not None:
        recorded = _get_previous_stable_manifest(project_root, baseline_holder)
        if recorded is not None:
            return recorded
    return _get_release_manifest_before(project_root, version, stable_only=True)


def _resolve_release_source(
    *,
    existing_manifest: ReleaseManifest | None,
    mode: str,
    new_entries: list[Entry],
    previous_release: ReleaseManifest | None,
) -> ReleaseSource | None:
    """Persist provenance for the release snapshot unless this is metadata-only."""
    if existing_manifest is not None and not new_entries:
        return existing_manifest.source

    return ReleaseSource(
        mode=mode,
        previous_stable=(
            render_release_tag(previous_release.version) if previous_release is not None else None
        ),
    )


def _build_cumulative_release_candidate_entries(
    project_root: Path,
    config: Config,
    active_series: list[ReleaseManifest],
) -> list[Entry]:
    latest_candidate = active_series[-1] if active_series else None
    selected_entries: dict[str, Entry] = {}
    if latest_candidate is not None:
        for entry in _load_manifest_entries(project_root, latest_candidate):
            selected_entries[entry.entry_id] = entry
    for entry in _collect_current_unreleased_entries(project_root, config):
        selected_entries[entry.entry_id] = entry
    entries = list(selected_entries.values())
    entries.sort(key=_release_entry_sort_key)
    return entries


def _combine_release_entries(
    existing_manifest: ReleaseManifest | None,
    selected_entries: list[Entry],
    project_root: Path,
) -> tuple[list[Entry], list[Entry], list[Entry]]:
    existing_entries: list[Entry] = []
    existing_entry_ids: set[str] = set()
    if existing_manifest is not None:
        existing_entries = _load_manifest_entries(project_root, existing_manifest)
        existing_entry_ids = {entry.entry_id for entry in existing_entries}

    new_entries = [entry for entry in selected_entries if entry.entry_id not in existing_entry_ids]
    combined_entries: dict[str, Entry] = {entry.entry_id: entry for entry in existing_entries}
    for entry in new_entries:
        combined_entries[entry.entry_id] = entry
    combined = list(combined_entries.values())
    combined.sort(key=_release_entry_sort_key)
    return existing_entries, new_entries, combined


def _plan_promoted_unreleased_cleanup(
    project_root: Path,
    config: Config,
    source_manifest: ReleaseManifest,
) -> tuple[list[Path], list[str]]:
    current_unreleased_entries = _collect_current_unreleased_entries(project_root, config)
    unreleased_entries_by_id = {entry.entry_id: entry for entry in current_unreleased_entries}
    promoted_entries_by_id = {
        entry.entry_id: entry for entry in _load_manifest_entries(project_root, source_manifest)
    }

    diverged_entry_ids: list[str] = []
    for entry_id, promoted_entry in sorted(promoted_entries_by_id.items()):
        current_entry = unreleased_entries_by_id.get(entry_id)
        if current_entry is None:
            continue
        if current_entry.path.read_bytes() != promoted_entry.path.read_bytes():
            diverged_entry_ids.append(entry_id)
    if diverged_entry_ids:
        quoted_ids = ", ".join(f"'{entry_id}'" for entry_id in diverged_entry_ids)
        source_tag = render_release_tag(source_manifest.version)
        raise click.ClickException(
            "Cannot promote "
            f"{source_tag} because unreleased entries changed after the release "
            f"candidate snapshot was created: {quoted_ids}. Move the follow-up changes "
            "into new unreleased entries and create another release candidate before "
            "promoting to stable."
        )

    cleanup_paths: list[Path] = []
    missing_entry_ids: list[str] = []
    for entry_id in sorted(promoted_entries_by_id):
        current_entry = unreleased_entries_by_id.get(entry_id)
        if current_entry is None:
            missing_entry_ids.append(entry_id)
            continue
        cleanup_paths.append(current_entry.path)
    return cleanup_paths, missing_entry_ids


def _build_module_release_plan(
    ctx: CLIContext,
    project_root: Path,
    *,
    existing_manifest: ReleaseManifest | None,
    source_manifest: ReleaseManifest | None,
    is_prerelease: bool,
    previous_release: ReleaseManifest | None,
) -> ModuleReleasePlan:
    """Resolve module versions and entries for the release snapshot."""
    modules = ctx.get_modules()
    if not modules:
        return ModuleReleasePlan({}, {}, previous_release)

    previous_module_versions = previous_release.modules if previous_release else None

    if source_manifest is not None:
        target_versions = dict(source_manifest.modules)
        if not target_versions:
            return ModuleReleasePlan({}, {}, previous_release)
        entries_by_module, _ = _gather_module_released_entries(
            modules,
            previous_module_versions,
            target_versions,
            include_prereleases=is_release_candidate(source_manifest.version),
        )
        return ModuleReleasePlan(entries_by_module, target_versions, previous_release)

    if existing_manifest is not None:
        target_versions = dict(existing_manifest.modules)
        if not target_versions:
            return ModuleReleasePlan({}, {}, previous_release)
        entries_by_module, _ = _gather_module_released_entries(
            modules,
            previous_module_versions,
            target_versions,
            include_prereleases=(
                is_prerelease
                or any(is_release_candidate(version) for version in target_versions.values())
            ),
        )
        return ModuleReleasePlan(entries_by_module, target_versions, previous_release)

    entries_by_module, current_versions = _gather_module_released_entries(
        modules,
        previous_module_versions,
        include_prereleases=is_prerelease,
    )
    return ModuleReleasePlan(entries_by_module, current_versions, previous_release)


def create_release(
    ctx: CLIContext,
    *,
    version: Optional[str],
    title: Optional[str],
    intro_text: Optional[str],
    release_date: Optional[datetime],
    intro_file: Optional[Path],
    compact: Optional[bool],
    explicit_links: bool = False,
    assume_yes: bool,
    version_bump: Optional[str],
    release_candidate: bool,
    title_explicit: bool,
    compact_explicit: bool,
) -> None:
    """Python wrapper for release creation that mirrors CLI behavior."""

    config = ctx.ensure_config()
    _enforce_structure_is_valid(ctx, action="create a release")
    project_root = ctx.project_root
    normalized_bump = _coerce_release_bump(version_bump)
    snapshot = _plan_release_snapshot(
        ctx,
        version=version,
        version_bump=normalized_bump,
        release_candidate=release_candidate,
    )

    version = snapshot.version
    tag_version = snapshot.tag_version
    existing_manifest = snapshot.existing_manifest
    active_rc_series = snapshot.active_rc_series
    source_manifest = snapshot.source_manifest
    metadata_source_manifest = snapshot.metadata_source_manifest
    is_prerelease = snapshot.is_prerelease
    copy_entries = snapshot.copy_entries
    release_mode = snapshot.release_mode
    selected_entries = snapshot.selected_entries
    new_entries = snapshot.new_entries
    entries_sorted = snapshot.entries_sorted
    release_dir = (
        release_manifest_root(project_root, existing_manifest)
        if existing_manifest is not None
        else release_directory(project_root) / tag_version
    )
    manifest_path = release_dir / "manifest.yaml"
    release_entries_dir = release_dir / "entries"
    notes_path = release_dir / NOTES_FILENAME
    cleanup_unreleased_paths = snapshot.cleanup_unreleased_paths
    cleanup_missing_entry_ids = snapshot.cleanup_missing_entry_ids
    if cleanup_missing_entry_ids:
        log_warning(
            f"{len(cleanup_missing_entry_ids)} promoted entry file(s) were not found in "
            f"unreleased/ and could not be cleaned up: {', '.join(cleanup_missing_entry_ids)}"
        )

    if title is not None and not title_explicit:
        # Treat explicitly provided empty strings as intentional overrides.
        title_explicit = True
    default_release_title, default_manifest_intro = _resolve_default_release_metadata(
        config,
        tag_version,
        existing_manifest=existing_manifest,
        metadata_source_manifest=metadata_source_manifest,
    )
    release_title = title if title_explicit else default_release_title

    if intro_text and intro_file:
        raise click.ClickException("Use only one of --intro or --intro-file, not both.")
    if intro_text is not None:
        manifest_intro: Optional[str] = intro_text.strip() or None
    elif intro_file:
        manifest_intro = intro_file.read_text(encoding="utf-8").strip() or None
    else:
        manifest_intro = default_manifest_intro

    if not entries_sorted and not manifest_intro:
        raise click.ClickException(
            "No changelog entries available. Provide --intro or --intro-file "
            "to create an intro-only release."
        )

    if entries_sorted:
        table = Table()
        table.add_column("✓", no_wrap=True, justify="center", header_style="dim")
        table.add_column("Title")
        table.add_column("Type", no_wrap=True, justify="center")
        table.add_column("ID", style="cyan")
        new_entry_ids = {entry.entry_id for entry in new_entries}
        for entry in entries_sorted:
            status = "new" if entry.entry_id in new_entry_ids else "existing"
            status_cell = STATUS_TABLE_CELLS.get(status, Text("•"))
            if isinstance(status_cell, Text):
                status_cell = status_cell.copy()
            type_value = entry.metadata.get("type", "change")
            type_emoji = ENTRY_TYPE_EMOJIS.get(type_value, "•")
            table.add_row(
                status_cell,
                entry.metadata.get("title", "Untitled"),
                type_emoji,
                entry.entry_id,
            )
        _print_renderable(table)

    release_dt = (
        release_date.date()
        if release_date is not None
        else existing_manifest.created
        if existing_manifest
        else date.today()
    )

    release_notes_standard = _render_release_notes(
        entries_sorted, config, include_emoji=True, explicit_links=explicit_links
    )
    release_notes_compact = _render_release_notes_compact(
        entries_sorted, config, include_emoji=True, explicit_links=explicit_links
    )

    if compact_explicit:
        compact_flag = bool(compact)
        existing_notes_payload = (
            notes_path.read_text(encoding="utf-8") if notes_path.exists() else None
        )
    else:
        prefer_compact = config.export_style == EXPORT_STYLE_COMPACT
        existing_notes_payload = (
            notes_path.read_text(encoding="utf-8") if notes_path.exists() else None
        )
        if existing_notes_payload is not None:
            normalized_existing = existing_notes_payload.rstrip("\n")
            doc_standard = _compose_release_document(
                manifest_intro,
                release_notes_standard,
            ).rstrip("\n")
            doc_compact = _compose_release_document(
                manifest_intro,
                release_notes_compact,
            ).rstrip("\n")
            if normalized_existing == doc_compact:
                prefer_compact = True
            elif normalized_existing == doc_standard:
                prefer_compact = False
        compact_flag = prefer_compact

    previous_release = snapshot.previous_release
    module_plan = snapshot.module_plan
    manifest = ReleaseManifest(
        version=tag_version,
        created=release_dt,
        entries=[entry.entry_id for entry in entries_sorted],
        title=release_title or "",
        intro=manifest_intro or None,
        modules=dict(module_plan.version_map),
        source=_resolve_release_source(
            existing_manifest=existing_manifest,
            mode=release_mode,
            new_entries=new_entries,
            previous_release=previous_release,
        ),
        path=existing_manifest.path if existing_manifest is not None else None,
    )

    release_notes = release_notes_compact if compact_flag else release_notes_standard
    readme_content = _compose_release_document(manifest.intro, release_notes)
    if module_plan.entries_by_module:
        module_sections: list[str] = []
        for module_id in sorted(module_plan.entries_by_module.keys()):
            module_config, module_entries = module_plan.entries_by_module[module_id]
            module_body = _render_module_entries_compact(
                module_entries,
                module_config,
                include_emoji=True,
                explicit_links=explicit_links,
            )
            if module_body:
                version_str = module_plan.version_map.get(module_id, "")
                header = (
                    f"## {module_config.name} {version_str}"
                    if version_str
                    else f"## {module_config.name}"
                )
                module_sections.append(f"{header}\n\n{module_body}")
        if module_sections:
            readme_content = readme_content + "\n\n---\n\n" + "\n\n".join(module_sections)

    manifest_payload = serialize_release_manifest(manifest)
    manifest_exists = manifest_path.exists()
    existing_manifest_payload = (
        manifest_path.read_text(encoding="utf-8") if manifest_exists else None
    )

    def _normalize_block(value: Optional[str]) -> str:
        return (value or "").rstrip("\n")

    rc_cleanup_dirs: list[Path] = []
    if existing_manifest is None:
        rc_cleanup_dirs = release_manifest_dirs(project_root, active_rc_series)

    changes_required = False
    change_reasons: list[str] = []
    if not release_dir.exists():
        changes_required = True
        change_reasons.append("create release directory")
    if new_entries:
        changes_required = True
        change_reasons.append(f"append {len(new_entries)} new entries")
    if cleanup_unreleased_paths:
        changes_required = True
        change_reasons.append(
            f"consume {len(cleanup_unreleased_paths)} promoted unreleased entries"
        )
    if rc_cleanup_dirs:
        changes_required = True
        change_reasons.append(
            f"remove {len(rc_cleanup_dirs)} superseded RC director{'ies' if len(rc_cleanup_dirs) != 1 else 'y'}"
        )
    if _normalize_block(manifest_payload) != _normalize_block(existing_manifest_payload):
        changes_required = True
        change_reasons.append("update manifest metadata")
    if _normalize_block(readme_content) != _normalize_block(existing_notes_payload):
        changes_required = True
        change_reasons.append("refresh release notes")

    version_file_updates = []
    if not is_prerelease and _is_current_or_newer_release(project_root, version):
        version_file_updates = plan_version_file_updates(
            project_root,
            version,
            bump_mode=config.release.version_bump_mode,
            explicit_paths=config.release.version_files,
        )
    if version_file_updates:
        changes_required = True
        count = len(version_file_updates)
        plural = "s" if count != 1 else ""
        change_reasons.append(f"update {count} version file{plural}")

    if not changes_required:
        log_success(f"release '{tag_version}' is already up to date.")
        click.echo(tag_version)
        return

    if not assume_yes:
        log_info(f"changes for release {format_bold(tag_version)}:")
        for reason in change_reasons:
            log_success(reason)
        log_info(f"re-run with {format_bold('--yes')} to apply these updates.")
        raise SystemExit(1)

    release_dir.mkdir(parents=True, exist_ok=True)
    release_entries_dir.mkdir(parents=True, exist_ok=True)

    if version_file_updates:
        apply_version_file_updates(version_file_updates)
        for update in version_file_updates:
            try:
                display_path = update.path.relative_to(project_root)
            except ValueError:
                display_path = update.path
            log_success(f"updated version file: {display_path}")

    entries_to_sync = selected_entries if copy_entries else new_entries
    for entry in entries_to_sync:
        source_path = entry.path
        destination_path = release_entries_dir / source_path.name
        if not source_path.exists():
            action = "copy" if copy_entries else "move"
            raise click.ClickException(
                f"Cannot {action} entry '{entry.entry_id}' because {source_path} is missing."
            )
        if destination_path.exists():
            if not copy_entries:
                continue
            destination_path.unlink()
        if copy_entries:
            shutil.copy2(source_path, destination_path)
        else:
            source_path.rename(destination_path)

    removed_unreleased_count = 0
    for unreleased_path in cleanup_unreleased_paths:
        if not unreleased_path.exists():
            continue
        unreleased_path.unlink()
        removed_unreleased_count += 1

    manifest_path_result = write_release_manifest(
        project_root,
        manifest,
        readme_content,
        overwrite=manifest_exists,
    )
    removed_rc_count = remove_release_directories(rc_cleanup_dirs)

    log_success(f"release manifest written: {manifest_path_result.relative_to(project_root)}")
    relative_release_dir = release_entries_dir.relative_to(project_root)
    if source_manifest is not None:
        log_success(
            f"synchronized {len(entries_to_sync)} promoted entries in: {relative_release_dir}"
        )
    elif new_entries:
        log_success(f"appended {len(new_entries)} entries to: {relative_release_dir}")
    else:
        log_success(f"updated release metadata for {tag_version}.")
    if removed_unreleased_count:
        log_success(f"consumed {removed_unreleased_count} unreleased entries for {tag_version}.")
    if removed_rc_count:
        log_success(
            f"removed {removed_rc_count} superseded release candidate director{'ies' if removed_rc_count != 1 else 'y'}."
        )

    # Output version to stdout for scripting (e.g., VERSION=$(tenzir-ship release create ...))
    click.echo(tag_version)


def publish_release(
    ctx: CLIContext,
    *,
    version: str,
    draft: bool,
    prerelease: bool,
    no_latest: bool,
    create_tag: bool,
    create_commit: bool,
    commit_message: str | None,
    assume_yes: bool,
) -> None:
    """Python wrapper around the ``release publish`` command."""

    config = ctx.ensure_config()
    _enforce_structure_is_valid(ctx, action="publish a release")
    project_root = ctx.project_root

    if not config.repository:
        raise click.ClickException(
            "Set the 'repository' field in config.yaml or package.yaml before publishing releases."
        )

    gh_path = shutil.which("gh")
    if gh_path is None:
        raise click.ClickException("The 'gh' CLI is required but was not found in PATH.")

    manifest = _find_release_manifest(project_root, version)
    if manifest is None:
        raise click.ClickException(f"Release '{version}' not found.")

    release_version = normalize_release_version(manifest.version)
    tag_name = render_release_tag(release_version)
    release_dir = release_manifest_root(project_root, manifest)
    notes_path = release_dir / NOTES_FILENAME
    if not notes_path.exists():
        relative_notes = notes_path.relative_to(project_root)
        raise click.ClickException(
            f"Release notes missing at {relative_notes}. Run 'tenzir-ship release create {manifest.version} --yes' first."
        )

    notes_content = notes_path.read_text(encoding="utf-8").strip()
    if not notes_content:
        raise click.ClickException("Release notes are empty; aborting publish.")

    inferred_prerelease = is_release_candidate(release_version)
    resolved_prerelease = prerelease or inferred_prerelease
    resolved_no_latest = no_latest or inferred_prerelease

    # Determine commit message early for step tracking display
    final_commit_message: str | None = None
    if create_commit:
        if not create_tag:
            raise click.ClickException("--commit requires --tag to be specified.")
        if not has_staged_changes(project_root):
            raise click.ClickException(
                "No staged changes to commit. Stage changes with 'git add' first."
            )
        final_commit_message = commit_message or config.release.commit_message.format(
            version=release_version
        )

    # Initialize step tracker with all planned steps
    tracker = StepTracker()
    if create_commit:
        tracker.add("commit", f'git commit -m "{final_commit_message}"')

    # Get branch info early for accurate step tracking display
    push_remote: str | None = None
    push_remote_ref: str | None = None
    push_branch: str | None = None
    if create_tag:
        try:
            push_remote, push_remote_ref, push_branch = get_push_branch_info(
                project_root, config.repository
            )
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc

        tracker.add("tag", f'git tag -a {tag_name} -m "Release {release_version}"')
        tracker.add("push_branch", f"git push {push_remote} {push_branch}:{push_remote_ref}")
        tracker.add("push_tag", f"git push {push_remote} {tag_name}")
    tracker.add("publish", f"gh release create {tag_name} --repo {config.repository} ...")

    def _fail_step_and_raise(step_name: str, exc: Exception) -> NoReturn:
        """Mark step as failed, render progress, and re-raise the exception."""
        tracker.fail(step_name)
        _render_release_progress(tracker)
        raise click.ClickException(str(exc)) from exc

    # Execute commit step
    if create_commit:
        assert final_commit_message is not None
        try:
            create_git_commit(project_root, final_commit_message)
        except RuntimeError as exc:
            _fail_step_and_raise("commit", exc)
        tracker.complete("commit")
        log_success(f"created commit: {final_commit_message}")

    # Execute tag and push steps
    if create_tag:
        tag_message = f"Release {release_version}"
        try:
            created = create_annotated_git_tag(project_root, tag_name, tag_message)
        except RuntimeError as exc:
            _fail_step_and_raise("tag", exc)
        tracker.complete("tag")
        if created:
            log_success(f"created git tag {tag_name}.")
        else:
            log_warning(f"git tag {tag_name} already exists; skipping creation.")

        try:
            push_current_branch(project_root, config.repository)
        except RuntimeError as exc:
            _fail_step_and_raise("push_branch", exc)
        tracker.complete("push_branch")
        log_success(f"pushed branch {push_branch} to remote {push_remote}/{push_remote_ref}.")

        try:
            remote_name = push_git_tag(project_root, tag_name, config.repository)
        except RuntimeError as exc:
            _fail_step_and_raise("push_tag", exc)
        tracker.complete("push_tag")
        log_success(f"pushed git tag {tag_name} to remote {remote_name}.")

    release_exists = _github_release_exists(config.repository, tag_name, gh_path)
    if release_exists:
        command: list[str] = [
            gh_path,
            "release",
            "edit",
            tag_name,
            "--repo",
            config.repository,
            "--notes-file",
            str(notes_path),
        ]
        if manifest.title:
            command.extend(["--title", manifest.title])
        if resolved_prerelease:
            command.append("--prerelease")
        if resolved_no_latest:
            command.append("--latest=false")
        confirmation_action = "gh release edit"
    else:
        command = [
            gh_path,
            "release",
            "create",
            tag_name,
            "--repo",
            config.repository,
            "--notes-file",
            str(notes_path),
        ]
        if manifest.title:
            command.extend(["--title", manifest.title])
        if draft:
            command.append("--draft")
        if resolved_prerelease:
            command.append("--prerelease")
        if resolved_no_latest:
            command.append("--latest=false")
        confirmation_action = "gh release create"

    tracker.update_command("publish", shlex.join(command))

    if not assume_yes:
        prompt_question = (
            f"Publish release {release_version} with tag {tag_name} "
            f"to GitHub repository {config.repository}?"
        )
        log_info(prompt_question.lower())
        prompt_action = f"This will run {format_bold(confirmation_action)}."
        log_info(prompt_action.lower())
        try:
            confirmed = click.confirm(
                "",
                default=True,
                prompt_suffix="[Y/n]: ",
                show_default=False,
            )
        except (click.exceptions.Abort, KeyboardInterrupt) as exc:
            abort_on_user_interrupt(exc)
        if not confirmed:
            log_info("aborted release publish.")
            return

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        tracker.fail("publish")
        _render_release_progress(tracker)
        raise click.ClickException(
            f"'gh' exited with status {exc.returncode}. See output for details."
        ) from exc
    tracker.complete("publish")

    log_success(f"published {tag_name} to GitHub repository {config.repository}.")


# Click commands - these use @click.command() and are registered in __init__.py


@click.group("release")
@click.pass_obj
def release_group(ctx: CLIContext) -> None:
    """Manage release manifests, notes, and publishing."""
    ctx.ensure_config()


@release_group.command("plan")
@click.argument("version", required=False)
@click.option(
    "--patch",
    "patch",
    is_flag=True,
    help="Plan a patch release from the latest stable version.",
)
@click.option(
    "--minor",
    "minor",
    is_flag=True,
    help="Plan a minor release from the latest stable version.",
)
@click.option(
    "--major",
    "major",
    is_flag=True,
    help="Plan a major release from the latest stable version.",
)
@click.option(
    "--rc",
    "release_candidate",
    is_flag=True,
    help="Plan a release candidate for the resolved stable version.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit the plan as JSON.",
)
@click.pass_obj
def release_plan_cmd(
    ctx: CLIContext,
    version: Optional[str],
    patch: bool,
    minor: bool,
    major: bool,
    release_candidate: bool,
    json_output: bool,
) -> None:
    """Inspect the release snapshot that would be created for the current queue."""

    version_bump = _resolve_manual_bump_flags(patch=patch, minor=minor, major=major)
    payload = build_release_plan_payload(
        ctx,
        version=version,
        version_bump=version_bump,
        release_candidate=release_candidate,
    )
    if json_output:
        emit_output(json.dumps(payload, indent=2))
        return

    project_payload = cast(dict[str, object], payload["project"])
    release_payload = cast(dict[str, object], payload["release"])
    entry_counts = cast(dict[str, int], release_payload["entry_counts"])
    highlights = cast(list[dict[str, object]], payload["highlights"])
    lines = [
        f"Release plan for {release_payload['version']}",
        f"Project: {project_payload['name']}",
        f"Mode: {release_payload['mode']}",
        (
            "Entries: "
            f"{entry_counts['total']} total "
            f"({entry_counts['breaking']} breaking, {entry_counts['feature']} features, "
            f"{entry_counts['bugfix']} bug fixes, {entry_counts['change']} changes)"
        ),
    ]
    if release_payload.get("resolved_intro"):
        lines.append(f"Resolved intro: {release_payload['resolved_intro']}")
    if release_payload.get("active_release_candidate"):
        lines.append(f"Active RC: {release_payload['active_release_candidate']}")
    if highlights:
        lines.append("Highlights:")
        for highlight in highlights:
            lines.append(f"- {highlight['title']}")
    emit_output("\n".join(lines))


@release_group.command("create")
@click.argument("version", required=False)
@click.option("--title", help="Display title for the release.")
@click.option("--intro", "intro_text", help="Short release introduction.")
@click.option(
    "--date",
    "release_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Release date (YYYY-MM-DD). Defaults to today or existing release date.",
)
@click.option(
    "--intro-file",
    type=click.Path(path_type=Path, dir_okay=False),
    help="Markdown file containing introductory notes for the release.",
)
# Options shared with `release notes`
@compact_option()
@explicit_links_option()
@click.option(
    "--yes",
    "assume_yes",
    is_flag=True,
    help="Apply detected changes without prompting.",
)
@click.option(
    "--patch",
    "patch",
    is_flag=True,
    help="Bump the patch segment from the latest stable release.",
)
@click.option(
    "--minor",
    "minor",
    is_flag=True,
    help="Bump the minor segment from the latest stable release.",
)
@click.option(
    "--major",
    "major",
    is_flag=True,
    help="Bump the major segment from the latest stable release.",
)
@click.option(
    "--rc",
    "release_candidate",
    is_flag=True,
    help="Create or continue a release candidate for the resolved stable version.",
)
@click.pass_obj
def release_create_cmd(
    ctx: CLIContext,
    version: Optional[str],
    title: Optional[str],
    intro_text: Optional[str],
    release_date: Optional[datetime],
    intro_file: Optional[Path],
    compact: Optional[bool],
    explicit_links: Optional[bool],
    assume_yes: bool,
    patch: bool,
    minor: bool,
    major: bool,
    release_candidate: bool,
) -> None:
    """Create or update a release manifest from changelog entries and intro text."""

    config = ctx.ensure_config()
    click_ctx = click.get_current_context()
    title_explicit = click_ctx.get_parameter_source("title") != ParameterSource.DEFAULT
    compact_explicit = click_ctx.get_parameter_source("compact") != ParameterSource.DEFAULT
    version_bump = _resolve_manual_bump_flags(patch=patch, minor=minor, major=major)
    # Resolve explicit_links: CLI flag overrides config default
    resolved_explicit_links = config.explicit_links if explicit_links is None else explicit_links
    create_release(
        ctx,
        version=version,
        title=title,
        intro_text=intro_text,
        release_date=release_date,
        intro_file=intro_file,
        compact=compact,
        explicit_links=resolved_explicit_links,
        assume_yes=assume_yes,
        version_bump=version_bump,
        release_candidate=release_candidate,
        title_explicit=title_explicit,
        compact_explicit=compact_explicit,
    )


@release_group.command("version")
@click.option(
    "--bare",
    is_flag=True,
    help="Print version without 'v' prefix.",
)
@click.pass_obj
def release_version_cmd(ctx: CLIContext, bare: bool) -> None:
    """Print the latest stable released version."""

    _warn_on_structure_issues(ctx)
    manifest = _get_latest_release_manifest(ctx.project_root)
    if manifest is None:
        raise click.ClickException(
            "No stable releases found. Create a stable release first with 'release create'."
        )

    if bare:
        emit_output(normalize_release_version(manifest.version))
        return
    emit_output(render_release_tag(manifest.version))


@release_group.command("publish")
@click.argument("version", required=False)
@click.option(
    "--draft/--no-draft",
    default=False,
    help="Create the GitHub release as a draft.",
)
@click.option(
    "--prerelease/--no-prerelease",
    default=False,
    help="Mark the GitHub release as a prerelease.",
)
@click.option(
    "--no-latest",
    is_flag=True,
    help="Prevent GitHub from marking this as the latest release.",
)
@click.option(
    "--tag",
    "create_tag",
    is_flag=True,
    help="Create an annotated git tag before publishing.",
)
@click.option(
    "--commit",
    "create_commit",
    is_flag=True,
    help="Commit staged changes before creating the tag.",
)
@click.option(
    "--commit-message",
    help="Custom commit message (default: from config or 'Release {version}').",
)
@click.option(
    "--yes",
    "assume_yes",
    is_flag=True,
    help="Publish without confirmation prompts.",
)
@click.pass_obj
def release_publish_cmd(
    ctx: CLIContext,
    version: Optional[str],
    draft: bool,
    prerelease: bool,
    no_latest: bool,
    create_tag: bool,
    create_commit: bool,
    commit_message: str | None,
    assume_yes: bool,
) -> None:
    """Publish a release to GitHub using the gh CLI.

    If no version is provided, defaults to the latest release.
    """

    resolved_version = version
    if resolved_version is None:
        manifest = _get_latest_release_manifest(ctx.project_root, stable_only=False)
        if manifest is None:
            raise click.ClickException(
                "No releases found. Create a release first with 'release create'."
            )
        resolved_version = manifest.version

    publish_release(
        ctx,
        version=resolved_version,
        draft=draft,
        prerelease=prerelease,
        no_latest=no_latest,
        create_tag=create_tag,
        create_commit=create_commit,
        commit_message=commit_message,
        assume_yes=assume_yes,
    )

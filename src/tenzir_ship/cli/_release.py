"""Release commands for the changelog CLI."""

from __future__ import annotations

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
    release_manifest_root,
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
from ._manifests import (
    _find_release_manifest,
    _get_previous_stable_manifest,
    _get_release_manifest_before,
)
from ._show import (
    _collect_unused_entries_for_release,
    _gather_module_released_entries,
    _get_latest_release_manifest,
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
    "create_release",
    "publish_release",
    "release_group",
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


class ReleaseMode(Enum):
    """High-level release workflows with distinct invariants."""

    SNAPSHOT_PRERELEASE = "snapshot-prerelease"
    PROMOTE_PRERELEASE = "promote-prerelease"
    SYNC_STABLE_QUEUE = "sync-stable-queue"
    REPLACE_WITH_CURRENT_UNRELEASED = "replace-with-current-unreleased"


@dataclass(frozen=True)
class ReleaseIntent:
    """Normalized release workflow intent derived from CLI/API inputs."""

    mode: ReleaseMode
    version: str
    tag_version: str
    version_source: ReleaseVersionSource
    existing_manifest: ReleaseManifest | None
    source_manifest: ReleaseManifest | None = None

    @property
    def is_prerelease(self) -> bool:
        """Return whether the target release is a prerelease."""
        return self.mode is ReleaseMode.SNAPSHOT_PRERELEASE


@dataclass
class ReleaseEntryPlan:
    """Entry selection and file movement plan for a release workflow."""

    existing_entries: list[Entry]
    selected_entries: list[Entry]
    combined_entries: list[Entry]
    new_entries: list[Entry]
    cleanup_unreleased_entry_ids: set[str]
    copy_entries: bool
    replace_existing_entries: bool


@dataclass
class ModuleReleasePlan:
    """Resolved module snapshot and rendered entry selection for a release."""

    entries_by_module: dict[str, tuple[Config, list[Entry]]]
    version_map: dict[str, str]
    previous_release: ReleaseManifest | None


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


def _next_version_for_bump(project_root: Path, bump: ReleaseBump) -> str:
    latest = _latest_bump_base_semver(project_root)
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


def _infer_next_release_version(project_root: Path, unreleased_entries: list[Entry]) -> str | None:
    bump = _infer_release_bump(unreleased_entries)
    if bump is None:
        return None
    return _next_version_for_bump(project_root, bump)


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
        return _next_version_for_bump(project_root, bump), "manual"

    inferred = _infer_next_release_version(project_root, unreleased_entries)
    if inferred is None:
        raise click.ClickException(
            "Cannot auto-bump release version because no unreleased changelog entries were "
            "found. Provide a version argument or specify one of --patch/--minor/--major."
        )
    return inferred, "auto"


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


def _find_release_candidates_for_base(project_root: Path, version: str) -> list[ReleaseManifest]:
    base_version = stable_release_version(version)
    candidates: list[tuple[Version, ReleaseManifest]] = []
    for manifest in iter_release_manifests(project_root):
        if not is_release_candidate(manifest.version):
            continue
        if stable_release_version(manifest.version) != base_version:
            continue
        try:
            parsed = parse_release_version(manifest.version)
        except InvalidVersion:
            continue
        candidates.append((parsed, manifest))
    candidates.sort(key=lambda item: item[0])
    return [manifest for _, manifest in candidates]


def _find_outstanding_release_candidates(
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


def _resolve_release_intent(
    project_root: Path,
    *,
    version: str,
    version_source: ReleaseVersionSource,
    source_release: Optional[str],
    current_unreleased: bool,
) -> ReleaseIntent:
    """Normalize CLI/API inputs into an explicit release workflow mode."""
    if source_release and current_unreleased:
        raise click.ClickException("Use only one of --from or --current-unreleased.")
    if source_release and version_source != "explicit":
        raise click.ClickException("Provide an explicit stable version when using --from.")

    tag_version = render_release_tag(version)
    is_prerelease = is_release_candidate(version)
    if is_prerelease and source_release:
        raise click.ClickException("--from can only be used when creating a stable release.")
    if is_prerelease and current_unreleased:
        raise click.ClickException(
            "Release candidates already snapshot the current unreleased queue; "
            "--current-unreleased is only for stable releases."
        )

    existing_manifest = _find_release_manifest(project_root, version)
    if version_source in {"manual", "auto"} and existing_manifest is not None:
        follow_up = (
            "Supply a different bump flag or explicit version."
            if version_source == "manual"
            else "Supply an explicit version or a manual bump flag."
        )
        raise click.ClickException(f"Release '{tag_version}' already exists. {follow_up}")

    if is_prerelease:
        return ReleaseIntent(
            mode=ReleaseMode.SNAPSHOT_PRERELEASE,
            version=version,
            tag_version=tag_version,
            version_source=version_source,
            existing_manifest=existing_manifest,
        )

    if source_release is not None:
        normalized_source_release = normalize_release_version(source_release)
        if not is_valid_release_version(normalized_source_release):
            raise click.ClickException(
                "Source release version must use X.Y.Z or X.Y.Z-rc.N (for example v1.2.3-rc.1)."
            )
        source_manifest = _find_release_manifest(project_root, normalized_source_release)
        if source_manifest is None:
            raise click.ClickException(f"Source release '{source_release}' not found.")
        if not is_release_candidate(source_manifest.version):
            raise click.ClickException(
                "--from currently only supports promoting release candidates."
            )
        if not is_stable_release(version):
            raise click.ClickException("--from requires a stable target version like 1.2.3.")
        if stable_release_version(source_manifest.version) != stable_release_version(version):
            raise click.ClickException(
                f"Source release '{render_release_tag(source_manifest.version)}' does not match "
                f"target stable version '{tag_version}'."
            )
        return ReleaseIntent(
            mode=ReleaseMode.PROMOTE_PRERELEASE,
            version=version,
            tag_version=tag_version,
            version_source=version_source,
            existing_manifest=existing_manifest,
            source_manifest=source_manifest,
        )

    outstanding_candidates = _find_outstanding_release_candidates(project_root)
    if outstanding_candidates and existing_manifest is None and not current_unreleased:
        matching_candidates = outstanding_candidates.get(stable_release_version(version))
        if matching_candidates:
            latest_candidate = render_release_tag(matching_candidates[-1].version)
            raise click.ClickException(
                f"Release candidates already exist for '{stable_release_version(version)}'. "
                f"Use --from {latest_candidate} to promote the latest candidate exactly, "
                "or pass --current-unreleased to create the stable release from the current "
                "unreleased queue."
            )
        latest_candidates = ", ".join(
            render_release_tag(candidates[-1].version)
            for _, candidates in sorted(outstanding_candidates.items())
        )
        raise click.ClickException(
            "Outstanding release candidates already exist: "
            f"{latest_candidates}. Promote one with --from <candidate>, or pass "
            f"--current-unreleased to create {tag_version} from the current unreleased "
            "queue."
        )

    return ReleaseIntent(
        mode=(
            ReleaseMode.REPLACE_WITH_CURRENT_UNRELEASED
            if current_unreleased
            else ReleaseMode.SYNC_STABLE_QUEUE
        ),
        version=version,
        tag_version=tag_version,
        version_source=version_source,
        existing_manifest=existing_manifest,
    )


def _build_release_entry_plan(
    project_root: Path,
    config: Config,
    intent: ReleaseIntent,
) -> ReleaseEntryPlan:
    """Resolve the exact parent entry snapshot for the requested workflow."""
    existing_entries: list[Entry] = []
    existing_entry_ids: set[str] = set()
    if intent.existing_manifest is not None:
        existing_entries = _load_manifest_entries(project_root, intent.existing_manifest)
        existing_entry_ids = {entry.entry_id for entry in existing_entries}

    cleanup_unreleased_entry_ids: set[str] = set()
    copy_entries = intent.mode in {
        ReleaseMode.SNAPSHOT_PRERELEASE,
        ReleaseMode.PROMOTE_PRERELEASE,
    }
    replace_existing_entries = intent.mode is ReleaseMode.REPLACE_WITH_CURRENT_UNRELEASED

    if intent.mode is ReleaseMode.SNAPSHOT_PRERELEASE:
        selected_entries = _collect_current_unreleased_entries(project_root, config)
    elif intent.mode is ReleaseMode.PROMOTE_PRERELEASE:
        assert intent.source_manifest is not None
        selected_entries = _load_manifest_entries(project_root, intent.source_manifest)
        source_entry_ids = {entry.entry_id for entry in selected_entries}
        if intent.existing_manifest is not None and existing_entry_ids != source_entry_ids:
            raise click.ClickException(
                f"Release '{intent.tag_version}' already exists with a different entry set. "
                "Delete the existing release directory or use --current-unreleased to "
                "create the stable release from the current unreleased queue instead."
            )
        cleanup_unreleased_entry_ids = source_entry_ids
        replace_existing_entries = intent.existing_manifest is not None
    elif intent.mode is ReleaseMode.REPLACE_WITH_CURRENT_UNRELEASED:
        selected_entries = _collect_current_unreleased_entries(project_root, config)
        cleanup_unreleased_entry_ids = {entry.entry_id for entry in selected_entries}
        replace_existing_entries = intent.existing_manifest is not None
    else:
        include_prereleases = intent.existing_manifest is not None
        selected_entries = _collect_unused_entries_for_release(
            project_root,
            config,
            include_prereleases=include_prereleases,
        )

    new_entries = [entry for entry in selected_entries if entry.entry_id not in existing_entry_ids]
    if replace_existing_entries:
        combined_entries = list(selected_entries)
    else:
        combined_entries_map = {entry.entry_id: entry for entry in existing_entries}
        for entry in new_entries:
            combined_entries_map[entry.entry_id] = entry
        combined_entries = list(combined_entries_map.values())

    combined_entries.sort(key=_release_entry_sort_key)
    return ReleaseEntryPlan(
        existing_entries=existing_entries,
        selected_entries=list(selected_entries),
        combined_entries=combined_entries,
        new_entries=new_entries,
        cleanup_unreleased_entry_ids=cleanup_unreleased_entry_ids,
        copy_entries=copy_entries,
        replace_existing_entries=replace_existing_entries,
    )


def _resolve_release_baseline(
    project_root: Path,
    intent: ReleaseIntent,
) -> ReleaseManifest | None:
    """Resolve the stable baseline that this release snapshot compares against."""
    baseline_holder = intent.source_manifest or intent.existing_manifest
    if baseline_holder is not None:
        recorded = _get_previous_stable_manifest(project_root, baseline_holder)
        if recorded is not None:
            return recorded
    return _get_release_manifest_before(project_root, intent.version, stable_only=True)


def _resolve_release_source(
    intent: ReleaseIntent,
    entry_plan: ReleaseEntryPlan,
    previous_release: ReleaseManifest | None,
) -> ReleaseSource | None:
    """Persist provenance for the release snapshot unless this is metadata-only."""
    if (
        intent.existing_manifest is not None
        and intent.mode is ReleaseMode.SYNC_STABLE_QUEUE
        and not entry_plan.new_entries
        and not entry_plan.replace_existing_entries
    ):
        return intent.existing_manifest.source

    return ReleaseSource(
        mode=intent.mode.value,
        source_release=(
            render_release_tag(intent.source_manifest.version)
            if intent.source_manifest is not None
            else None
        ),
        previous_stable=(
            render_release_tag(previous_release.version) if previous_release is not None else None
        ),
    )


def _build_module_release_plan(
    ctx: CLIContext,
    project_root: Path,
    intent: ReleaseIntent,
    previous_release: ReleaseManifest | None,
) -> ModuleReleasePlan:
    """Resolve module versions and entries for the release snapshot."""
    modules = ctx.get_modules()
    if not modules:
        return ModuleReleasePlan({}, {}, previous_release)

    previous_module_versions = previous_release.modules if previous_release else None

    if intent.source_manifest is not None:
        target_versions = dict(intent.source_manifest.modules)
        if not target_versions:
            return ModuleReleasePlan({}, {}, previous_release)
        entries_by_module, _ = _gather_module_released_entries(
            modules,
            previous_module_versions,
            target_versions,
            include_prereleases=is_release_candidate(intent.source_manifest.version),
        )
        return ModuleReleasePlan(entries_by_module, target_versions, previous_release)

    if (
        intent.existing_manifest is not None
        and intent.mode is not ReleaseMode.REPLACE_WITH_CURRENT_UNRELEASED
    ):
        target_versions = dict(intent.existing_manifest.modules)
        if not target_versions:
            return ModuleReleasePlan({}, {}, previous_release)
        entries_by_module, _ = _gather_module_released_entries(
            modules,
            previous_module_versions,
            target_versions,
            include_prereleases=(
                intent.is_prerelease
                or any(is_release_candidate(version) for version in target_versions.values())
            ),
        )
        return ModuleReleasePlan(entries_by_module, target_versions, previous_release)

    entries_by_module, current_versions = _gather_module_released_entries(
        modules,
        previous_module_versions,
        include_prereleases=intent.is_prerelease,
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
    source_release: Optional[str],
    current_unreleased: bool,
    title_explicit: bool,
    compact_explicit: bool,
) -> None:
    """Python wrapper for release creation that mirrors CLI behavior."""

    config = ctx.ensure_config()
    _enforce_structure_is_valid(ctx, action="create a release")
    project_root = ctx.project_root
    normalized_bump = _coerce_release_bump(version_bump)

    preview_entries = _collect_unused_entries_for_release(
        project_root,
        config,
        include_prereleases=False,
    )
    version, version_source = _resolve_release_version(
        project_root,
        version,
        normalized_bump,
        unreleased_entries=preview_entries,
    )
    intent = _resolve_release_intent(
        project_root,
        version=version,
        version_source=version_source,
        source_release=source_release,
        current_unreleased=current_unreleased,
    )

    existing_manifest = intent.existing_manifest
    source_manifest = intent.source_manifest
    release_dir = (
        release_manifest_root(project_root, existing_manifest)
        if existing_manifest is not None
        else release_directory(project_root) / intent.tag_version
    )
    manifest_path = release_dir / "manifest.yaml"
    notes_path = release_dir / NOTES_FILENAME

    entry_plan = _build_release_entry_plan(project_root, config, intent)
    entries_sorted = entry_plan.combined_entries

    if title is not None and not title_explicit:
        # Treat explicitly provided empty strings as intentional overrides.
        title_explicit = True
    default_release_title = f"{config.name} {intent.tag_version}"
    source_release_title = None
    if source_manifest is not None:
        source_tag = render_release_tag(source_manifest.version)
        if source_manifest.title in {source_tag, f"{config.name} {source_tag}"}:
            source_release_title = default_release_title
        else:
            source_release_title = source_manifest.title
    release_title = (
        title
        if title_explicit
        else source_release_title
        if source_release_title is not None
        else existing_manifest.title
        if existing_manifest
        else default_release_title
    )

    if intro_text and intro_file:
        raise click.ClickException("Use only one of --intro or --intro-file, not both.")
    if intro_text is not None:
        manifest_intro: Optional[str] = intro_text.strip() or None
    elif intro_file:
        manifest_intro = intro_file.read_text(encoding="utf-8").strip() or None
    elif source_manifest is not None:
        manifest_intro = source_manifest.intro.strip() if source_manifest.intro else None
    elif existing_manifest and existing_manifest.intro:
        manifest_intro = existing_manifest.intro.strip() or None
    else:
        manifest_intro = None

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
        new_entry_ids = {entry.entry_id for entry in entry_plan.new_entries}
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

    previous_release = _resolve_release_baseline(project_root, intent)
    module_plan = _build_module_release_plan(ctx, project_root, intent, previous_release)
    manifest = ReleaseManifest(
        version=intent.tag_version,
        created=release_dt,
        entries=[entry.entry_id for entry in entries_sorted],
        title=release_title or "",
        intro=manifest_intro or None,
        modules=dict(module_plan.version_map),
        source=_resolve_release_source(intent, entry_plan, previous_release),
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

    current_unreleased_entries = _collect_current_unreleased_entries(project_root, config)
    unreleased_entries_by_id = {entry.entry_id: entry for entry in current_unreleased_entries}
    missing_cleanup_entry_ids = sorted(
        entry_plan.cleanup_unreleased_entry_ids - set(unreleased_entries_by_id)
    )
    if missing_cleanup_entry_ids:
        log_warning(
            f"{len(missing_cleanup_entry_ids)} promoted entry file(s) were not found in "
            f"unreleased/ and could not be cleaned up: {', '.join(missing_cleanup_entry_ids)}"
        )
    cleanup_unreleased_paths = [
        unreleased_entries_by_id[entry_id].path
        for entry_id in sorted(entry_plan.cleanup_unreleased_entry_ids)
        if entry_id in unreleased_entries_by_id
    ]

    stale_release_entry_paths: list[Path] = []
    if entry_plan.replace_existing_entries:
        existing_entries_by_id = {entry.entry_id: entry for entry in entry_plan.existing_entries}
        combined_entry_ids = {entry.entry_id for entry in entry_plan.combined_entries}
        stale_release_entry_paths = [
            existing_entries_by_id[entry_id].path
            for entry_id in sorted(existing_entries_by_id.keys() - combined_entry_ids)
            if entry_id in existing_entries_by_id
        ]

    entry_snapshot_updates: list[Entry] = []
    if (
        source_manifest is not None or entry_plan.replace_existing_entries
    ) and existing_manifest is not None:
        release_entries_dir = release_dir / "entries"
        for entry in entry_plan.selected_entries:
            destination_path = release_entries_dir / entry.path.name
            if (
                not destination_path.exists()
                or destination_path.read_bytes() != entry.path.read_bytes()
            ):
                entry_snapshot_updates.append(entry)

    changes_required = False
    change_reasons: list[str] = []
    if not release_dir.exists():
        changes_required = True
        change_reasons.append("create release directory")
    if entry_plan.new_entries:
        changes_required = True
        change_reasons.append(f"append {len(entry_plan.new_entries)} new entries")
    if cleanup_unreleased_paths:
        changes_required = True
        change_reasons.append(
            f"consume {len(cleanup_unreleased_paths)} promoted unreleased entries"
        )
    if stale_release_entry_paths:
        changes_required = True
        change_reasons.append(
            f"remove {len(stale_release_entry_paths)} stale released entry snapshot(s)"
        )
    if entry_snapshot_updates:
        changes_required = True
        change_reasons.append(f"refresh {len(entry_snapshot_updates)} release entry snapshot(s)")
    if _normalize_block(manifest_payload) != _normalize_block(existing_manifest_payload):
        changes_required = True
        change_reasons.append("update manifest metadata")
    if _normalize_block(readme_content) != _normalize_block(existing_notes_payload):
        changes_required = True
        change_reasons.append("refresh release notes")

    version_file_updates = []
    if not intent.is_prerelease and _is_current_or_newer_release(project_root, version):
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
        log_success(f"release '{intent.tag_version}' is already up to date.")
        click.echo(intent.tag_version)
        return

    if not assume_yes:
        log_info(f"changes for release {format_bold(intent.tag_version)}:")
        for reason in change_reasons:
            log_success(reason)
        log_info(f"re-run with {format_bold('--yes')} to apply these updates.")
        raise SystemExit(1)

    release_dir.mkdir(parents=True, exist_ok=True)
    release_entries_dir = release_dir / "entries"
    release_entries_dir.mkdir(parents=True, exist_ok=True)

    if version_file_updates:
        apply_version_file_updates(version_file_updates)
        for update in version_file_updates:
            try:
                display_path = update.path.relative_to(project_root)
            except ValueError:
                display_path = update.path
            log_success(f"updated version file: {display_path}")

    for stale_entry_path in stale_release_entry_paths:
        if stale_entry_path.exists():
            stale_entry_path.unlink()

    entries_to_sync = (
        entry_plan.selected_entries
        if source_manifest is not None or entry_plan.replace_existing_entries
        else entry_plan.new_entries
    )
    for entry in entries_to_sync:
        source_path = entry.path
        destination_path = release_entries_dir / source_path.name
        if not source_path.exists():
            action = "copy" if entry_plan.copy_entries else "move"
            raise click.ClickException(
                f"Cannot {action} entry '{entry.entry_id}' because {source_path} is missing."
            )
        if destination_path.exists():
            if source_manifest is None and not entry_plan.replace_existing_entries:
                continue
            destination_path.unlink()
        if entry_plan.copy_entries:
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

    log_success(f"release manifest written: {manifest_path_result.relative_to(project_root)}")
    relative_release_dir = release_entries_dir.relative_to(project_root)
    if source_manifest is not None:
        log_success(
            f"synchronized {len(entries_to_sync)} promoted entries in: {relative_release_dir}"
        )
    elif entry_plan.new_entries:
        log_success(f"appended {len(entry_plan.new_entries)} entries to: {relative_release_dir}")
    else:
        log_success(f"updated release metadata for {intent.tag_version}.")
    if removed_unreleased_count:
        log_success(
            f"consumed {removed_unreleased_count} unreleased entries for {intent.tag_version}."
        )

    # Output version to stdout for scripting (e.g., VERSION=$(tenzir-ship release create ...))
    click.echo(intent.tag_version)


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
    "--from",
    "source_release",
    help="Promote the specified release candidate into the target stable release.",
)
@click.option(
    "--current-unreleased",
    is_flag=True,
    help="Create the stable release from the current unreleased queue even if RCs exist.",
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
    source_release: Optional[str],
    current_unreleased: bool,
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
        source_release=source_release,
        current_unreleased=current_unreleased,
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

    If no version is provided, defaults to the latest stable release.
    """

    resolved_version = version
    if resolved_version is None:
        manifest = _get_latest_release_manifest(ctx.project_root)
        if manifest is None:
            raise click.ClickException(
                "No stable releases found. Create a stable release first with 'release create'."
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

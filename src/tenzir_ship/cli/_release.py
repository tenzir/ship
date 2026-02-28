"""Release commands for the changelog CLI."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import NoReturn, Optional

import click
from click.core import ParameterSource
from packaging.version import InvalidVersion, Version
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..config import EXPORT_STYLE_COMPACT
from ..entries import Entry
from ..releases import (
    ReleaseManifest,
    NOTES_FILENAME,
    iter_release_manifests,
    load_release_entry,
    release_directory,
    serialize_release_manifest,
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


def _find_release_manifest(project_root: Path, version: str) -> Optional[ReleaseManifest]:
    normalized_version = version.strip()
    for manifest in iter_release_manifests(project_root):
        if manifest.version == normalized_version:
            return manifest
    return None


def _github_release_exists(repository: str, version: str, gh_path: str) -> bool:
    command = [gh_path, "release", "view", version, "--repo", repository]
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


def _latest_semver(project_root: Path) -> tuple[Version, str] | None:
    versions: list[tuple[Version, str]] = []
    for manifest in iter_release_manifests(project_root):
        label = manifest.version
        prefix = ""
        value = label
        if label.startswith(("v", "V")):
            prefix = label[0]
            value = label[1:]
        try:
            parsed = Version(value)
        except InvalidVersion:
            continue
        versions.append((parsed, prefix))
    if not versions:
        return None
    versions.sort(key=lambda item: item[0])
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


def _validate_semver_label(version: str) -> None:
    value = version
    if value.startswith(("v", "V")):
        value = value[1:]
    try:
        Version(value)
    except InvalidVersion as exc:
        raise click.ClickException(
            "Release version must be a valid semantic version (e.g. 1.2.3 or v1.2.3)."
        ) from exc


def _resolve_release_version(
    project_root: Path,
    explicit: Optional[str],
    bump: Optional[str],
) -> str:
    if explicit and bump:
        raise click.ClickException("Provide either a version argument or a bump flag, not both.")
    if explicit:
        value = explicit.strip()
        if not value:
            raise click.ClickException("Release version cannot be empty.")
        _validate_semver_label(value)
        return value
    if not bump:
        raise click.ClickException(
            "Provide a version argument or specify one of --patch/--minor/--major."
        )
    latest = _latest_semver(project_root)
    if latest is None:
        base_version = Version("0.0.0")
        prefix = ""
    else:
        base_version, prefix = latest
    next_version = _bump_version_value(base_version, bump)
    return f"{prefix}{next_version}"


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
    title_explicit: bool,
    compact_explicit: bool,
) -> None:
    """Python wrapper for release creation that mirrors CLI behavior."""

    config = ctx.ensure_config()
    _enforce_structure_is_valid(ctx, action="create a release")
    project_root = ctx.project_root

    version = _resolve_release_version(project_root, version, version_bump)

    existing_manifest = _find_release_manifest(project_root, version)
    if version_bump and existing_manifest is not None:
        raise click.ClickException(
            f"Release '{version}' already exists. Supply a different bump flag or explicit version."
        )
    release_dir = release_directory(project_root) / version
    manifest_path = release_dir / "manifest.yaml"
    notes_path = release_dir / NOTES_FILENAME

    existing_entries: list[Entry] = []
    existing_entry_ids: set[str] = set()
    if existing_manifest:
        for entry_id in existing_manifest.entries:
            entry = load_release_entry(project_root, existing_manifest, entry_id)
            if entry is None:
                raise click.ClickException(
                    f"Release '{version}' is missing entry file for '{entry_id}'. "
                    "Recreate or repair the release before appending new entries."
                )
            existing_entries.append(entry)
            existing_entry_ids.add(entry.entry_id)

    unused_entries = _collect_unused_entries_for_release(project_root, config)

    new_entries = [entry for entry in unused_entries if entry.entry_id not in existing_entry_ids]

    combined_entries: dict[str, Entry] = {entry.entry_id: entry for entry in existing_entries}
    for entry in new_entries:
        combined_entries[entry.entry_id] = entry

    entries_sorted = sorted(combined_entries.values(), key=_release_entry_sort_key)

    if title is not None and not title_explicit:
        # Treat explicitly provided empty strings as intentional overrides.
        title_explicit = True
    release_title = (
        title
        if title_explicit
        else existing_manifest.title
        if existing_manifest
        else f"{config.name} {version}"
    )
    # Validate mutually exclusive intro sources and resolve intro.
    if intro_text and intro_file:
        raise click.ClickException("Use only one of --intro or --intro-file, not both.")
    if intro_text is not None:
        manifest_intro: Optional[str] = intro_text.strip() or None
    elif intro_file:
        manifest_intro = intro_file.read_text(encoding="utf-8").strip() or None
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

    release_notes = release_notes_compact if compact_flag else release_notes_standard

    manifest = ReleaseManifest(
        version=version,
        created=release_dt,
        entries=[entry.entry_id for entry in entries_sorted],
        title=release_title or "",
        intro=manifest_intro or None,
    )

    readme_content = _compose_release_document(manifest.intro, release_notes)

    # Append module summaries to static release notes
    modules = ctx.get_modules()
    if modules:
        # Get previous release to determine which module entries are new
        previous_release = _get_latest_release_manifest(project_root)
        previous_module_versions = previous_release.modules if previous_release else None

        module_entries, current_module_versions = _gather_module_released_entries(
            modules, previous_module_versions
        )

        # Record current module versions in manifest
        if current_module_versions:
            manifest.modules = current_module_versions

        if module_entries:
            module_sections: list[str] = []
            for module_id in sorted(module_entries.keys()):
                module_config, entries = module_entries[module_id]
                module_body = _render_module_entries_compact(
                    entries,
                    module_config,
                    include_emoji=True,
                    explicit_links=explicit_links,
                )
                if module_body:
                    version_str = current_module_versions.get(module_id, "")
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

    changes_required = False
    change_reasons: list[str] = []
    if not release_dir.exists():
        changes_required = True
        change_reasons.append("create release directory")
    if new_entries:
        changes_required = True
        change_reasons.append(f"append {len(new_entries)} new entries")
    if _normalize_block(manifest_payload) != _normalize_block(existing_manifest_payload):
        changes_required = True
        change_reasons.append("update manifest metadata")
    if _normalize_block(readme_content) != _normalize_block(existing_notes_payload):
        changes_required = True
        change_reasons.append("refresh release notes")

    if not changes_required:
        log_success(f"release '{version}' is already up to date.")
        return

    if not assume_yes:
        log_info(f"changes for release {format_bold(version)}:")
        for reason in change_reasons:
            log_success(reason)
        log_info(f"re-run with {format_bold('--yes')} to apply these updates.")
        raise SystemExit(1)

    release_dir.mkdir(parents=True, exist_ok=True)
    release_entries_dir = release_dir / "entries"
    release_entries_dir.mkdir(parents=True, exist_ok=True)

    for entry in new_entries:
        source_path = entry.path
        destination_path = release_entries_dir / source_path.name
        if not source_path.exists():
            raise click.ClickException(
                f"Cannot move entry '{entry.entry_id}' because {source_path} is missing."
            )
        if destination_path.exists():
            continue
        source_path.rename(destination_path)

    manifest_path_result = write_release_manifest(
        project_root,
        manifest,
        readme_content,
        overwrite=manifest_exists,
    )

    log_success(f"release manifest written: {manifest_path_result.relative_to(project_root)}")
    if new_entries:
        relative_release_dir = release_entries_dir.relative_to(project_root)
        log_success(f"appended {len(new_entries)} entries to: {relative_release_dir}")
    else:
        log_success(f"updated release metadata for {version}.")

    # Output version to stdout for scripting (e.g., VERSION=$(tenzir-ship release create ...))
    click.echo(version)


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

    release_dir = release_directory(project_root) / manifest.version
    notes_path = release_dir / NOTES_FILENAME
    if not notes_path.exists():
        relative_notes = notes_path.relative_to(project_root)
        raise click.ClickException(
            f"Release notes missing at {relative_notes}. Run 'tenzir-ship release create {manifest.version} --yes' first."
        )

    notes_content = notes_path.read_text(encoding="utf-8").strip()
    if not notes_content:
        raise click.ClickException("Release notes are empty; aborting publish.")

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
            version=manifest.version
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

        tracker.add("tag", f'git tag -a {manifest.version} -m "Release {manifest.version}"')
        tracker.add("push_branch", f"git push {push_remote} {push_branch}:{push_remote_ref}")
        tracker.add("push_tag", f"git push {push_remote} {manifest.version}")
    tracker.add("publish", f"gh release create {manifest.version} --repo {config.repository} ...")

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
        tag_message = f"Release {manifest.version}"
        try:
            created = create_annotated_git_tag(project_root, manifest.version, tag_message)
        except RuntimeError as exc:
            _fail_step_and_raise("tag", exc)
        tracker.complete("tag")
        if created:
            log_success(f"created git tag {manifest.version}.")
        else:
            log_warning(f"git tag {manifest.version} already exists; skipping creation.")

        try:
            push_current_branch(project_root, config.repository)
        except RuntimeError as exc:
            _fail_step_and_raise("push_branch", exc)
        tracker.complete("push_branch")
        log_success(f"pushed branch {push_branch} to remote {push_remote}/{push_remote_ref}.")

        try:
            remote_name = push_git_tag(project_root, manifest.version, config.repository)
        except RuntimeError as exc:
            _fail_step_and_raise("push_tag", exc)
        tracker.complete("push_tag")
        log_success(f"pushed git tag {manifest.version} to remote {remote_name}.")

    release_exists = _github_release_exists(config.repository, manifest.version, gh_path)
    if release_exists:
        command: list[str] = [
            gh_path,
            "release",
            "edit",
            manifest.version,
            "--repo",
            config.repository,
            "--notes-file",
            str(notes_path),
        ]
        if manifest.title:
            command.extend(["--title", manifest.title])
        confirmation_action = "gh release edit"
    else:
        command = [
            gh_path,
            "release",
            "create",
            manifest.version,
            "--repo",
            config.repository,
            "--notes-file",
            str(notes_path),
        ]
        if manifest.title:
            command.extend(["--title", manifest.title])
        if draft:
            command.append("--draft")
        if prerelease:
            command.append("--prerelease")
        if no_latest:
            command.append("--latest=false")
        confirmation_action = "gh release create"

    tracker.update_command("publish", shlex.join(command))

    if not assume_yes:
        prompt_question = f"Publish {manifest.version} to GitHub repository {config.repository}?"
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

    log_success(f"published {manifest.version} to GitHub repository {config.repository}.")


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
    "version_bump",
    flag_value="patch",
    default=None,
    help="Bump the patch segment from the latest release.",
)
@click.option(
    "--minor",
    "version_bump",
    flag_value="minor",
    help="Bump the minor segment from the latest release.",
)
@click.option(
    "--major",
    "version_bump",
    flag_value="major",
    help="Bump the major segment from the latest release.",
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
    version_bump: Optional[str],
) -> None:
    """Create or update a release manifest from changelog entries and intro text."""

    config = ctx.ensure_config()
    click_ctx = click.get_current_context()
    title_explicit = click_ctx.get_parameter_source("title") != ParameterSource.DEFAULT
    compact_explicit = click_ctx.get_parameter_source("compact") != ParameterSource.DEFAULT
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
    """Print the latest released version."""

    _warn_on_structure_issues(ctx)
    manifest = _get_latest_release_manifest(ctx.project_root)
    if manifest is None:
        raise click.ClickException(
            "No releases found. Create a release first with 'release create'."
        )

    version = manifest.version
    if bare:
        version = version.lstrip("vV")

    emit_output(version)


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
        manifest = _get_latest_release_manifest(ctx.project_root)
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

"""Show command and related functions for displaying changelog entries."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import (
    Iterable,
    Literal,
    Optional,
    Sequence,
    cast,
)

import click
from rich.console import RenderableType, Group
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.rule import Rule

from ..config import Config, EXPORT_STYLE_COMPACT
from ..entries import (
    Entry,
    MultiProjectEntry,
    iter_entries,
    iter_multi_project_entries,
    sort_entries_desc,
)
from ..modules import Module
from ..releases import (
    ReleaseManifest,
    build_entry_release_index,
    collect_release_entries,
    iter_release_manifests,
    load_release_entry,
    unused_entries,
    used_entry_ids,
)
from ..utils import (
    console,
    emit_output,
)
from ._core import (
    CLIContext,
    _command_help_text,
    _filter_entries_by_project,
    _normalize_component_filters,
    _filter_entries_by_component,
)
from ._rendering import (
    IdentifierResolution,
    _print_renderable,
    _render_project_header,
    _render_entries,
    _render_release,
    _render_single_entry,
    _render_entries_multi_project,
    _render_release_notes,
    _render_release_notes_compact,
    _render_module_entries_compact,
    _compose_release_document,
    _build_entry_title,
    _build_entry_metadata_line,
    _build_entry_body,
    _sort_entries_for_display,
    _build_release_sort_order,
    _release_entry_sort_key,
)
from ._export import (
    _entry_to_dict,
    _build_release_payload,
    _render_markdown_release_block,
    _export_markdown_release,
    _export_markdown_compact,
    _export_json_payload,
)
from ._manifests import (
    _get_release_manifest_before,
    _get_latest_release_manifest,
    _gather_module_released_entries,
)

__all__ = [
    "ShowView",
    "show_entries",
    "run_show_entries",
]

# Type aliases
IdentifierKind = Literal["row", "entry", "release", "unreleased"]
ShowView = Literal["table", "card", "markdown", "json"]


def _collect_unused_entries_for_release(project_root: Path, config: Config) -> list[Entry]:
    """Collect unreleased entries that haven't been included in any release."""
    all_entries = list(iter_entries(project_root))
    used = used_entry_ids(project_root)
    unused = unused_entries(all_entries, used)
    filtered = [entry for entry in unused if entry.project is None or entry.project == config.id]
    return filtered


def _component_matches(entry: Entry, normalized_components: set[str]) -> bool:
    """Return True if entry matches the component filters."""
    if not normalized_components:
        return True
    entry_components = entry.components
    return bool(
        entry_components and any(c.lower() in normalized_components for c in entry_components)
    )


def _render_release_header(
    manifest: ReleaseManifest | None,
    *,
    project_id: str,
) -> None:
    """Render a release header with title and intro."""
    if manifest:
        version = manifest.version
        title = manifest.title or manifest.version
        created = manifest.created.isoformat()
        intro = manifest.intro
    else:
        version = "unreleased"
        title = "Unreleased Changes"
        created = date.today().isoformat()
        intro = None

    _print_renderable(Rule(f"Release {version}"))
    header = Text.assemble(
        ("Title: ", "bold"),
        title or "—",
        ("\nCreated: ", "bold"),
        created,
        ("\nProject: ", "bold"),
        project_id or "—",
    )
    _print_renderable(header)

    if intro:
        _print_renderable(
            Panel(
                intro,
                title="Introduction",
                subtitle="Markdown",
                expand=False,
            )
        )


def _load_release_entries_for_display(
    project_root: Path,
    release_version: str,
    entry_map: dict[str, Entry],
) -> tuple[ReleaseManifest, list[Entry]]:
    """Load entries for a specific release version."""
    normalized_version = release_version.strip()
    manifests = [
        manifest
        for manifest in iter_release_manifests(project_root)
        if manifest.version == normalized_version
    ]
    if not manifests:
        raise click.ClickException(f"Release '{release_version}' not found.")
    manifest = manifests[0]
    missing_entries: list[str] = []
    release_entries: list[Entry] = []
    for entry_id in manifest.entries:
        entry = entry_map.get(entry_id)
        if entry is None:
            entry = load_release_entry(project_root, manifest, entry_id)
        if entry is None:
            missing_entries.append(entry_id)
            continue
        entry_map[entry_id] = entry
        release_entries.append(entry)
    if missing_entries:
        missing_list = ", ".join(sorted(missing_entries))
        raise click.ClickException(
            f"Release '{manifest.version}' is missing entry files for: {missing_list}"
        )
    return manifest, release_entries


def _resolve_identifier(
    identifier: str,
    *,
    project_root: Path,
    config: Config,
    sorted_entries: list[Entry],
    entry_map: dict[str, Entry],
    allowed_kinds: Optional[Iterable[IdentifierKind]] = None,
) -> IdentifierResolution:
    """Resolve a single identifier to its matching entries."""
    allowed = (
        set(allowed_kinds)
        if allowed_kinds is not None
        else {"row", "entry", "release", "unreleased"}
    )
    token = identifier.strip()
    if not token:
        raise click.ClickException("Identifier cannot be empty.")

    lowered = token.lower()
    # "unreleased" and "-" are no longer valid identifiers - use --unreleased flag instead
    if lowered == "unreleased" or token == "-":
        raise click.ClickException(
            f"'{token}' is not a valid identifier. Use --unreleased flag instead."
        )

    try:
        row_num = int(token)
    except ValueError:
        row_num = None

    if row_num is not None:
        if "row" not in allowed:
            raise click.ClickException("Row numbers are not supported by this command.")
        if 1 <= row_num <= len(sorted_entries):
            index = len(sorted_entries) - row_num
            return IdentifierResolution(
                kind="row",
                entries=[sorted_entries[index]],
                identifier=token,
            )
        raise click.ClickException(
            f"Row number {row_num} is out of range. Valid range: 1-{len(sorted_entries)}"
        )

    if token.startswith(("v", "V")):
        if "release" not in allowed:
            raise click.ClickException(
                f"Release identifiers such as '{token}' are not supported by this command."
            )
        manifest, release_entries = _load_release_entries_for_display(
            project_root, token, entry_map
        )
        return IdentifierResolution(
            kind="release",
            entries=release_entries,
            identifier=manifest.version,
            manifest=manifest,
        )

    exact_match = entry_map.get(token)
    if exact_match:
        return IdentifierResolution(kind="entry", entries=[exact_match], identifier=token)

    matches = [(entry_id, entry) for entry_id, entry in entry_map.items() if token in entry_id]
    if not matches:
        raise click.ClickException(
            f"No entry found matching '{token}'. Use 'tenzir-ship show' to see all entries."
        )
    if len(matches) > 1:
        match_ids = [entry_id for entry_id, _ in matches]
        raise click.ClickException(
            f"Multiple entries match '{token}':\n  "
            + "\n  ".join(match_ids)
            + "\n\nPlease be more specific or use a row number."
        )

    entry_id, entry = matches[0]
    return IdentifierResolution(kind="entry", entries=[entry], identifier=entry_id)


def _resolve_identifiers_sequence(
    identifiers: Iterable[str],
    *,
    project_root: Path,
    config: Config,
    sorted_entries: list[Entry],
    entry_map: dict[str, Entry],
    allowed_kinds: Optional[Iterable[IdentifierKind]] = None,
) -> list[IdentifierResolution]:
    """Resolve a list of identifiers into their matching entries."""
    return [
        _resolve_identifier(
            identifier,
            project_root=project_root,
            config=config,
            sorted_entries=sorted_entries,
            entry_map=entry_map,
            allowed_kinds=allowed_kinds,
        )
        for identifier in identifiers
    ]


def _gather_entry_context(
    project_root: Path,
    modules: list[Module] | None = None,
) -> tuple[dict[str, Entry], dict[str, list[str]], dict[str, int], list[Entry]]:
    """Gather all entries and build release index for display."""
    entries = list(iter_entries(project_root))
    entry_map = {entry.entry_id: entry for entry in entries}
    released_entries = collect_release_entries(project_root)
    for entry_id, entry in released_entries.items():
        entry_map.setdefault(entry_id, entry)
    release_index_all = build_entry_release_index(project_root, project=None)
    release_order = _build_release_sort_order(project_root)

    if modules:
        for module in modules:
            module_entries = list(iter_entries(module.root))
            for entry in module_entries:
                entry_map.setdefault(entry.entry_id, entry)
            module_released = collect_release_entries(module.root)
            for entry_id, entry in module_released.items():
                entry_map.setdefault(entry_id, entry)
            module_release_index = build_entry_release_index(module.root, project=None)
            for entry_id, versions in module_release_index.items():
                if entry_id in release_index_all:
                    release_index_all[entry_id].extend(versions)
                else:
                    release_index_all[entry_id] = versions
            module_release_order = _build_release_sort_order(module.root)
            for version, order in module_release_order.items():
                release_order.setdefault(version, order)

    sorted_entries = _sort_entries_for_display(entry_map.values(), release_index_all, release_order)
    return entry_map, release_index_all, release_order, sorted_entries


def _render_release_card(
    manifest: ReleaseManifest | None,
    entries: list[Entry],
    config: Config,
    release_index: dict[str, list[str]],
    *,
    include_emoji: bool,
    compact: bool = True,
) -> None:
    """Render a release as a card with header and entries."""
    if manifest:
        title = manifest.title or manifest.version
        version = manifest.version
        created = manifest.created.isoformat()
        intro = manifest.intro
    else:
        title = "Unreleased Changes"
        version = "unreleased"
        created = date.today().isoformat()
        intro = None

    renderables: list[RenderableType] = []

    header_lines = [
        f"[bold]Version:[/bold] {version}",
        f"[bold]Created:[/bold] {created}",
        f"[bold]Project:[/bold] {config.id}",
        f"[bold]Entries:[/bold] {len(entries)}",
    ]
    renderables.append(Text.from_markup("\n".join(header_lines)))

    if intro:
        renderables.append(Text())
        if compact:
            intro_preview = intro[:200] + "..." if len(intro) > 200 else intro
            renderables.append(Text(intro_preview))
        else:
            renderables.append(Markdown(intro, code_theme="ansi_light"))

    if entries:
        display_entries = entries[:10] if compact else entries
        for entry in display_entries:
            renderables.append(Text())
            entry_title = _build_entry_title(entry, include_emoji=include_emoji)
            renderables.append(entry_title)

            meta_line = _build_entry_metadata_line(entry)
            if meta_line.plain:
                renderables.append(meta_line)

            if not compact:
                renderables.append(Text())
                renderables.append(_build_entry_body(entry))

        if compact and len(entries) > 10:
            renderables.append(Text())
            renderables.append(Text(f"... and {len(entries) - 10} more", style="dim"))

    panel = Panel(
        Group(*renderables),
        title=title,
        border_style="cyan",
        expand=False,
    )
    _print_renderable(panel)


def _show_entries_table_all(
    ctx: CLIContext,
    *,
    release_mode: bool,
    select_released: bool,
    select_unreleased: bool,
    components: set[str],
    include_emoji: bool,
    banner: bool,
) -> None:
    """Handle --all/--released/--unreleased flags in table view."""
    config = ctx.ensure_config()
    project_root = ctx.project_root
    release_index = build_entry_release_index(project_root, project=config.id)

    manifests = list(iter_release_manifests(project_root))
    manifests.sort(key=lambda m: m.created, reverse=True)

    # Determine what to include based on flags
    # --all: both released and unreleased (select_released=False, select_unreleased=False)
    # --released: only released entries
    # --unreleased: only unreleased entries
    include_unreleased = not select_released  # Include unless --released is set
    include_released = not select_unreleased  # Include unless --unreleased is set

    unreleased_entries: list[Entry] = []
    if include_unreleased:
        unreleased = list(iter_entries(project_root))
        unreleased_entries = _filter_entries_by_component(unreleased, components)
        unreleased_entries = sort_entries_desc(unreleased_entries)

    if release_mode:
        if banner:
            _render_project_header(config)

        rendered = False

        if unreleased_entries:
            _render_release_header(None, project_id=config.id)
            _print_renderable(Text())
            _render_entries(
                unreleased_entries,
                release_index,
                config,
                show_banner=False,
                release_order=None,
                include_emoji=include_emoji,
            )
            rendered = True

        if include_released:
            for manifest in manifests:
                release_entries: list[Entry] = []
                for entry_id in manifest.entries:
                    entry = load_release_entry(project_root, manifest, entry_id)
                    if entry is not None:
                        release_entries.append(entry)
                filtered = _filter_entries_by_component(release_entries, components)
                filtered = sort_entries_desc(filtered)

                if rendered:
                    _print_renderable(Text())
                _render_release_header(manifest, project_id=config.id)
                _print_renderable(Text())
                if filtered:
                    _render_entries(
                        filtered,
                        release_index,
                        config,
                        show_banner=False,
                        release_order=None,
                        include_emoji=include_emoji,
                    )
                else:
                    _print_renderable(Text("No entries in this release.", style="dim"))
                rendered = True

        if not rendered:
            raise click.ClickException("No entries found.")
    else:
        all_entries: list[Entry] = list(unreleased_entries)

        if include_released:
            for manifest in manifests:
                for entry_id in manifest.entries:
                    entry = load_release_entry(project_root, manifest, entry_id)
                    if entry is not None:
                        all_entries.append(entry)

        all_entries = _filter_entries_by_component(all_entries, components)
        all_entries = sort_entries_desc(all_entries)

        if not all_entries:
            raise click.ClickException("No entries found.")

        _render_entries(
            all_entries,
            release_index,
            config,
            show_banner=banner,
            release_order=None,
            include_emoji=include_emoji,
        )


def _show_entries_table_release_mode(
    ctx: CLIContext,
    identifiers: tuple[str, ...],
    *,
    components: set[str],
    include_emoji: bool,
    entry_map: dict[str, Entry],
    sorted_entries: list[Entry],
) -> None:
    """Handle --release flag with identifiers: group entries by release with headers."""
    config = ctx.ensure_config()
    project_root = ctx.project_root
    release_index = build_entry_release_index(project_root, project=config.id)

    resolutions = _resolve_identifiers_sequence(
        identifiers,
        project_root=project_root,
        config=config,
        sorted_entries=sorted_entries,
        entry_map=entry_map,
    )

    release_groups: list[tuple[ReleaseManifest | None, list[Entry]]] = []
    for resolution in resolutions:
        filtered = _filter_entries_by_component(resolution.entries, components)
        filtered = sort_entries_desc(filtered)
        if resolution.kind == "release" and resolution.manifest:
            release_groups.append((resolution.manifest, filtered))
        else:
            for entry in filtered:
                versions = release_index.get(entry.entry_id, [])
                if versions:
                    for release_manifest in iter_release_manifests(project_root):
                        if release_manifest.version == versions[0]:
                            found = False
                            for i, (m, entries) in enumerate(release_groups):
                                if m and m.version == release_manifest.version:
                                    if entry not in entries:
                                        release_groups[i] = (m, entries + [entry])
                                    found = True
                                    break
                            if not found:
                                release_groups.append((release_manifest, [entry]))
                            break
                else:
                    found = False
                    for i, (m, entries) in enumerate(release_groups):
                        if m is None:
                            if entry not in entries:
                                release_groups[i] = (None, entries + [entry])
                            found = True
                            break
                    if not found:
                        release_groups.append((None, [entry]))

    if not release_groups:
        raise click.ClickException("No entries found for the given identifiers.")

    rendered = False
    for manifest, entries in release_groups:
        if rendered:
            _print_renderable(Text())
        _render_release_header(manifest, project_id=config.id)
        _print_renderable(Text())
        if entries:
            _render_entries(
                entries,
                release_index,
                config,
                show_banner=False,
                release_order=None,
                include_emoji=include_emoji,
            )
        else:
            _print_renderable(Text("No entries match the filters.", style="dim"))
        rendered = True


def _show_entries_table(
    ctx: CLIContext,
    identifiers: tuple[str, ...],
    project_filter: tuple[str, ...],
    component_filter: tuple[str, ...],
    banner: bool,
    *,
    include_emoji: bool,
    release_mode: bool = False,
    select_all: bool = False,
    select_released: bool = False,
    select_unreleased: bool = False,
) -> None:
    """Display entries in table format."""
    modules = ctx.get_modules()

    if modules:
        config = ctx.ensure_config()
        combined_projects: list[tuple[Path, Config]] = [(ctx.project_root, config)]
        combined_projects.extend((m.root, m.config) for m in modules)

        project_filters = {value.strip() for value in project_filter if value.strip()}
        available_projects = {cfg.id for _, cfg in combined_projects}
        unknown_filters = sorted(project_filters - available_projects)
        if unknown_filters:
            available_display = ", ".join(sorted(available_projects))
            raise click.ClickException(
                f"Unknown project filter(s): {', '.join(unknown_filters)}. "
                f"Available projects: {available_display or 'none'}."
            )

        normalized_components = {
            value.strip().lower() for value in component_filter if value and value.strip()
        }

        def filtered_with_modules(
            entries: Iterable[MultiProjectEntry],
        ) -> list[MultiProjectEntry]:
            return [
                multi_entry
                for multi_entry in entries
                if (
                    (not project_filters or multi_entry.project_id in project_filters)
                    and _component_matches(multi_entry.entry, normalized_components)
                )
            ]

        multi_entries = filtered_with_modules(iter_multi_project_entries(combined_projects))
        _render_entries_multi_project(multi_entries, combined_projects, include_emoji=include_emoji)
        return

    config = ctx.ensure_config()
    project_root = ctx.project_root
    projects = set(project_filter)
    components = _normalize_component_filters(component_filter, config)

    entries = list(iter_entries(project_root))
    entry_map = {entry.entry_id: entry for entry in entries}
    released_entries = collect_release_entries(project_root)
    for entry_id, entry in released_entries.items():
        if entry_id not in entry_map:
            entry_map[entry_id] = entry

    release_index = build_entry_release_index(project_root, project=config.id)
    release_order = _build_release_sort_order(project_root)

    sorted_entries = _sort_entries_for_display(entry_map.values(), release_index, release_order)

    if select_all or select_released or select_unreleased:
        _show_entries_table_all(
            ctx,
            release_mode=release_mode,
            select_released=select_released,
            select_unreleased=select_unreleased,
            components=components,
            include_emoji=include_emoji,
            banner=banner,
        )
        return

    if release_mode:
        if not identifiers:
            raise click.ClickException(
                "--release requires identifiers (e.g., v1.0.0) or use "
                "--all, --released, or --unreleased flags."
            )
        _show_entries_table_release_mode(
            ctx,
            identifiers,
            components=components,
            include_emoji=include_emoji,
            entry_map=entry_map,
            sorted_entries=sorted_entries,
        )
        return

    if identifiers:
        resolutions = _resolve_identifiers_sequence(
            identifiers,
            project_root=project_root,
            config=config,
            sorted_entries=sorted_entries,
            entry_map=entry_map,
        )
        if len(resolutions) == 1 and resolutions[0].kind == "release" and not components:
            release_resolution = resolutions[0]
            resolved_manifest = release_resolution.manifest
            if resolved_manifest is None:
                raise click.ClickException(f"Release '{release_resolution.identifier}' not found.")
            _render_release(resolved_manifest, project_root, project_id=config.id)
            return
        filtered_entries: list[Entry] = []
        for resolution in resolutions:
            filtered_entries.extend(resolution.entries)
        entries = filtered_entries
    else:
        entries = sorted_entries

    entries = _filter_entries_by_project(entries, projects, config.id)
    entries = _filter_entries_by_component(entries, components)
    render_release_order = release_order if not identifiers else None
    _render_entries(
        entries,
        release_index,
        config,
        show_banner=banner,
        release_order=render_release_order,
        include_emoji=include_emoji,
    )


def _show_entries_card(
    ctx: CLIContext,
    identifiers: tuple[str, ...],
    component_filter: tuple[str, ...],
    *,
    include_emoji: bool,
    release_mode: bool = False,
    select_all: bool = False,
    select_released: bool = False,
    select_unreleased: bool = False,
    compact: bool = True,
) -> None:
    """Display entries as detailed cards."""
    config = ctx.ensure_config()
    project_root = ctx.project_root
    components = _normalize_component_filters(component_filter, config)
    release_index = build_entry_release_index(project_root, project=config.id)

    if select_all or select_released or select_unreleased:
        manifests = list(iter_release_manifests(project_root))
        manifests.sort(key=lambda m: m.created, reverse=True)

        # Determine what to include based on flags
        include_unreleased = not select_released
        include_released = not select_unreleased

        unreleased_entries: list[Entry] = []
        if include_unreleased:
            unreleased = list(iter_entries(project_root))
            unreleased_entries = _filter_entries_by_component(unreleased, components)
            unreleased_entries = sort_entries_desc(unreleased_entries)

        if release_mode:
            if unreleased_entries:
                _render_release_card(
                    None,
                    unreleased_entries,
                    config,
                    release_index,
                    include_emoji=include_emoji,
                    compact=compact,
                )

            if include_released:
                for manifest in manifests:
                    release_entries: list[Entry] = []
                    for entry_id in manifest.entries:
                        entry = load_release_entry(project_root, manifest, entry_id)
                        if entry is not None:
                            release_entries.append(entry)
                    filtered = _filter_entries_by_component(release_entries, components)
                    filtered = sort_entries_desc(filtered)
                    _render_release_card(
                        manifest,
                        filtered,
                        config,
                        release_index,
                        include_emoji=include_emoji,
                        compact=compact,
                    )
        else:
            all_entries: list[Entry] = list(unreleased_entries)
            if include_released:
                for manifest in manifests:
                    for entry_id in manifest.entries:
                        entry = load_release_entry(project_root, manifest, entry_id)
                        if entry is not None:
                            all_entries.append(entry)

            all_entries = _filter_entries_by_component(all_entries, components)
            all_entries = sort_entries_desc(all_entries)

            if not all_entries:
                raise click.ClickException("No entries found.")

            for entry in all_entries:
                versions = release_index.get(entry.entry_id, [])
                _render_single_entry(entry, versions, include_emoji=include_emoji)
        return

    if release_mode:
        if not identifiers:
            raise click.ClickException(
                "--release requires identifiers (e.g., v1.0.0) or use "
                "--all, --released, or --unreleased flags."
            )

        modules = ctx.get_modules()
        entry_map, release_index_all, _, sorted_entries = _gather_entry_context(
            project_root, modules
        )

        resolutions = _resolve_identifiers_sequence(
            identifiers,
            project_root=project_root,
            config=config,
            sorted_entries=sorted_entries,
            entry_map=entry_map,
        )

        release_groups: list[tuple[ReleaseManifest | None, list[Entry]]] = []
        for resolution in resolutions:
            filtered = _filter_entries_by_component(resolution.entries, components)
            filtered = sort_entries_desc(filtered)
            if resolution.kind == "release" and resolution.manifest:
                release_groups.append((resolution.manifest, filtered))
            else:
                for entry in filtered:
                    versions = release_index_all.get(entry.entry_id, [])
                    if versions:
                        for release_manifest in iter_release_manifests(project_root):
                            if release_manifest.version == versions[0]:
                                found = False
                                for i, (grp_manifest, entries) in enumerate(release_groups):
                                    if (
                                        grp_manifest
                                        and grp_manifest.version == release_manifest.version
                                    ):
                                        if entry not in entries:
                                            release_groups[i] = (grp_manifest, entries + [entry])
                                        found = True
                                        break
                                if not found:
                                    release_groups.append((release_manifest, [entry]))
                                break
                    else:
                        found = False
                        for i, (grp_manifest, entries) in enumerate(release_groups):
                            if grp_manifest is None:
                                if entry not in entries:
                                    release_groups[i] = (None, entries + [entry])
                                found = True
                                break
                        if not found:
                            release_groups.append((None, [entry]))

        if not release_groups:
            raise click.ClickException("No entries found for the given identifiers.")

        for grp_manifest, entries in release_groups:
            _render_release_card(
                grp_manifest,
                entries,
                config,
                release_index_all,
                include_emoji=include_emoji,
                compact=compact,
            )
        return

    if not identifiers:
        raise click.ClickException(
            "Provide at least one identifier such as a row number, entry ID, "
            "release version, or the 'unreleased' token."
        )

    config = ctx.ensure_config()
    project_root = ctx.project_root
    modules = ctx.get_modules()
    entry_map, release_index_all, _, sorted_entries = _gather_entry_context(project_root, modules)
    components = _normalize_component_filters(component_filter, config)

    if modules:
        combined_projects: list[tuple[Path, Config]] = [(project_root, config)]
        combined_projects.extend((m.root, m.config) for m in modules)
        project_order = {cfg.id: idx for idx, (_, cfg) in enumerate(combined_projects)}

        multi_entries = list(iter_multi_project_entries(combined_projects))

        def sort_key(item: MultiProjectEntry) -> tuple[float, int, str]:
            entry = item.entry
            project_idx = project_order.get(item.project_id, len(project_order))
            created = entry.created_at or datetime.min.replace(tzinfo=timezone.utc)
            return (created.timestamp(), project_idx, entry.entry_id)

        sorted_multi = sorted(multi_entries, key=sort_key)
        sorted_entries = [item.entry for item in sorted_multi]
        for item in sorted_multi:
            entry_map.setdefault(item.entry.entry_id, item.entry)

    resolutions = _resolve_identifiers_sequence(
        identifiers,
        project_root=project_root,
        config=config,
        sorted_entries=sorted_entries,
        entry_map=entry_map,
    )

    release_index = release_index_all
    rendered = False
    for resolution in resolutions:
        filtered_entries = _filter_entries_by_component(resolution.entries, components)
        if not filtered_entries:
            continue
        for entry in filtered_entries:
            versions = release_index.get(entry.entry_id, [])
            if resolution.kind == "release" and resolution.manifest:
                version = resolution.manifest.version
                if version and version not in versions:
                    versions = versions + [version]
            _render_single_entry(entry, versions, include_emoji=include_emoji)
            rendered = True
    if not rendered:
        raise click.ClickException(
            "No entries matched the provided identifiers and component filters."
        )


def _show_entries_export_all(
    ctx: CLIContext,
    *,
    view: ShowView,
    compact: bool,
    include_emoji: bool,
    explicit_links: bool,
    components: set[str],
    release_mode: bool,
    select_released: bool,
    select_unreleased: bool,
) -> None:
    """Handle --all/--released/--unreleased flags: export entries."""
    config = ctx.ensure_config()
    project_root = ctx.project_root
    release_index = build_entry_release_index(project_root, project=config.id)

    manifests = list(iter_release_manifests(project_root))
    manifests.sort(key=lambda m: m.created, reverse=True)

    # Determine what to include based on flags
    include_unreleased = not select_released
    include_released = not select_unreleased

    unreleased_entries: list[Entry] = []
    if include_unreleased:
        unreleased = list(iter_entries(project_root))
        unreleased_entries = _filter_entries_by_component(unreleased, components)
        unreleased_entries = sort_entries_desc(unreleased_entries)

    if release_mode:
        releases_data: list[dict[str, object]] = []

        # Gather module entries for unreleased preview
        modules = ctx.get_modules()
        module_entries_map: dict[str, tuple[Config, list[Entry]]] = {}
        current_versions: dict[str, str] = {}
        if modules and include_unreleased:
            previous_release = _get_latest_release_manifest(project_root)
            previous_module_versions = (
                previous_release.modules if previous_release else None
            )
            module_entries_map, current_versions = _gather_module_released_entries(
                modules, previous_module_versions, None
            )

        if unreleased_entries:
            payload = _build_release_payload(
                None, unreleased_entries, config, compact=compact
            )
            # Add modules to the payload for JSON output
            if module_entries_map:
                modules_data: list[dict[str, object]] = []
                for module_id in sorted(module_entries_map.keys()):
                    module_config, entries = module_entries_map[module_id]
                    module_payload: dict[str, object] = {
                        "id": module_id,
                        "name": module_config.name,
                        "entries": [
                            _entry_to_dict(e, module_config, compact=True) for e in entries
                        ],
                    }
                    modules_data.append(module_payload)
                payload["modules"] = modules_data
            releases_data.append(payload)

        if include_released:
            for manifest in manifests:
                release_entries: list[Entry] = []
                for entry_id in manifest.entries:
                    entry = load_release_entry(project_root, manifest, entry_id)
                    if entry is not None:
                        release_entries.append(entry)
                filtered = _filter_entries_by_component(release_entries, components)
                filtered = sort_entries_desc(filtered)
                releases_data.append(
                    _build_release_payload(manifest, filtered, config, compact=compact)
                )

        if view == "json":
            emit_output(json.dumps(releases_data, indent=2))
        else:
            blocks: list[str] = []
            if unreleased_entries:
                release_block = _render_markdown_release_block(
                    None,
                    unreleased_entries,
                    config,
                    release_index,
                    include_emoji=include_emoji,
                    explicit_links=explicit_links,
                    compact=compact,
                )
                # Append module sections for unreleased preview
                if module_entries_map:
                    module_sections: list[str] = []
                    for module_id in sorted(module_entries_map.keys()):
                        module_config, entries = module_entries_map[module_id]
                        module_body = _render_module_entries_compact(
                            entries,
                            module_config,
                            include_emoji=include_emoji,
                            explicit_links=explicit_links,
                        )
                        if module_body:
                            version = current_versions.get(module_id, "")
                            header = (
                                f"## {module_config.name} {version}"
                                if version
                                else f"## {module_config.name}"
                            )
                            module_sections.append(f"{header}\n\n{module_body}")
                    if module_sections:
                        release_block = (
                            release_block.rstrip("\n")
                            + "\n\n---\n\n"
                            + "\n\n".join(module_sections)
                        )
                blocks.append(release_block)
            if include_released:
                for manifest in manifests:
                    release_entries = []
                    for entry_id in manifest.entries:
                        entry = load_release_entry(project_root, manifest, entry_id)
                        if entry is not None:
                            release_entries.append(entry)
                    filtered = _filter_entries_by_component(release_entries, components)
                    filtered = sort_entries_desc(filtered)
                    blocks.append(
                        _render_markdown_release_block(
                            manifest,
                            filtered,
                            config,
                            release_index,
                            include_emoji=include_emoji,
                            explicit_links=explicit_links,
                            compact=compact,
                        )
                    )
            emit_output("\n---\n\n".join(blocks), newline=False)
    else:
        all_entries: list[Entry] = list(unreleased_entries)

        if include_released:
            for manifest in manifests:
                for entry_id in manifest.entries:
                    entry = load_release_entry(project_root, manifest, entry_id)
                    if entry is not None:
                        all_entries.append(entry)

        all_entries = _filter_entries_by_component(all_entries, components)
        all_entries = sort_entries_desc(all_entries)

        if not all_entries:
            raise click.ClickException("No entries found.")

        if view == "json":
            payload = _export_json_payload(
                None,
                all_entries,
                config,
                compact=compact,
                fallback_heading="All Entries",
                fallback_created=None,
            )
            emit_output(json.dumps(payload, indent=2))
        else:
            if compact:
                content = _export_markdown_compact(
                    None,
                    all_entries,
                    config,
                    release_index,
                    include_emoji=include_emoji,
                    explicit_links=explicit_links,
                )
            else:
                content = _export_markdown_release(
                    None,
                    all_entries,
                    config,
                    release_index,
                    include_emoji=include_emoji,
                    explicit_links=explicit_links,
                )
            emit_output(content, newline=False)


def _show_entries_export_release_mode(
    ctx: CLIContext,
    identifiers: tuple[str, ...],
    *,
    view: ShowView,
    compact: bool,
    include_emoji: bool,
    explicit_links: bool,
    components: set[str],
    entry_map: dict[str, Entry],
    sorted_entries: list[Entry],
) -> None:
    """Handle --release flag with explicit identifiers: group entries by release."""
    config = ctx.ensure_config()
    project_root = ctx.project_root

    if len(identifiers) == 1 and not components:
        identifier = identifiers[0]
        resolutions = _resolve_identifiers_sequence(
            [identifier],
            project_root=project_root,
            config=config,
            sorted_entries=sorted_entries,
            entry_map=entry_map,
        )
        if len(resolutions) == 1 and resolutions[0].kind == "release":
            if view == "json":
                release_index = build_entry_release_index(project_root, project=config.id)
                resolution = resolutions[0]
                manifest = resolution.manifest
                entries_for_output = sorted(resolution.entries, key=_release_entry_sort_key)

                fallback_heading = (
                    manifest.title if manifest and manifest.title else identifier
                )
                fallback_created = manifest.created if manifest else None
                payload = _export_json_payload(
                    manifest,
                    entries_for_output,
                    config,
                    compact=compact,
                    fallback_heading=fallback_heading,
                    fallback_created=fallback_created,
                )

                modules = ctx.get_modules()
                if modules:
                    if manifest:
                        previous_release = _get_release_manifest_before(
                            project_root, manifest.version
                        )
                        target_module_versions = manifest.modules or None
                    else:
                        previous_release = _get_latest_release_manifest(project_root)
                        target_module_versions = None
                    previous_module_versions = (
                        previous_release.modules if previous_release else None
                    )
                    module_entries, _ = _gather_module_released_entries(
                        modules, previous_module_versions, target_module_versions
                    )
                    if module_entries:
                        modules_data: list[dict[str, object]] = []
                        for module_id in sorted(module_entries.keys()):
                            module_config, entries = module_entries[module_id]
                            module_payload: dict[str, object] = {
                                "id": module_id,
                                "name": module_config.name,
                                "entries": [
                                    _entry_to_dict(e, module_config, compact=True) for e in entries
                                ],
                            }
                            modules_data.append(module_payload)
                        payload["modules"] = modules_data

                emit_output(json.dumps([payload], indent=2))
                return
            else:
                release_index = build_entry_release_index(project_root, project=config.id)
                resolution = resolutions[0]
                manifest = resolution.manifest if resolution.kind == "release" else None
                entries_for_output = sorted(resolution.entries, key=_release_entry_sort_key)

                if manifest:
                    title = manifest.title or manifest.version
                else:
                    title = "Unreleased Changes"

                if resolution.kind == "release":
                    release_body = (
                        _render_release_notes_compact(
                            entries_for_output,
                            config,
                            include_emoji=include_emoji,
                            explicit_links=explicit_links,
                        )
                        if compact
                        else _render_release_notes(
                            entries_for_output,
                            config,
                            include_emoji=include_emoji,
                            explicit_links=explicit_links,
                        )
                    )
                    output = _compose_release_document(
                        manifest.intro if manifest else None,
                        release_body,
                    )
                else:
                    release_body = (
                        _export_markdown_compact(
                            None,
                            entries_for_output,
                            config,
                            release_index,
                            include_emoji=include_emoji,
                            explicit_links=explicit_links,
                        )
                        if compact
                        else _export_markdown_release(
                            None,
                            entries_for_output,
                            config,
                            release_index,
                            explicit_links=explicit_links,
                            include_emoji=include_emoji,
                        )
                    )
                    output = release_body.rstrip("\n")

                output = f"# {title}\n\n{output}"

                modules = ctx.get_modules()
                if modules:
                    if manifest:
                        previous_release = _get_release_manifest_before(
                            project_root, manifest.version
                        )
                        target_module_versions = manifest.modules or None
                    else:
                        previous_release = _get_latest_release_manifest(project_root)
                        target_module_versions = None
                    previous_module_versions = (
                        previous_release.modules if previous_release else None
                    )
                    module_entries, current_versions = _gather_module_released_entries(
                        modules, previous_module_versions, target_module_versions
                    )
                    version_map = target_module_versions or current_versions
                    if module_entries:
                        module_sections: list[str] = []
                        for module_id in sorted(module_entries.keys()):
                            module_config, entries = module_entries[module_id]
                            module_body = _render_module_entries_compact(
                                entries,
                                module_config,
                                include_emoji=include_emoji,
                                explicit_links=explicit_links,
                            )
                            if module_body:
                                version = version_map.get(module_id, "")
                                header = (
                                    f"## {module_config.name} {version}"
                                    if version
                                    else f"## {module_config.name}"
                                )
                                module_sections.append(f"{header}\n\n{module_body}")
                        if module_sections:
                            output = output + "\n\n---\n\n" + "\n\n".join(module_sections)

                emit_output(output)
                return

    release_index = build_entry_release_index(project_root, project=config.id)

    resolutions = _resolve_identifiers_sequence(
        identifiers,
        project_root=project_root,
        config=config,
        sorted_entries=sorted_entries,
        entry_map=entry_map,
    )

    release_groups: list[tuple[ReleaseManifest | None, list[Entry]]] = []
    for resolution in resolutions:
        filtered = _filter_entries_by_component(resolution.entries, components)
        filtered = sort_entries_desc(filtered)
        if resolution.kind == "release" and resolution.manifest:
            release_groups.append((resolution.manifest, filtered))
        else:
            for entry in filtered:
                versions = release_index.get(entry.entry_id, [])
                if versions:
                    for manifest in iter_release_manifests(project_root):
                        if manifest.version == versions[0]:
                            found = False
                            for i, (m, entries) in enumerate(release_groups):
                                if m and m.version == manifest.version:
                                    if entry not in entries:
                                        release_groups[i] = (m, entries + [entry])
                                    found = True
                                    break
                            if not found:
                                release_groups.append((manifest, [entry]))
                            break
                else:
                    found = False
                    for i, (m, entries) in enumerate(release_groups):
                        if m is None:
                            if entry not in entries:
                                release_groups[i] = (None, entries + [entry])
                            found = True
                            break
                    if not found:
                        release_groups.append((None, [entry]))

    if not release_groups:
        raise click.ClickException("No entries found for the given identifiers.")

    if view == "json":
        releases_data = [
            _build_release_payload(manifest, entries, config, compact=compact)
            for manifest, entries in release_groups
        ]
        emit_output(json.dumps(releases_data, indent=2))
    else:
        blocks = [
            _render_markdown_release_block(
                manifest,
                entries,
                config,
                release_index,
                include_emoji=include_emoji,
                explicit_links=explicit_links,
                compact=compact,
            )
            for manifest, entries in release_groups
        ]
        emit_output("\n---\n\n".join(blocks), newline=False)


def _show_entries_export(
    ctx: CLIContext,
    identifiers: tuple[str, ...],
    *,
    view: ShowView,
    compact: Optional[bool],
    include_emoji: bool,
    explicit_links: bool,
    component_filter: tuple[str, ...],
    release_mode: bool = False,
    select_all: bool = False,
    select_released: bool = False,
    select_unreleased: bool = False,
) -> None:
    """Export entries as Markdown or JSON."""
    config = ctx.ensure_config()
    project_root = ctx.project_root
    components = _normalize_component_filters(component_filter, config)
    entry_map, _, _, sorted_entries = _gather_entry_context(project_root)

    compact_flag = config.export_style == EXPORT_STYLE_COMPACT if compact is None else compact
    release_index_export = build_entry_release_index(project_root, project=config.id)

    if select_all or select_released or select_unreleased:
        _show_entries_export_all(
            ctx,
            view=view,
            compact=compact_flag,
            include_emoji=include_emoji,
            explicit_links=explicit_links,
            components=components,
            release_mode=release_mode,
            select_released=select_released,
            select_unreleased=select_unreleased,
        )
        return

    if release_mode:
        if not identifiers:
            raise click.ClickException(
                "--release requires identifiers (e.g., v1.0.0) or use "
                "--all, --released, or --unreleased flags."
            )
        _show_entries_export_release_mode(
            ctx,
            identifiers,
            view=view,
            compact=compact_flag,
            include_emoji=include_emoji,
            explicit_links=explicit_links,
            components=components,
            entry_map=entry_map,
            sorted_entries=sorted_entries,
        )
        return

    manifest_for_export: ReleaseManifest | None = None

    if identifiers:
        resolutions = _resolve_identifiers_sequence(
            identifiers,
            project_root=project_root,
            config=config,
            sorted_entries=sorted_entries,
            entry_map=entry_map,
        )

        if len(resolutions) == 1 and resolutions[0].kind == "release":
            manifest_for_export = resolutions[0].manifest

        ordered_entries: dict[str, Entry] = {}
        for resolution in resolutions:
            for entry in resolution.entries:
                if entry.entry_id not in ordered_entries:
                    ordered_entries[entry.entry_id] = entry
        filtered_entries = _filter_entries_by_component(ordered_entries.values(), components)
        export_entries = sort_entries_desc(filtered_entries)

        if manifest_for_export is not None:
            fallback_heading = (
                resolutions[0].manifest.title
                if resolutions[0].manifest and resolutions[0].manifest.title
                else resolutions[0].identifier
            )
            fallback_created = None
        elif len(resolutions) == 1 and resolutions[0].kind in {"entry", "row"} and export_entries:
            first_entry = export_entries[0]
            fallback_heading = f"Entry {first_entry.entry_id}"
            fallback_created = first_entry.created_at
        else:
            fallback_heading = "Selected Entries"
            dates = [entry.created_at for entry in export_entries if entry.created_at]
            fallback_created = min(dates) if dates else None
    else:
        unreleased = list(iter_entries(project_root))
        filtered_entries = _filter_entries_by_component(unreleased, components)
        export_entries = sort_entries_desc(filtered_entries)
        fallback_heading = "Unreleased Changes"
        fallback_created = None

    if not export_entries:
        raise click.ClickException(
            "No entries matched the provided identifiers and component filters for export."
        )

    if view == "markdown":
        if compact_flag:
            content = _export_markdown_compact(
                manifest_for_export,
                export_entries,
                config,
                release_index_export,
                include_emoji=include_emoji,
                explicit_links=explicit_links,
            )
        else:
            content = _export_markdown_release(
                manifest_for_export,
                export_entries,
                config,
                release_index_export,
                include_emoji=include_emoji,
                explicit_links=explicit_links,
            )
        emit_output(content, newline=False)
    else:
        payload = _export_json_payload(
            manifest_for_export,
            export_entries,
            config,
            compact=compact_flag,
            fallback_heading=fallback_heading,
            fallback_created=fallback_created,
        )
        emit_output(json.dumps(payload, indent=2))


def run_show_entries(
    ctx: CLIContext,
    *,
    identifiers: Sequence[str] | None = None,
    view: ShowView = "table",
    project_filter: Sequence[str] | None = None,
    component_filter: Sequence[str] | None = None,
    banner: bool = False,
    compact: Optional[bool] = None,
    include_emoji: bool = True,
    explicit_links: bool = False,
    release_mode: bool = False,
    select_all: bool = False,
    select_released: bool = False,
    select_unreleased: bool = False,
) -> None:
    """Python-friendly wrapper around the ``show`` command."""

    identifier_values = tuple(identifiers or ())
    project_filters = tuple(project_filter or ())
    component_filters = tuple(component_filter or ())

    # Validate mutually exclusive flags
    filter_flags = [select_all, select_released, select_unreleased]
    if sum(filter_flags) > 1:
        raise click.ClickException(
            "--all, --released, and --unreleased are mutually exclusive."
        )
    if any(filter_flags) and identifier_values:
        raise click.ClickException(
            "Filter flags (--all, --released, --unreleased) cannot be combined "
            "with explicit identifiers."
        )

    if view == "table":
        if compact is not None:
            raise click.ClickException(
                "--compact/--no-compact only apply to markdown and json views."
            )
        _show_entries_table(
            ctx,
            identifier_values,
            project_filters,
            component_filters,
            banner,
            include_emoji=include_emoji,
            release_mode=release_mode,
            select_all=select_all,
            select_released=select_released,
            select_unreleased=select_unreleased,
        )
        return

    if project_filters or banner:
        raise click.ClickException("--project/--banner are only available in table view.")

    if view == "card":
        if compact is not None and not release_mode:
            raise click.ClickException(
                "--compact/--no-compact only apply to markdown, json, and release card views."
            )
        card_compact = compact if compact is not None else False
        _show_entries_card(
            ctx,
            identifier_values,
            component_filters,
            include_emoji=include_emoji,
            release_mode=release_mode,
            select_all=select_all,
            select_released=select_released,
            select_unreleased=select_unreleased,
            compact=card_compact,
        )
        return

    if view in {"markdown", "json"}:
        _show_entries_export(
            ctx,
            identifier_values,
            view=view,
            compact=compact,
            include_emoji=include_emoji,
            explicit_links=explicit_links,
            component_filter=component_filters,
            release_mode=release_mode,
            select_all=select_all,
            select_released=select_released,
            select_unreleased=select_unreleased,
        )
        return

    raise click.ClickException(f"Unsupported view '{view}'.")


# The show_entries command will be defined after all helper functions
# We use a function to create it so it can be imported and registered by __init__.py

SHOW_COMMAND_SUMMARY = "Display changelog entries in tables, cards, or exports."


def _create_show_command() -> click.Command:
    """Create the show command with all decorators."""

    @click.command("show")
    @click.argument("identifiers", nargs=-1, required=False)
    @click.option(
        "-t",
        "--table",
        "view_flags",
        flag_value="table",
        help="Display entries in a table view (default).",
        multiple=True,
    )
    @click.option(
        "-c",
        "--card",
        "view_flags",
        flag_value="card",
        help="Display entries as detailed cards.",
        multiple=True,
    )
    @click.option(
        "-m",
        "--markdown",
        "view_flags",
        flag_value="markdown",
        help="Export entries as Markdown.",
        multiple=True,
    )
    @click.option(
        "-j",
        "--json",
        "view_flags",
        flag_value="json",
        help="Export entries as JSON.",
        multiple=True,
    )
    @click.option("--project", "project_filter", multiple=True, help="Filter by project key.")
    @click.option("--component", "component_filter", multiple=True, help="Filter by component.")
    @click.option("--banner", is_flag=True, help="Display a project banner above entries.")
    @click.option(
        "--compact",
        "compact",
        flag_value=True,
        default=None,
        help="Use the compact layout for Markdown and JSON output.",
    )
    @click.option(
        "--no-compact",
        "compact",
        flag_value=False,
        help="Disable the compact layout for Markdown and JSON output.",
    )
    @click.option(
        "--no-emoji",
        is_flag=True,
        help="Disable type emoji in entry output.",
    )
    @click.option(
        "--explicit-links/--no-explicit-links",
        default=None,
        help="Render @mentions and PR references as explicit Markdown links.",
    )
    @click.option(
        "--release",
        is_flag=True,
        help="Display entries grouped by release with release metadata.",
    )
    @click.option(
        "--all",
        "select_all",
        is_flag=True,
        help="Show all entries (released and unreleased).",
    )
    @click.option(
        "--released",
        "select_released",
        is_flag=True,
        help="Show only released entries.",
    )
    @click.option(
        "--unreleased",
        "select_unreleased",
        is_flag=True,
        help="Show only unreleased entries.",
    )
    @click.pass_obj
    def show_entries_cmd(
        ctx: CLIContext,
        identifiers: tuple[str, ...],
        view_flags: tuple[str, ...],
        project_filter: tuple[str, ...],
        component_filter: tuple[str, ...],
        banner: bool,
        compact: Optional[bool],
        no_emoji: bool,
        explicit_links: Optional[bool],
        release: bool,
        select_all: bool,
        select_released: bool,
        select_unreleased: bool,
    ) -> None:
        """Display changelog entries in tables, cards, or export formats."""

        config = ctx.ensure_config()
        view_choice = view_flags[-1] if view_flags else "table"
        if view_choice not in {"table", "card", "markdown", "json"}:
            raise click.ClickException(f"Unsupported view '{view_choice}'.")
        resolved_explicit_links = (
            config.explicit_links if explicit_links is None else explicit_links
        )
        run_show_entries(
            ctx,
            identifiers=identifiers,
            view=cast(ShowView, view_choice),
            project_filter=project_filter,
            component_filter=component_filter,
            banner=banner,
            compact=compact,
            include_emoji=not no_emoji,
            explicit_links=resolved_explicit_links,
            release_mode=release,
            select_all=select_all,
            select_released=select_released,
            select_unreleased=select_unreleased,
        )

    show_help = _command_help_text(
        summary=SHOW_COMMAND_SUMMARY,
        command_name="show",
        verb="show",
        row_hint="Row numbers (e.g., 1, 2, 3)",
        version_hint="to show all entries in that release or export it",
    )
    show_entries_cmd.__doc__ = show_help
    show_entries_cmd.help = show_help
    show_entries_cmd.short_help = SHOW_COMMAND_SUMMARY

    return show_entries_cmd


# Create the command instance
show_entries = _create_show_command()

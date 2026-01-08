"""Shared rendering utilities for tables, entries, and release notes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Iterable,
    Literal,
    Optional,
    TypedDict,
)

from rich.console import RenderableType, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.rule import Rule

from ..config import Config
from ..entries import (
    Entry,
    MultiProjectEntry,
    iter_entries,
    sort_entries_desc,
)
from ..releases import (
    ReleaseManifest,
    build_entry_release_index,
    iter_release_manifests,
    load_release_entry,
)
from ..utils import (
    console,
    extract_excerpt,
    log_info,
    normalize_markdown,
)
from ._core import (
    ENTRY_TYPE_STYLES,
    ENTRY_TYPE_EMOJIS,
    ENTRY_EXPORT_ORDER,
    DEFAULT_ENTRY_TYPE,
    _format_author,
    _format_section_title,
    _parse_pr_numbers,
    _collect_author_pr_text,
    _format_author_line,
)

__all__ = [
    "ColumnSpec",
    "IdentifierResolution",
    "OverflowMethod",
    "JustifyMethod",
    "_print_renderable",
    "_entries_table_layout",
    "_ellipsis_cell",
    "_add_table_column",
    "_render_project_header",
    "_render_entries",
    "_render_release",
    "_render_single_entry",
    "_render_entries_multi_project",
    "_render_release_notes",
    "_render_release_notes_compact",
    "_render_module_entries_compact",
    "_compose_release_document",
    "_build_entry_title",
    "_build_entry_metadata_line",
    "_build_entry_body",
    "_sort_entries_for_display",
    "_entry_release_group",
    "_render_project_banner",
    "_release_entry_sort_key",
    "_build_release_sort_order",
]


IdentifierKind = Literal["row", "entry", "release", "unreleased"]


@dataclass
class IdentifierResolution:
    """Mapping from an identifier to matching entries."""

    kind: IdentifierKind
    entries: list[Entry]
    identifier: str
    manifest: Optional[ReleaseManifest] = None


OverflowMethod = Literal["fold", "crop", "ellipsis", "ignore"]
JustifyMethod = Literal["default", "left", "center", "right", "full"]


class ColumnSpec(TypedDict, total=False):
    """Configuration for rendering a Rich table column."""

    max_width: int
    overflow: OverflowMethod
    no_wrap: bool
    min_width: int


def _print_renderable(renderable: RenderableType) -> None:
    """Print a Rich renderable to the console."""
    console.print(renderable)


def _entries_table_layout(
    console_width: int, include_component: bool, include_project: bool = False
) -> tuple[list[str], dict[str, ColumnSpec]]:
    """Return the visible columns and their specs for the current terminal width."""

    width = max(console_width, 60)
    if width < 70:
        columns = ["num", "date", "title", "type"]
        specs: dict[str, ColumnSpec] = {
            "num": {"min_width": 3, "max_width": 5, "no_wrap": True},
            "date": {"min_width": 10, "max_width": 10, "no_wrap": True},
            "title": {"min_width": 20, "max_width": 32, "overflow": "ellipsis", "no_wrap": True},
            "type": {"min_width": 3, "max_width": 4, "no_wrap": True},
        }
        if include_component:
            columns.append("component")
            specs["component"] = {
                "min_width": 4,
                "max_width": 8,
                "no_wrap": True,
                "overflow": "ellipsis",
            }
    elif width < 78:
        columns = ["num", "date", "version", "title", "type"]
        specs = {
            "num": {"min_width": 3, "max_width": 5, "no_wrap": True},
            "date": {"min_width": 10, "max_width": 10, "no_wrap": True},
            "version": {"max_width": 8, "no_wrap": True},
            "title": {"min_width": 18, "max_width": 30, "overflow": "ellipsis", "no_wrap": True},
            "type": {"min_width": 3, "max_width": 4, "no_wrap": True},
        }
        if include_component:
            columns.append("component")
            specs["component"] = {
                "min_width": 4,
                "max_width": 8,
                "no_wrap": True,
                "overflow": "ellipsis",
            }
    elif width < 88:
        columns = ["num", "date", "version", "title", "type", "prs"]
        specs = {
            "num": {"min_width": 3, "max_width": 5, "no_wrap": True},
            "date": {"min_width": 10, "max_width": 10, "no_wrap": True},
            "version": {"max_width": 9, "no_wrap": True},
            "title": {"min_width": 18, "max_width": 28, "overflow": "ellipsis", "no_wrap": True},
            "prs": {"max_width": 12, "no_wrap": True},
            "type": {"min_width": 3, "max_width": 4, "no_wrap": True},
        }
        if include_component:
            columns.insert(5, "component")
            specs["component"] = {
                "min_width": 4,
                "max_width": 10,
                "no_wrap": True,
                "overflow": "ellipsis",
            }
    elif width < 110:
        columns = ["num", "date", "version", "title", "type", "prs", "authors"]
        specs = {
            "num": {"min_width": 3, "max_width": 5, "no_wrap": True},
            "date": {"min_width": 10, "max_width": 10, "no_wrap": True},
            "version": {"max_width": 9, "no_wrap": True},
            "title": {"min_width": 18, "max_width": 26, "overflow": "ellipsis", "no_wrap": True},
            "prs": {"max_width": 12, "no_wrap": True},
            "authors": {
                "min_width": 10,
                "max_width": 14,
                "overflow": "ellipsis",
                "no_wrap": True,
            },
            "type": {"min_width": 3, "max_width": 4, "no_wrap": True},
        }
        if include_component:
            columns.insert(5, "component")
            specs["component"] = {
                "min_width": 4,
                "max_width": 10,
                "no_wrap": True,
                "overflow": "ellipsis",
            }
    elif width < 140:
        columns = ["num", "date", "version", "title", "type", "prs", "authors", "id"]
        specs = {
            "num": {"min_width": 3, "max_width": 5, "no_wrap": True},
            "date": {"min_width": 10, "max_width": 10, "no_wrap": True},
            "version": {"max_width": 10, "no_wrap": True},
            "title": {"min_width": 18, "max_width": 32, "overflow": "ellipsis", "no_wrap": True},
            "prs": {"max_width": 12, "no_wrap": True},
            "authors": {
                "min_width": 10,
                "max_width": 16,
                "overflow": "ellipsis",
                "no_wrap": True,
            },
            "id": {"min_width": 16, "max_width": 22, "overflow": "ellipsis", "no_wrap": True},
            "type": {"min_width": 3, "max_width": 4, "no_wrap": True},
        }
        if include_component:
            columns.insert(5, "component")
            specs["component"] = {
                "min_width": 4,
                "max_width": 10,
                "no_wrap": True,
                "overflow": "ellipsis",
            }
    else:
        columns = ["num", "date", "version", "title", "type", "prs", "authors", "id"]
        specs = {
            "num": {"min_width": 3, "max_width": 5, "no_wrap": True},
            "date": {"min_width": 10, "max_width": 10, "no_wrap": True},
            "version": {"max_width": 12, "no_wrap": True},
            "title": {"min_width": 20, "max_width": 40, "overflow": "fold"},
            "prs": {"max_width": 14, "no_wrap": True},
            "authors": {"min_width": 14, "max_width": 20, "overflow": "fold"},
            "id": {"min_width": 18, "max_width": 28, "overflow": "fold"},
            "type": {"min_width": 3, "max_width": 4, "no_wrap": True},
        }
        if include_component:
            columns.insert(5, "component")
            specs["component"] = {
                "min_width": 6,
                "max_width": 12,
                "no_wrap": True,
                "overflow": "fold",
            }
    # Inject project column after num when in module mode
    if include_project:
        columns.insert(1, "project")
        # Use responsive widths based on terminal width
        if width < 80:
            specs["project"] = {
                "min_width": 6,
                "max_width": 12,
                "overflow": "ellipsis",
                "no_wrap": True,
            }
        elif width < 120:
            specs["project"] = {
                "min_width": 8,
                "max_width": 14,
                "overflow": "ellipsis",
                "no_wrap": True,
            }
        else:
            specs["project"] = {
                "min_width": 10,
                "max_width": 18,
                "overflow": "ellipsis",
                "no_wrap": True,
            }
    return columns, specs


def _ellipsis_cell(
    value: str,
    column: str,
    specs: dict[str, ColumnSpec],
    *,
    style: str | None = None,
) -> Text | str:
    """Return a Text cell with ellipsis truncation when requested."""

    spec = specs.get(column)
    if not spec:
        return value
    overflow_mode = spec.get("overflow")
    if overflow_mode != "ellipsis":
        return value
    width = spec.get("max_width") or spec.get("min_width")
    if not width:
        return value
    text = Text(str(value), style=style or "")
    plain = text.plain
    if len(plain) > width:
        text = Text(plain[: width - 1] + "…", style=style or "")
    text.no_wrap = True
    return text


def _add_table_column(
    table: Table,
    header: str,
    column_key: str,
    specs: dict[str, ColumnSpec],
    *,
    style: str | None = None,
    justify: JustifyMethod = "left",
    overflow_default: OverflowMethod = "fold",
    no_wrap_default: bool = False,
) -> None:
    spec = specs.get(column_key)
    min_width = spec.get("min_width") if spec and "min_width" in spec else None
    max_width = spec.get("max_width") if spec and "max_width" in spec else None
    overflow = overflow_default
    if spec and "overflow" in spec:
        overflow = spec["overflow"]
    no_wrap = no_wrap_default
    if spec and "no_wrap" in spec:
        no_wrap = spec["no_wrap"]
    table.add_column(
        header,
        style=style,
        justify=justify,
        overflow=overflow,
        min_width=min_width,
        max_width=max_width,
        no_wrap=no_wrap,
    )


def _render_project_banner(config: Config) -> Panel:
    """Render a project banner panel."""
    legend = "  ".join(
        f"{ENTRY_TYPE_EMOJIS.get(entry_type, '•')} {entry_type}"
        for entry_type in ENTRY_EXPORT_ORDER
    )
    header = Text.assemble(
        ("Name: ", "bold"),
        config.name or "—",
        ("\nID: ", "bold"),
        config.id or "—",
        ("\nRepository: ", "bold"),
        config.repository or "—",
        ("\nTypes: ", "bold"),
        legend or "—",
    )
    return Panel.fit(header, title="Project")


def _render_project_header(config: Config) -> None:
    _print_renderable(_render_project_banner(config))


def _build_release_sort_order(project_root: Path) -> dict[str, int]:
    """Build a mapping from version to sort order (newest = highest)."""
    manifests = list(iter_release_manifests(project_root))
    manifests.sort(key=lambda m: m.created)
    return {m.version: i for i, m in enumerate(manifests)}


def _sort_entries_for_display(
    entries: Iterable[Entry],
    release_index: dict[str, list[str]],
    release_order: dict[str, int],
) -> list[Entry]:
    """Sort entries so the newest entry ends up last in the table view."""
    entries_list = list(entries)
    unreleased_rank = len(release_order) + 1

    def sort_key(entry: Entry) -> tuple[int, datetime, str]:
        versions = release_index.get(entry.entry_id) or []
        if versions:
            ranks = [release_order.get(version, unreleased_rank) for version in versions]
            release_rank = min(ranks)
        else:
            release_rank = unreleased_rank  # unreleased entries last
        created = entry.created_at or datetime.min.replace(tzinfo=timezone.utc)
        return (release_rank, created, entry.entry_id)

    # Sort ascending by (release_rank, created, entry_id): oldest entries first
    return sorted(entries_list, key=sort_key)


def _entry_release_group(
    entry: Entry,
    release_index: dict[str, list[str]],
    release_order: dict[str, int],
) -> int:
    """Return a group key for sectioning entries by release."""
    versions = release_index.get(entry.entry_id, [])
    if not versions:
        return -1  # unreleased
    return max(release_order.get(v, 0) for v in versions)


def _render_entries(
    entries: Iterable[Entry],
    release_index: dict[str, list[str]],
    config: Config,
    show_banner: bool = False,
    release_order: dict[str, int] | None = None,
    *,
    include_emoji: bool = True,
) -> None:
    if show_banner:
        _render_project_header(config)

    entries_list = list(entries)
    include_component = any(entry.components for entry in entries_list)
    visible_columns, column_specs = _entries_table_layout(console.size.width, include_component)
    table_width = max(console.size.width, 40)
    table = Table(show_lines=False, expand=False, width=table_width, pad_edge=False)
    if "num" in visible_columns:
        _add_table_column(
            table,
            "#",
            "num",
            column_specs,
            style="dim",
            justify="right",
            overflow_default="fold",
            no_wrap_default=True,
        )
    if "date" in visible_columns:
        _add_table_column(
            table,
            "Date",
            "date",
            column_specs,
            style="yellow",
            overflow_default="fold",
            no_wrap_default=True,
        )
    if "version" in visible_columns:
        _add_table_column(
            table,
            "Version",
            "version",
            column_specs,
            style="cyan",
            justify="center",
            overflow_default="fold",
            no_wrap_default=True,
        )
    if "title" in visible_columns:
        _add_table_column(
            table,
            "Title",
            "title",
            column_specs,
            style="bold",
            overflow_default="fold",
        )
    if "type" in visible_columns:
        _add_table_column(
            table,
            "Type",
            "type",
            column_specs,
            style="magenta",
            justify="center",
            overflow_default="ellipsis",
            no_wrap_default=True,
        )
    if "component" in visible_columns:
        _add_table_column(
            table,
            "Component",
            "component",
            column_specs,
            style="green",
            justify="center",
            overflow_default="ellipsis",
            no_wrap_default=True,
        )
    if "prs" in visible_columns:
        _add_table_column(
            table,
            "PRs",
            "prs",
            column_specs,
            style="yellow",
            overflow_default="fold",
            no_wrap_default=True,
        )
    if "authors" in visible_columns:
        _add_table_column(
            table,
            "Authors",
            "authors",
            column_specs,
            style="blue",
            overflow_default="fold",
        )
    if "id" in visible_columns:
        _add_table_column(
            table,
            "ID",
            "id",
            column_specs,
            style="cyan",
            overflow_default="ellipsis",
            no_wrap_default=True,
        )

    has_rows = False
    release_groups: list[int | None]
    if release_order is not None:
        sorted_entries = _sort_entries_for_display(entries_list, release_index, release_order)
        release_groups = [
            _entry_release_group(entry, release_index, release_order) for entry in sorted_entries
        ]
    else:
        sorted_entries = sort_entries_desc(entries_list)
        release_groups = [None] * len(sorted_entries)

    total_rows = len(sorted_entries)

    for index, entry in enumerate(sorted_entries):
        metadata = entry.metadata
        created_display = entry.created_date.isoformat() if entry.created_date else "—"
        type_value = metadata.get("type", "change")
        versions = release_index.get(entry.entry_id)
        version_display = ", ".join(versions) if versions else "—"
        if include_emoji:
            glyph = ENTRY_TYPE_EMOJIS.get(type_value, "•")
        else:
            glyph = type_value[:1].upper() if type_value else "?"
        type_display = Text(glyph, style=ENTRY_TYPE_STYLES.get(type_value, ""))
        row: list[RenderableType] = []
        if "num" in visible_columns:
            if release_order is not None:
                display_row_num = total_rows - index
            else:
                display_row_num = index + 1
            row.append(str(display_row_num))
        if "date" in visible_columns:
            row.append(created_display)
        if "version" in visible_columns:
            row.append(version_display)
        if "title" in visible_columns:
            row.append(_ellipsis_cell(metadata.get("title", "Untitled"), "title", column_specs))
        if "type" in visible_columns:
            row.append(type_display)
        if "component" in visible_columns:
            component_value = ", ".join(entry.components) if entry.components else "—"
            row.append(_ellipsis_cell(component_value, "component", column_specs))
        if "prs" in visible_columns:
            pr_numbers = _parse_pr_numbers(metadata)
            pr_display = ", ".join(f"#{pr}" for pr in pr_numbers) if pr_numbers else "—"
            row.append(_ellipsis_cell(pr_display, "prs", column_specs))
        if "authors" in visible_columns:
            row.append(
                _ellipsis_cell(
                    ", ".join(metadata.get("authors") or []) or "—",
                    "authors",
                    column_specs,
                )
            )
        if "id" in visible_columns:
            row.append(_ellipsis_cell(entry.entry_id, "id", column_specs, style="cyan"))
        end_section = False
        if release_order is not None and index < len(sorted_entries) - 1:
            current_group = release_groups[index]
            next_group = release_groups[index + 1]
            if current_group != next_group:
                end_section = True

        table.add_row(*row, end_section=end_section)
        has_rows = True

    if has_rows:
        _print_renderable(table)
    else:
        log_info("no entries found.")


def _render_release(
    manifest: ReleaseManifest,
    project_root: Path,
    *,
    project_id: str,
) -> None:
    _print_renderable(Rule(f"Release {manifest.version}"))
    header = Text.assemble(
        ("Title: ", "bold"),
        manifest.title or manifest.version or "—",
        ("\nIntro: ", "bold"),
        ("present" if (manifest.intro and manifest.intro.strip()) else "—"),
        ("\nCreated: ", "bold"),
        manifest.created.isoformat(),
        ("\nProject: ", "bold"),
        project_id or "—",
    )
    _print_renderable(header)

    if manifest.intro:
        _print_renderable(
            Panel(
                manifest.intro,
                title="Introduction",
                subtitle="Markdown",
                expand=False,
            )
        )

    all_entries = {entry.entry_id: entry for entry in iter_entries(project_root)}
    table = Table(title="Included Entries")
    table.add_column("Order")
    table.add_column("Entry ID", style="cyan")
    table.add_column("Title")
    table.add_column("Type", style="magenta")

    resolved_entries: list[Entry | None] = []
    has_components = False
    for entry_id in manifest.entries:
        entry = all_entries.get(entry_id)
        if entry is None:
            entry = load_release_entry(project_root, manifest, entry_id)
        resolved_entries.append(entry)
        if entry and entry.components:
            has_components = True

    if has_components:
        table.add_column("Component", style="green")

    for index, entry in enumerate(resolved_entries, 1):
        entry_id = manifest.entries[index - 1]
        if entry:
            row = [
                str(index),
                entry_id,
                entry.metadata.get("title", "Untitled"),
                entry.metadata.get("type", "change"),
            ]
            if has_components:
                row.append(", ".join(entry.components) if entry.components else "—")
            table.add_row(*row)
        else:
            row = [str(index), entry_id, "[red]Missing entry[/red]", "—"]
            if has_components:
                row.append("—")
            table.add_row(*row)
    _print_renderable(table)


def _build_entry_title(entry: Entry, *, include_emoji: bool = True) -> Text:
    """Build a Rich Text title for an entry."""
    type_color = ENTRY_TYPE_STYLES.get(entry.type, "white")
    title = Text()
    if include_emoji:
        type_emoji = ENTRY_TYPE_EMOJIS.get(entry.type, "•")
        title.append(f"{type_emoji} ", style="bold")
    title.append(entry.title, style=f"bold {type_color}")
    return title


def _build_entry_metadata_line(entry: Entry) -> Text:
    """Build a compact metadata line for an entry (date · authors · PRs)."""
    meta_parts: list[str] = []
    if entry.created_at:
        date_str = str(entry.created_at)[:10]
        meta_parts.append(date_str)
    authors = entry.metadata.get("authors")
    if authors:
        authors_str = ", ".join(_format_author(a) for a in authors)
        meta_parts.append(authors_str)
    pr_numbers = _parse_pr_numbers(entry.metadata)
    if pr_numbers:
        prs_str = ", ".join(f"#{pr}" for pr in pr_numbers)
        meta_parts.append(prs_str)
    return Text(" · ".join(meta_parts), style="dim") if meta_parts else Text()


def _build_entry_body(entry: Entry) -> RenderableType:
    """Build the body content for an entry."""
    if entry.body.strip():
        return Markdown(entry.body.strip(), code_theme="ansi_light")
    return Text("No description provided.", style="dim")


def _render_single_entry(
    entry: Entry,
    release_versions: list[str],
    *,
    include_emoji: bool = True,
) -> None:
    """Display a single changelog entry with formatted output."""
    type_color = ENTRY_TYPE_STYLES.get(entry.type, "white")
    title = _build_entry_title(entry, include_emoji=include_emoji)

    # Build metadata section (verbose format for standalone card)
    metadata_parts = []
    metadata_parts.append(f"Entry ID:  [cyan]{entry.entry_id}[/cyan]")
    metadata_parts.append(f"Type:      [{type_color}]{entry.type}[/{type_color}]")
    if entry.components:
        components_display = ", ".join(entry.components)
        metadata_parts.append(f"Components: [green]{components_display}[/green]")

    if entry.created_at:
        metadata_parts.append(f"Created:   {entry.created_at}")

    authors = entry.metadata.get("authors")
    if authors:
        authors_str = ", ".join(_format_author(a) for a in authors)
        metadata_parts.append(f"Authors:   {authors_str}")

    # Include pull-request references when available.
    pr_numbers = _parse_pr_numbers(entry.metadata)
    if pr_numbers:
        prs_str = ", ".join(f"#{pr}" for pr in pr_numbers)
        metadata_parts.append(f"PRs:       {prs_str}")

    # Status: released or unreleased
    if release_versions:
        versions_str = ", ".join(release_versions)
        metadata_parts.append(f"Status:    [green]Released in {versions_str}[/green]")
    else:
        metadata_parts.append("Status:    [yellow]Unreleased[/yellow]")

    metadata_text = Text.from_markup("\n".join(metadata_parts))
    body_content = _build_entry_body(entry)

    # Create a divider that fits inside the panel
    # Panel has 2 characters for borders and 2 for padding (left/right)
    divider_width = max(40, console.width - 4)
    divider = Text("─" * divider_width, style="dim")

    # Combine all sections with dividers
    content = Group(
        metadata_text,
        divider,
        body_content,
    )

    # Display everything in a single panel with the title
    _print_renderable(
        Panel(content, title=title, title_align="left", expand=True, border_style=type_color)
    )


def _render_entries_multi_project(
    entries: list[MultiProjectEntry],
    projects: list[tuple[Path, Config]],
    *,
    include_emoji: bool = True,
) -> None:
    """Render entries from multiple projects with a Project column."""
    if not entries:
        log_info("No entries found across all projects.")
        return

    project_order = {config.id: index for index, (_, config) in enumerate(projects)}

    # Build release index for each project
    release_indices: dict[str, dict[str, list[str]]] = {}
    for project_root, config in projects:
        release_indices[config.id] = build_entry_release_index(project_root, project=config.id)

    # Use the unified layout with project column enabled
    include_component = any(multi.entry.components for multi in entries)
    visible_columns, column_specs = _entries_table_layout(
        console.size.width, include_component, include_project=True
    )

    table_width = max(console.size.width, 40)
    table = Table(show_lines=False, expand=False, width=table_width, pad_edge=False)

    # Add columns using the same logic as _render_entries
    if "num" in visible_columns:
        _add_table_column(
            table, "#", "num", column_specs, style="dim", justify="right", no_wrap_default=True
        )
    if "project" in visible_columns:
        _add_table_column(table, "Project", "project", column_specs, style="cyan")
    if "date" in visible_columns:
        _add_table_column(table, "Date", "date", column_specs, style="yellow", no_wrap_default=True)
    if "version" in visible_columns:
        _add_table_column(table, "Version", "version", column_specs, style="cyan", justify="center")
    if "title" in visible_columns:
        _add_table_column(table, "Title", "title", column_specs, style="bold")
    if "type" in visible_columns:
        _add_table_column(
            table,
            "Type",
            "type",
            column_specs,
            style="magenta",
            justify="center",
            no_wrap_default=True,
        )
    if "component" in visible_columns:
        _add_table_column(
            table, "Component", "component", column_specs, style="green", justify="center"
        )
    if "prs" in visible_columns:
        _add_table_column(table, "PRs", "prs", column_specs, style="yellow", no_wrap_default=True)
    if "authors" in visible_columns:
        _add_table_column(table, "Authors", "authors", column_specs, style="blue")
    if "id" in visible_columns:
        _add_table_column(table, "ID", "id", column_specs, style="cyan", no_wrap_default=True)

    # Sort entries: by project order, then by date descending
    def sort_key(multi: MultiProjectEntry) -> tuple[int, float, str]:
        proj_idx = project_order.get(multi.project_id, 999)
        ts = multi.entry.created_at.timestamp() if multi.entry.created_at else 0
        return (proj_idx, -ts, multi.entry.entry_id)

    sorted_entries = sorted(entries, key=sort_key)

    for row_num, multi in enumerate(sorted_entries, 1):
        entry = multi.entry
        project_id = multi.project_id
        metadata = entry.metadata
        created_display = entry.created_date.isoformat() if entry.created_date else "—"
        type_value = metadata.get("type", "change")
        # Get version from project-specific release index
        proj_release_index = release_indices.get(project_id, {})
        versions = proj_release_index.get(entry.entry_id)
        version_display = ", ".join(versions) if versions else "—"
        if include_emoji:
            glyph = ENTRY_TYPE_EMOJIS.get(type_value, "•")
        else:
            glyph = type_value[:1].upper() if type_value else "?"
        type_display = Text(glyph, style=ENTRY_TYPE_STYLES.get(type_value, ""))

        row: list[RenderableType] = []
        if "num" in visible_columns:
            row.append(str(row_num))
        if "project" in visible_columns:
            row.append(_ellipsis_cell(project_id, "project", column_specs, style="cyan"))
        if "date" in visible_columns:
            row.append(created_display)
        if "version" in visible_columns:
            row.append(version_display)
        if "title" in visible_columns:
            row.append(_ellipsis_cell(metadata.get("title", "Untitled"), "title", column_specs))
        if "type" in visible_columns:
            row.append(type_display)
        if "component" in visible_columns:
            component_value = ", ".join(entry.components) if entry.components else "—"
            row.append(_ellipsis_cell(component_value, "component", column_specs))
        if "prs" in visible_columns:
            pr_numbers = _parse_pr_numbers(metadata)
            pr_display = ", ".join(f"#{pr}" for pr in pr_numbers) if pr_numbers else "—"
            row.append(_ellipsis_cell(pr_display, "prs", column_specs))
        if "authors" in visible_columns:
            row.append(
                _ellipsis_cell(
                    ", ".join(metadata.get("authors") or []) or "—", "authors", column_specs
                )
            )
        if "id" in visible_columns:
            row.append(_ellipsis_cell(entry.entry_id, "id", column_specs, style="cyan"))

        table.add_row(*row)

    _print_renderable(table)


def _render_release_notes(
    entries: list[Entry],
    config: Config,
    *,
    include_emoji: bool = True,
    explicit_links: bool = False,
) -> str:
    """Render Markdown sections for the provided entries."""

    if not entries:
        return ""

    entries_by_type: dict[str, list[Entry]] = {}
    for entry in entries:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        entries_by_type.setdefault(entry_type, []).append(entry)

    lines: list[str] = []
    for type_key in ENTRY_EXPORT_ORDER:
        type_entries = entries_by_type.get(type_key) or []
        if not type_entries:
            continue
        section_title = _format_section_title(type_key, include_emoji)
        lines.append(f"## {section_title}")
        lines.append("")
        for entry in type_entries:
            title = entry.metadata.get("title", "Untitled")
            lines.append(f"### {title}")
            lines.append("")
            body = entry.body.strip()
            if body:
                lines.append(body)
                lines.append("")
            author_line = _format_author_line(entry, config, explicit_links=explicit_links)
            if author_line:
                lines.append(author_line)
                lines.append("")

    if not lines:
        return ""
    raw = "\n".join(lines).strip()
    return normalize_markdown(raw)


def _render_release_notes_compact(
    entries: list[Entry],
    config: Config,
    *,
    include_emoji: bool = True,
    explicit_links: bool = False,
) -> str:
    """Render compact Markdown bullet list for the provided entries."""

    if not entries:
        return ""

    entries_by_type: dict[str, list[Entry]] = {}
    for entry in entries:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        entries_by_type.setdefault(entry_type, []).append(entry)

    lines: list[str] = []
    for type_key in ENTRY_EXPORT_ORDER:
        type_entries = entries_by_type.get(type_key) or []
        if not type_entries:
            continue
        section_title = _format_section_title(type_key, include_emoji)
        lines.append(f"## {section_title}")
        lines.append("")
        for entry in type_entries:
            excerpt = extract_excerpt(entry.body)
            bullet_text = excerpt or entry.metadata.get("title", "Untitled")
            component_labels = entry.components
            if component_labels:
                components_display = ", ".join(component_labels)
                bullet = f"- **{components_display}**: {bullet_text}"
            else:
                bullet = f"- {bullet_text}"
            author_text, pr_text = _collect_author_pr_text(
                entry, config, explicit_links=explicit_links
            )
            suffix_parts: list[str] = []
            if author_text:
                suffix_parts.append(f"by {author_text}")
            if pr_text:
                suffix_parts.append(f"in {pr_text}")
            if suffix_parts:
                bullet = f"{bullet} ({' '.join(suffix_parts)})"
            lines.append(bullet)
        lines.append("")

    if not lines:
        return ""
    raw = "\n".join(lines).strip()
    return normalize_markdown(raw)


def _render_module_entries_compact(
    entries: list[Entry],
    config: Config,
    *,
    include_emoji: bool = True,
    explicit_links: bool = False,
) -> str:
    """Render compact module entries: emoji + title + byline + PR (no body).

    This format is used for module summaries in aggregated release notes,
    showing only the entry title with attribution, prefixed by type emoji.
    """
    if not entries:
        return ""

    # Sort entries by type order, then by title
    def sort_key(entry: Entry) -> tuple[int, str, str]:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        type_order = (
            ENTRY_EXPORT_ORDER.index(entry_type)
            if entry_type in ENTRY_EXPORT_ORDER
            else len(ENTRY_EXPORT_ORDER)
        )
        title = entry.metadata.get("title", "").lower()
        return (type_order, title, entry.entry_id)

    sorted_entries = sorted(entries, key=sort_key)

    lines: list[str] = []
    for entry in sorted_entries:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        title = entry.metadata.get("title", "Untitled")
        emoji = ENTRY_TYPE_EMOJIS.get(entry_type, "•") if include_emoji else ""
        author_text, pr_text = _collect_author_pr_text(entry, config, explicit_links=explicit_links)
        # Build attribution suffix
        suffix_parts: list[str] = []
        if author_text:
            suffix_parts.append(f"*{author_text}*")
        if pr_text:
            suffix_parts.append(f"({pr_text})")
        if suffix_parts:
            attribution = " ".join(suffix_parts)
            bullet = f"- {emoji} {title} — {attribution}" if emoji else f"- {title} — {attribution}"
        else:
            bullet = f"- {emoji} {title}" if emoji else f"- {title}"
        lines.append(bullet)

    if not lines:
        return ""
    raw = "\n".join(lines)
    return normalize_markdown(raw)


def _compose_release_document(
    intro: Optional[str],
    release_notes: str,
) -> str:
    parts: list[str] = []
    if intro:
        intro_text = intro.strip()
        if intro_text:
            parts.append(intro_text)
    notes = release_notes.strip()
    if notes:
        parts.append(notes)
    if not parts:
        return ""
    raw = "\n\n".join(parts)
    return normalize_markdown(raw)


def _release_entry_sort_key(entry: Entry) -> tuple[str, str]:
    title_value = entry.metadata.get("title", "")
    return (title_value.lower(), entry.entry_id)

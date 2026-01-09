"""Stats command for displaying project statistics."""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

import click

from ._core import CLIContext
from ._rendering import create_table
from ..entries import iter_entries
from ..releases import collect_release_entries, iter_release_manifests
from ..utils import console
from ._manifests import _get_latest_release_manifest


def _format_age(days: int) -> str:
    """Format age in compact human-readable units."""
    if days == 0:
        return "today"
    if days == 1:
        return "1 day"
    if days < 7:
        return f"{days} days"
    weeks = days // 7
    if weeks == 1:
        return "1 week"
    if days < 30:
        return f"{weeks} weeks"
    months = days // 30
    if months == 1:
        return "1 month"
    if days < 365:
        return f"{months} months"
    years = days // 365
    if years == 1:
        return "1 year"
    return f"{years} years"


def _collect_project_stats(project_root: Path) -> dict:
    """Collect statistics for a single project/module."""
    # Get latest release info
    latest = _get_latest_release_manifest(project_root)
    if latest:
        last_date = latest.created
        last_str = latest.created.isoformat()
        age_days = (date.today() - latest.created).days
        age_str = _format_age(age_days)
        version_str = latest.version
        latest_entry_count = len(latest.entries)
    else:
        last_date = None
        last_str = None
        age_days = None
        age_str = None
        version_str = None
        latest_entry_count = None

    # Count releases and compute time span/cadence
    releases = list(iter_release_manifests(project_root))
    release_count = len(releases)

    # Find first release and compute time span
    if releases:
        # Sort by date to find first
        sorted_releases = sorted(releases, key=lambda r: r.created)
        first_date = sorted_releases[0].created
        first_str = first_date.isoformat()
        if last_date and first_date != last_date:
            span_days = (last_date - first_date).days
            span_str = _format_age(span_days)
            # Cadence: exponentially weighted releases per month
            # Recent months weighted more heavily (half-life ~2 months)
            by_month = Counter((r.created.year, r.created.month) for r in releases)
            if by_month:
                today = date.today()
                current_month = (today.year, today.month)
                decay = 0.7  # weight multiplier per month back

                weighted_sum = 0.0
                weight_total = 0.0
                for (year, month), count in by_month.items():
                    # Months ago (0 = current month)
                    months_ago = (current_month[0] - year) * 12 + (current_month[1] - month)
                    weight = decay**months_ago
                    weighted_sum += count * weight
                    weight_total += weight

                if weight_total > 0:
                    weighted_avg = weighted_sum / weight_total
                    per_month = round(weighted_avg)
                    per_year = per_month * 12
                    cadence_str = f"{per_month}/mo"
                    cadence_extra = f"{per_year}/yr"
                else:
                    cadence_str = None
                    cadence_extra = None
            else:
                cadence_str = None
                cadence_extra = None
        else:
            span_str = None
            cadence_str = None
            cadence_extra = None
    else:
        first_str = None
        span_str = None
        cadence_str = None
        cadence_extra = None

    # Count released entries by type
    released_entries = collect_release_entries(project_root)
    released_types: Counter[str] = Counter()
    for entry in released_entries.values():
        released_types[entry.type] += 1
    shipped_count = len(released_entries)

    # Count unreleased entries by type
    unreleased_entries = list(iter_entries(project_root))
    unreleased_types: Counter[str] = Counter()
    for entry in unreleased_entries:
        unreleased_types[entry.type] += 1
    unreleased_count = len(unreleased_entries)

    # Combine type counts (all entries)
    all_types = released_types + unreleased_types
    total_entries = shipped_count + unreleased_count

    return {
        "last_date": last_date,
        "last_str": last_str,
        "first_str": first_str,
        "age_days": age_days,
        "age_str": age_str,
        "span_str": span_str,
        "cadence_str": cadence_str,
        "cadence_extra": cadence_extra,
        "version": version_str,
        "latest_entry_count": latest_entry_count,
        "release_count": release_count,
        "shipped_count": shipped_count,
        "unreleased_count": unreleased_count,
        "total_entries": total_entries,
        "types": dict(all_types),
        "released_types": dict(released_types),
        "unreleased_types": dict(unreleased_types),
    }


def _show_stats_table(ctx: CLIContext) -> None:
    """Display project statistics in a table."""
    config = ctx.ensure_config()

    # Display absolute project root
    console.print(f"[dim]Project root:[/dim] {ctx.project_root.resolve()}")
    console.print()

    # Collect all project stats first (for computing max widths)
    projects: list[tuple[str, Path, str]] = [(config.id, ctx.project_root, ".")]
    if config.modules:
        for module in ctx.get_modules():
            projects.append((module.config.id, module.root, module.relative_path))

    all_stats = []
    for pid, root, rel in projects:
        all_stats.append((pid, rel, _collect_project_stats(root)))

    def format_type_cell(count: int) -> str:
        """Format type count, showing dash for zero."""
        if count == 0:
            return "[dim]-[/]"
        return str(count)

    # Borderless table matching vertical view structure
    table = create_table()

    # Block 1: Project (matches vertical Project section)
    table.add_column("📛", style="cyan", no_wrap=True)  # Name/ID
    table.add_column("Path", style="dim", no_wrap=True, max_width=30, overflow="ellipsis")
    table.add_column("🔖", no_wrap=True)  # Version
    table.add_column("📅", justify="right", no_wrap=True)  # Age
    # Block 2: Releases (matches vertical Releases section)
    table.add_column("🔢", justify="right", no_wrap=True)  # Count
    table.add_column("🔄", justify="right", no_wrap=True)  # Cadence
    # Block 3: Entry types (matches vertical Entry Types section)
    table.add_column("💥", justify="right", no_wrap=True)
    table.add_column("🚀", justify="right", no_wrap=True)
    table.add_column("🔧", justify="right", no_wrap=True)
    table.add_column("🐞", justify="right", no_wrap=True)
    # Block 4: Entry status (matches vertical Entry Status section)
    table.add_column("Σ", justify="right", no_wrap=True)
    table.add_column("📦", justify="right", no_wrap=True)
    table.add_column("⏳", justify="right", no_wrap=True)

    for project_id, relative_path, stats in all_stats:
        age_str = stats["age_str"] or "[dim]-[/]"
        version_str = stats["version"] or "[dim]-[/]"
        cadence_str = stats["cadence_str"] or "[dim]-[/]"
        all_types = stats["types"]

        table.add_row(
            project_id,
            relative_path,
            version_str,
            age_str,
            str(stats["release_count"]),
            cadence_str,
            format_type_cell(all_types.get("breaking", 0)),
            format_type_cell(all_types.get("feature", 0)),
            format_type_cell(all_types.get("change", 0)),
            format_type_cell(all_types.get("bugfix", 0)),
            str(stats["total_entries"]),
            str(stats["shipped_count"]),
            str(stats["unreleased_count"]),
        )

    console.print(table)


def _show_stats_vertical(ctx: CLIContext) -> None:
    """Display project statistics in a vertical card layout for single projects."""
    config = ctx.ensure_config()
    stats = _collect_project_stats(ctx.project_root)

    # Build table with sections
    table = create_table(show_header=False)
    table.add_column(no_wrap=True)
    table.add_column(justify="right", no_wrap=True)
    table.add_column(style="dim", no_wrap=True)

    # Section: Project
    version_display = stats["version"] or "[dim]unreleased[/dim]"
    latest_count = stats["latest_entry_count"]
    version_aux = f"{latest_count} entries" if latest_count else ""
    table.add_row("[bold]Project[/]", "", "")
    table.add_row("📛 Name", config.id, str(ctx.project_root.resolve()))
    table.add_row("🔖 Version", version_display, version_aux)
    table.add_row("📅 Age", stats["age_str"] or "-", stats["last_str"] or "")

    # Section: Releases
    table.add_row("", "", "")  # spacer
    table.add_row("[bold]Releases[/]", "", "")
    span_str = f"over {stats['span_str']}" if stats["span_str"] else ""
    table.add_row("🔢 Count", str(stats["release_count"]), span_str)
    if stats["cadence_str"]:
        table.add_row("🔄 Cadence", stats["cadence_str"], stats["cadence_extra"] or "")

    # Section: Entry Types
    table.add_row("", "", "")  # spacer
    table.add_row("[bold]Entry Types[/]", "", "")
    total = stats["total_entries"]
    all_types = stats["types"]
    type_info = [
        ("💥 Breaking", "breaking"),
        ("🚀 Feature", "feature"),
        ("🔧 Change", "change"),
        ("🐞 Bugfix", "bugfix"),
    ]
    for label, type_key in type_info:
        count = all_types.get(type_key, 0)
        if count > 0 and total > 0:
            pct = round(count * 100 / total)
            table.add_row(label, str(count), f"{pct}%")
        elif count > 0:
            table.add_row(label, str(count), "")
        else:
            table.add_row(label, "-", "")

    # Section: Entry Status
    table.add_row("", "", "")  # spacer
    table.add_row("[bold]Entry Status[/]", "", "")
    shipped = stats["shipped_count"]
    unreleased = stats["unreleased_count"]
    shipped_pct = round(shipped * 100 / total) if total > 0 else 0
    unreleased_pct = round(unreleased * 100 / total) if total > 0 else 0
    table.add_row("Σ  Total", str(total), "100%")
    table.add_row("📦 Shipped", str(shipped), f"{shipped_pct}%")
    table.add_row("⏳ Unreleased", str(unreleased), f"{unreleased_pct}%")

    console.print(table)


def _show_stats_json(ctx: CLIContext) -> None:
    """Export project statistics as JSON."""
    import json

    from ..utils import emit_output

    config = ctx.ensure_config()

    def build_project_json(
        project_id: str, project_name: str, project_root: Path, relative_path: str
    ) -> dict:
        s = _collect_project_stats(project_root)
        return {
            "id": project_id,
            "name": project_name,
            "path": relative_path,
            "releases": {
                "count": s["release_count"],
                "last": s["last_str"],
                "age_days": s["age_days"],
                "latest": s["version"],
            },
            "entries": {
                "total": s["total_entries"],
                "shipped": s["shipped_count"],
                "unreleased": s["unreleased_count"],
                **s["types"],
            },
        }

    result = {
        "project_root": str(ctx.project_root.resolve()),
        "parent": build_project_json(config.id, config.name, ctx.project_root, "."),
    }

    # Add modules if configured
    if config.modules:
        modules = []
        for module in ctx.get_modules():
            modules.append(
                build_project_json(
                    module.config.id,
                    module.config.name,
                    module.root,
                    module.relative_path,
                )
            )
        result["modules"] = modules

    emit_output(json.dumps(result, indent=2))


@click.command("stats")
@click.option(
    "--table",
    "force_table",
    is_flag=True,
    help="Force table view even for single projects.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Export statistics as JSON.",
)
@click.pass_context
def stats_cmd(ctx: click.Context, force_table: bool, as_json: bool) -> None:
    """Show project and module statistics.

    By default, displays a vertical card view for single projects and a
    table view for projects with modules. Use --table to force table view
    or --json to export structured data.
    """
    cli_ctx: CLIContext = ctx.obj

    if as_json:
        _show_stats_json(cli_ctx)
    elif force_table or cli_ctx.has_modules():
        _show_stats_table(cli_ctx)
    else:
        _show_stats_vertical(cli_ctx)

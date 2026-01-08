"""Validate and modules commands for the changelog CLI."""

from __future__ import annotations

import click
from rich.table import Table

from ..entries import iter_entries
from ..utils import console, log_error, log_info, log_success
from ..validate import run_validation, run_validation_with_modules
from ._core import CLIContext

__all__ = [
    "run_validate",
    "validate_cmd",
    "modules_cmd",
]


def run_validate(ctx: CLIContext) -> None:
    """Python wrapper for validating changelog files."""

    config = ctx.ensure_config()
    modules = ctx.get_modules()
    if modules:
        issues = run_validation_with_modules(ctx.project_root, config, modules)
    else:
        issues = run_validation(ctx.project_root, config)
    if not issues:
        log_success("all changelog files look good")
        return

    for issue in issues:
        severity_label = issue.severity.lower()
        log_error(f"{severity_label} issue at {issue.path}: {issue.message}")
    raise SystemExit(1)


@click.command("validate")
@click.pass_obj
def validate_cmd(ctx: CLIContext) -> None:
    """Validate entries and release manifests."""

    run_validate(ctx)


@click.command("modules")
@click.pass_obj
def modules_cmd(ctx: CLIContext) -> None:
    """List discovered modules."""

    config = ctx.ensure_config()
    if not config.modules:
        log_info("No modules configured.")
        log_info("Add a 'modules' field to config.yaml with a glob pattern.")
        return

    modules = ctx.get_modules()
    if not modules:
        log_info(f"No modules found matching pattern: {config.modules}")
        return

    table = Table(box=None, padding=(0, 2, 0, 0), show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("NAME")
    table.add_column("PATH", style="dim")
    table.add_column("UNRELEASED", justify="right")

    for module in modules:
        unreleased_count = sum(1 for _ in iter_entries(module.root))
        table.add_row(
            module.config.id,
            module.config.name,
            module.relative_path,
            str(unreleased_count),
        )

    console.print(table)

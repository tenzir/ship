"""Validate command for the changelog CLI."""

from __future__ import annotations

import click

from ..utils import log_error, log_success
from ..validate import run_validation, run_validation_with_modules
from ._core import CLIContext

__all__ = [
    "run_validate",
    "validate_cmd",
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

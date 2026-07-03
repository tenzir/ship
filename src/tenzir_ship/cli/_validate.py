"""Validate command for the changelog CLI."""

from __future__ import annotations

import click

from ..utils import log_error, log_success, log_warning
from ..validate import MISSING_PR_CODE, run_validation, run_validation_with_modules
from ._core import CLIContext

__all__ = [
    "run_validate",
    "validate_cmd",
]


def run_validate(ctx: CLIContext, *, lenient: bool = False) -> None:
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

    error_count = 0
    warning_count = 0
    for issue in issues:
        severity_label = issue.severity.lower()
        if lenient and issue.code == MISSING_PR_CODE:
            severity_label = "warning"
        if severity_label == "warning":
            warning_count += 1
            log_warning(f"{severity_label} issue at {issue.path}: {issue.message}")
        else:
            error_count += 1
            log_error(f"{severity_label} issue at {issue.path}: {issue.message}")
    if error_count:
        raise SystemExit(1)
    log_warning(f"validation passed with {warning_count} warning(s)")


@click.command("validate")
@click.option(
    "--lenient",
    is_flag=True,
    help="Demote missing-PR issues to warnings instead of errors.",
)
@click.pass_obj
def validate_cmd(ctx: CLIContext, lenient: bool) -> None:
    """Validate entries and release manifests."""

    run_validate(ctx, lenient=lenient)

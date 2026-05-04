"""CLI package for tenzir-ship."""

from __future__ import annotations

from ._add import add
from ._core import INFO_PREFIX, _create_cli_group, main
from ._init import init_cmd
from ._release import release_group
from ._show import show_entries
from ._stats import stats_cmd
from ._validate import validate_cmd

cli = _create_cli_group()
cli.add_command(show_entries)
cli.add_command(add)
cli.add_command(init_cmd)
cli.add_command(validate_cmd)
cli.add_command(release_group)
cli.add_command(stats_cmd)

__all__ = ["INFO_PREFIX", "cli", "main"]

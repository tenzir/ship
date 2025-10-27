"""Quality gate runner for tenzir-changelog."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Sequence

from .utils import configure_logging, log_info

_COMMANDS: Sequence[Sequence[str]] = (
    ("ruff", "format", "--check"),
    ("ruff", "check"),
    ("mypy",),
    ("pytest",),
    ("uv", "build"),
)


def _run(command: Sequence[str]) -> None:
    printable = " ".join(shlex.quote(part) for part in command)
    log_info(f"running {printable}")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    configure_logging(debug=False)
    for command in _COMMANDS:
        _run(command)
    wheel_candidates = list(Path("dist").glob("*.whl"))
    if not wheel_candidates:
        raise SystemExit("uv build did not produce a wheel in dist/")
    wheel_path = max(wheel_candidates, key=lambda path: path.stat().st_mtime)
    _run(
        (
            "uvx",
            "--no-cache",
            "--from",
            str(wheel_path),
            "tenzir-changelog",
            "--version",
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

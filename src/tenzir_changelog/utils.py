"""Shared utilities for the CLI implementation."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from collections.abc import Iterable as IterableABC
from typing import Iterable, Mapping, Optional, cast, NoReturn

import mdformat
import click
from rich.console import Console, RenderableType
from rich.style import Style
from rich.theme import Theme

CHECKMARK = "\033[92;1m✔\033[0m"
CROSS = "\033[31m✘\033[0m"
INFO = "\033[94;1mi\033[0m"
WARNING = "○"
DEBUG_PREFIX = "\033[95m◆\033[0m"

CHECKMARK_PREFIX = f"{CHECKMARK} "
CROSS_PREFIX = f"{CROSS} "
INFO_PREFIX = f"{INFO} "
WARNING_PREFIX = f"{WARNING} "
DEBUG_PREFIX_WITH_SPACE = f"{DEBUG_PREFIX} "
BOLD = "\033[1m"
RESET = "\033[0m"

_LOGGER_NAME = "tenzir_changelog"
_LOGGER = logging.getLogger(_LOGGER_NAME)

console = Console(
    stderr=True,
    theme=Theme(
        {
            "markdown.code": Style(bold=True, color="cyan"),
            "markdown.code_block": Style(color="cyan"),
        }
    ),
)


def configure_logging(debug: bool = False) -> logging.Logger:
    """Configure the shared logger used across the CLI."""
    level = logging.DEBUG if debug else logging.INFO
    _LOGGER.setLevel(level)
    while _LOGGER.handlers:
        handler = _LOGGER.handlers.pop()
        handler.close()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(level)
    _LOGGER.addHandler(handler)
    _LOGGER.propagate = False
    return _LOGGER


def _log(prefix: str, message: str, level: int) -> None:
    logger = logging.getLogger(_LOGGER_NAME)
    lines = message.splitlines() or [""]
    for line in lines:
        if line:
            logger.log(level, f"{prefix}{line}")
        else:
            logger.log(level, prefix.rstrip())


def log_info(message: str) -> None:
    """Log an informational message with the standardized prefix."""
    _log(INFO_PREFIX, message, logging.INFO)


def log_success(message: str) -> None:
    """Log a success message with the standardized prefix."""
    _log(CHECKMARK_PREFIX, message, logging.INFO)


def log_error(message: str) -> None:
    """Log an error message with the standardized prefix."""
    _log(CROSS_PREFIX, message, logging.ERROR)


def log_warning(message: str) -> None:
    """Log a warning message with the standardized prefix."""
    _log(WARNING_PREFIX, message, logging.WARNING)


def log_debug(message: str) -> None:
    """Log a debug message with the standardized prefix."""
    _log(DEBUG_PREFIX_WITH_SPACE, message, logging.DEBUG)


def abort_on_user_interrupt(exc: BaseException | None = None) -> NoReturn:
    """Log a standardized cancellation message and exit the command."""

    log_error("operation cancelled by user (Ctrl+C).")
    raise click.exceptions.Exit(130) from exc


def format_bold(text: str) -> str:
    """Return text wrapped in ANSI bold styling."""
    return f"{BOLD}{text}{RESET}"


def render_to_text(renderable: RenderableType) -> str:
    """Return the string representation of a Rich renderable."""
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()


def emit_output(content: str, *, newline: bool = True) -> None:
    """Emit raw command output to stdout for machine consumption."""
    click.echo(content, nl=newline, err=False)


def coerce_date(value: object) -> Optional[date]:
    """Return a date object for ISO-like inputs, preserving None."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def coerce_datetime(value: object) -> Optional[datetime]:
    """Return a UTC-aware datetime object for ISO-like inputs, preserving None.

    Accepts datetime objects, date objects (converted to midnight UTC),
    and ISO-formatted strings (with or without time component).
    All returned datetimes are timezone-aware (UTC).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    # Try parsing as date-only and convert to midnight UTC
    try:
        d = date.fromisoformat(text)
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    except ValueError:
        return None


def guess_git_remote(project_root: Path) -> Optional[str]:
    """Return the GitHub repository slug (owner/name) if available."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(project_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    url = result.stdout.strip()
    if not url:
        return None
    url = url.replace(".git", "")
    if url.startswith("git@"):
        _, _, remainder = url.partition(":")
        return remainder
    if url.startswith("https://"):
        remainder = url[len("https://") :]
        # Remove domain
        parts = remainder.split("/", 1)
        if len(parts) == 2:
            return parts[1]
    return url


def slugify(value: str) -> str:
    """Generate a safe slug for filesystem or identifier usage."""
    safe_chars = []
    for char in value.lower():
        if char.isalnum():
            safe_chars.append(char)
        elif char in {" ", "-", "_"}:
            safe_chars.append("-")
    slug = "".join(safe_chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "project"


_GH_LOGIN_ENV_KEYS = (
    "TENZIR_CHANGELOG_AUTHOR",
    "GH_USERNAME",
    "GH_USER",
    "GITHUB_ACTOR",
    "GITHUB_USER",
)
_GH_PR_ENV_KEYS = (
    "GH_PR_NUMBER",
    "GITHUB_PR_NUMBER",
    "PR_NUMBER",
)


def _find_gh_executable(env: Mapping[str, str] | None) -> Optional[str]:
    """Return the path to the gh CLI using the provided environment PATH."""
    path_env = None
    if env is not None:
        path_env = env.get("PATH")
    return shutil.which("gh", path=path_env)


def detect_github_login(
    *,
    env: Mapping[str, str] | None = None,
    log_success: bool = True,
) -> Optional[str]:
    """Return an authenticated GitHub login via environment or the gh CLI."""

    env_mapping = env if env is not None else os.environ
    for key in _GH_LOGIN_ENV_KEYS:
        value = env_mapping.get(key)
        if value:
            stripped = value.strip()
            if stripped:
                if log_success:
                    log_info(
                        f"detected GitHub login {format_bold(stripped)} from environment key {key}."
                    )
                else:
                    log_debug(f"detected GitHub login '{stripped}' from environment key {key}.")
                return stripped

    gh_path = _find_gh_executable(env_mapping)
    if gh_path is None:
        log_debug("gh CLI not found, skipping GitHub login detection.")
        return None

    subprocess_env = dict(env_mapping) if env is not None else None
    try:
        result = subprocess.run(
            [gh_path, "api", "user", "--cache", "1m", "--jq", ".login"],
            check=True,
            capture_output=True,
            text=True,
            env=subprocess_env,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        log_debug(f"gh CLI failed to report login: {exc}")
        return None

    login = result.stdout.strip()
    if login:
        if log_success:
            log_info(f"detected GitHub login {format_bold(login)} via gh CLI.")
        else:
            log_debug(f"detected GitHub login '{login}' via gh CLI.")
        return login
    return None


def detect_github_pr_number(
    project_root: Path,
    *,
    env: Mapping[str, str] | None = None,
    log_success: bool = True,
) -> Optional[int]:
    """Return the pull request number for the current branch, if any."""

    env_mapping = env if env is not None else os.environ
    for key in _GH_PR_ENV_KEYS:
        value = env_mapping.get(key)
        if value:
            stripped = value.strip()
            if stripped.isdigit():
                if log_success:
                    log_info(
                        f"detected open pull request {format_bold(f'#{stripped}')} "
                        f"from environment key {key}."
                    )
                else:
                    log_debug(f"detected PR #{stripped} from environment key {key}.")
                return int(stripped)

    gh_path = _find_gh_executable(env_mapping)
    if gh_path is None:
        log_debug("gh CLI not found, skipping PR detection.")
        return None

    subprocess_env = dict(env_mapping) if env is not None else None
    try:
        result = subprocess.run(
            [gh_path, "pr", "view", "--json", "number", "--jq", ".number"],
            cwd=str(project_root),
            check=True,
            capture_output=True,
            text=True,
            env=subprocess_env,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        log_debug(f"gh CLI failed to detect PR for current branch: {exc}")
        return None

    text = result.stdout.strip()
    if not text or not text.isdigit():
        return None
    number = int(text)
    if number <= 0:
        return None
    if log_success:
        log_info(f"detected open pull request {format_bold(f'#{number}')} via gh CLI.")
    else:
        log_debug(f"detected PR #{number} via gh CLI.")
    return number


def normalize_string_choices(values: object | None) -> tuple[str, ...]:
    """Return a tuple of distinct, stripped strings from user-provided config values."""
    if values is None:
        return ()
    if isinstance(values, str):
        candidate = values.strip()
        return (candidate,) if candidate else ()
    normalized: list[str] = []
    if isinstance(values, IterableABC):
        candidates = cast(Iterable[object], values)
    else:
        candidate = str(values).strip()
        return (candidate,) if candidate else ()
    for item in candidates:
        text = str(item).strip()
        if not text or text in normalized:
            continue
        normalized.append(text)
    return tuple(normalized)


def parse_components(values: object | None) -> dict[str, str]:
    """Parse components from config, supporting both list and dict formats.

    Accepts:
      - A list of strings: ["cli", "python"] -> {"cli": "", "python": ""}
      - A dict mapping names to descriptions: {cli: "desc"} -> {"cli": "desc"}
      - A single string: "cli" -> {"cli": ""}
      - None: -> {}
    """
    if values is None:
        return {}
    if isinstance(values, Mapping):
        result: dict[str, str] = {}
        for key, value in values.items():
            name = str(key).strip()
            if not name:
                continue
            desc = str(value).strip() if value else ""
            result[name] = desc
        return result
    # Fall back to list-style parsing
    names = normalize_string_choices(values)
    return {name: "" for name in names}


def extract_excerpt(text: str) -> str:
    """Return the first paragraph of a Markdown body as a single line."""
    stripped = text.strip()
    if not stripped:
        return ""
    first_paragraph, *_ = re.split(r"\n\s*\n", stripped, maxsplit=1)
    collapsed = re.sub(r"\s*\n\s*", " ", first_paragraph.strip())
    return collapsed.strip()


def normalize_markdown(text: str) -> str:
    """Return Markdown with paragraphs normalized to single lines."""
    if not text.strip():
        return ""
    formatted = mdformat.text(text, options={"wrap": "no"})
    return formatted.rstrip("\n")


def create_annotated_git_tag(project_root: Path, tag_name: str, message: str) -> bool:
    """Create an annotated Git tag for the provided version.

    Returns True when a new tag was created, False if the tag already existed.
    """
    try:
        result = subprocess.run(
            ["git", "tag", "--list", tag_name],
            cwd=str(project_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "git is required to create release tags but was not found in PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("failed to query existing git tags.") from exc

    existing_tags = {line.strip() for line in result.stdout.splitlines()}
    if tag_name in existing_tags:
        return False

    try:
        subprocess.run(
            ["git", "tag", "-a", tag_name, "-m", message],
            cwd=str(project_root),
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git failed to create tag '{tag_name}' (exit status {exc.returncode})."
        ) from exc
    return True


def has_staged_changes(project_root: Path) -> bool:
    """Check if there are staged changes to commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(project_root),
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "git is required to check for staged changes but was not found in PATH."
        ) from exc
    return result.returncode != 0


def create_git_commit(project_root: Path, message: str) -> None:
    """Create a git commit with the given message."""
    try:
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(project_root),
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git is required to create commits but was not found in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git failed to create commit (exit status {exc.returncode}).") from exc


def _select_remote_name(project_root: Path, repository: str | None) -> str:
    """Return the git remote name matching the configured repository."""
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=str(project_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "git is required to push release tags but was not found in PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("failed to list git remotes.") from exc

    remotes: dict[str, list[str]] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name, url, _kind = parts[0], parts[1], parts[2]
        remotes.setdefault(name, []).append(url)

    if not remotes:
        raise RuntimeError("no git remotes configured; cannot push release tags.")

    if repository:
        for remote_name, urls in remotes.items():
            for url in urls:
                if repository in url:
                    return remote_name

    if "origin" in remotes:
        return "origin"

    # Fallback to first configured remote for completeness.
    return next(iter(remotes))


def _current_branch(project_root: Path) -> Optional[str]:
    """Return the current branch name if HEAD is not detached."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(project_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    branch = result.stdout.strip()
    if not branch or branch == "HEAD":
        return None
    return branch


def _upstream_branch(project_root: Path) -> Optional[tuple[str, str]]:
    """Return the configured upstream as (remote, branch)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=str(project_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    upstream = result.stdout.strip()
    if not upstream or "/" not in upstream:
        return None
    remote_name, _, branch_name = upstream.partition("/")
    if not remote_name or not branch_name:
        return None
    return remote_name, branch_name


def push_current_branch(project_root: Path, repository: str | None = None) -> tuple[str, str, str]:
    """Push the current branch to its upstream (or configured) remote."""
    branch = _current_branch(project_root)
    if not branch:
        raise RuntimeError(
            "cannot push the current branch because HEAD is detached. "
            "check out a branch before publishing the release."
        )

    upstream = _upstream_branch(project_root)
    if upstream:
        remote_name, remote_branch = upstream
    else:
        remote_name = _select_remote_name(project_root, repository)
        remote_branch = branch

    try:
        subprocess.run(
            ["git", "push", remote_name, f"{branch}:{remote_branch}"],
            cwd=str(project_root),
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "git failed to push branch "
            f"'{branch}' to remote '{remote_name}/{remote_branch}' "
            f"(exit status {exc.returncode})."
        ) from exc
    return remote_name, remote_branch, branch


def push_git_tag(project_root: Path, tag_name: str, repository: str | None = None) -> str:
    """Push the provided git tag to the matching remote and return the remote name."""
    remote_name = _select_remote_name(project_root, repository)
    try:
        subprocess.run(
            ["git", "push", remote_name, tag_name],
            cwd=str(project_root),
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "git failed to push tag "
            f"'{tag_name}' to remote '{remote_name}' "
            f"(exit status {exc.returncode})."
        ) from exc
    return remote_name

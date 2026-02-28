"""Helpers for planning and applying package-manager version file updates."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

import click

SUPPORTED_AUTO_VERSION_FILES: tuple[str, ...] = (
    "package.json",
    "pyproject.toml",
    "project.toml",
    "Cargo.toml",
)

_TABLE_PATTERN = re.compile(r"^\s*\[(?P<table>[^\]]+)\]\s*(?:#.*)?$")
_VERSION_ASSIGNMENT_PATTERN = re.compile(
    r'^(?P<prefix>\s*version\s*=\s*)(?P<quote>["\'])(?P<value>[^"\']*)(?P=quote)'
    r"(?P<suffix>\s*(?:#.*)?)(?P<newline>\r?\n?)$"
)


@dataclass(frozen=True)
class VersionFileUpdate:
    """In-memory representation of one file update."""

    path: Path
    old_version: str | None
    new_version: str
    content: str


@dataclass(frozen=True)
class _TomlUpdateResult:
    """Result of searching for a version assignment in one TOML table."""

    found_table: bool
    found_version: bool
    old_version: str | None
    changed: bool
    content: str


@dataclass(frozen=True)
class _ResolvedVersionFileTarget:
    """Resolved version file target along with how it was configured."""

    path: Path
    explicit: bool


def _strip_release_prefix(version: str) -> str:
    """Convert release labels like v1.2.3 into package-manager version strings."""

    if version.startswith(("v", "V")):
        return version[1:]
    return version


def _resolve_explicit_version_file_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (project_root / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        raise click.ClickException(f"Configured version file does not exist: {path}")
    if not path.is_file():
        raise click.ClickException(f"Configured version file is not a file: {path}")
    return path


def _auto_search_roots(project_root: Path) -> list[Path]:
    roots = [project_root.resolve()]
    if project_root.name == "changelog":
        roots.append(project_root.parent.resolve())
    return roots


def resolve_version_file_targets(project_root: Path, explicit_paths: Sequence[str]) -> list[Path]:
    """Resolve auto-detected and configured version file paths in deterministic order."""

    candidates = _resolve_version_file_targets(project_root, explicit_paths)
    return [candidate.path for candidate in candidates]


def _resolve_version_file_targets(
    project_root: Path, explicit_paths: Sequence[str]
) -> list[_ResolvedVersionFileTarget]:
    candidates: list[_ResolvedVersionFileTarget] = []
    for root in _auto_search_roots(project_root):
        for filename in SUPPORTED_AUTO_VERSION_FILES:
            candidate = root / filename
            if candidate.is_file():
                candidates.append(_ResolvedVersionFileTarget(path=candidate.resolve(), explicit=False))

    for raw_path in explicit_paths:
        candidates.append(
            _ResolvedVersionFileTarget(
                path=_resolve_explicit_version_file_path(project_root, raw_path),
                explicit=True,
            )
        )

    deduped: list[_ResolvedVersionFileTarget] = []
    seen: dict[Path, int] = {}
    for candidate in candidates:
        existing_index = seen.get(candidate.path)
        if existing_index is not None:
            if candidate.explicit and not deduped[existing_index].explicit:
                deduped[existing_index] = _ResolvedVersionFileTarget(
                    path=candidate.path,
                    explicit=True,
                )
            continue
        seen[candidate.path] = len(deduped)
        deduped.append(candidate)
    return deduped


def _replace_toml_table_version(content: str, table_name: str, new_version: str) -> _TomlUpdateResult:
    lines = content.splitlines(keepends=True)
    active = False
    found_table = False
    found_version = False
    changed = False
    old_version: str | None = None

    for index, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        table_match = _TABLE_PATTERN.match(stripped)
        if table_match:
            current_table = table_match.group("table").strip()
            if current_table == table_name:
                active = True
                found_table = True
            elif active:
                active = False
            continue

        if not active or found_version:
            continue

        version_match = _VERSION_ASSIGNMENT_PATTERN.match(line)
        if version_match is None:
            continue

        found_version = True
        old_version = version_match.group("value")
        if old_version != new_version:
            changed = True
            lines[index] = (
                f"{version_match.group('prefix')}"
                f"{version_match.group('quote')}{new_version}{version_match.group('quote')}"
                f"{version_match.group('suffix')}{version_match.group('newline')}"
            )
        break

    return _TomlUpdateResult(
        found_table=found_table,
        found_version=found_version,
        old_version=old_version,
        changed=changed,
        content="".join(lines),
    )


def _update_package_json(path: Path, content: str, new_version: str) -> tuple[str, str | None]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Cannot parse JSON in {path}: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise click.ClickException(f"Expected a JSON object in {path}.")

    old_value = parsed.get("version")
    if old_value is not None and not isinstance(old_value, str):
        raise click.ClickException(
            f"Expected 'version' in {path} to be a string, got {type(old_value).__name__}."
        )
    old_version = old_value if isinstance(old_value, str) else None
    parsed["version"] = new_version
    return json.dumps(parsed, indent=2, ensure_ascii=False) + "\n", old_version


def _update_pyproject_like(
    path: Path,
    content: str,
    new_version: str,
    *,
    skip_if_missing_static_version: bool,
) -> tuple[str, str | None]:
    project_update = _replace_toml_table_version(content, "project", new_version)
    if project_update.found_table:
        if project_update.found_version:
            return project_update.content, project_update.old_version

    poetry_update = _replace_toml_table_version(content, "tool.poetry", new_version)
    if poetry_update.found_table:
        if poetry_update.found_version:
            return poetry_update.content, poetry_update.old_version

    if skip_if_missing_static_version:
        return content, None

    if project_update.found_table:
        raise click.ClickException(
            f"{path} has a [project] table but no static 'version' field."
        )
    if poetry_update.found_table:
        raise click.ClickException(
            f"{path} has a [tool.poetry] table but no static 'version' field."
        )

    raise click.ClickException(
        f"{path} is missing [project] and [tool.poetry] tables with a static 'version' field."
    )


def _update_cargo_toml(
    path: Path,
    content: str,
    new_version: str,
    *,
    skip_if_missing_static_version: bool,
) -> tuple[str, str | None]:
    package_update = _replace_toml_table_version(content, "package", new_version)
    if package_update.found_table:
        if package_update.found_version:
            return package_update.content, package_update.old_version
        if skip_if_missing_static_version:
            return content, None
        raise click.ClickException(f"{path} has a [package] table but no static 'version' field.")

    workspace_package_update = _replace_toml_table_version(content, "workspace.package", new_version)
    if workspace_package_update.found_table:
        if workspace_package_update.found_version:
            return workspace_package_update.content, workspace_package_update.old_version
        if skip_if_missing_static_version:
            return content, None
        raise click.ClickException(
            f"{path} has a [workspace.package] table but no static 'version' field."
        )

    if skip_if_missing_static_version:
        return content, None
    raise click.ClickException(f"{path} is missing a [package] table.")


def _version_file_kind(path: Path) -> Literal["package_json", "pyproject", "cargo"]:
    name = path.name
    lowered = name.lower()
    if lowered == "package.json":
        return "package_json"
    if lowered in {"pyproject.toml", "project.toml"}:
        return "pyproject"
    if name == "Cargo.toml":
        return "cargo"
    if lowered == "cargo.toml":
        return "cargo"
    raise click.ClickException(
        "Unsupported version file "
        f"{path}. Supported filenames: {', '.join(SUPPORTED_AUTO_VERSION_FILES)}."
    )


def _plan_single_version_file_update(
    path: Path,
    release_version: str,
    *,
    strict: bool,
) -> VersionFileUpdate | None:
    content = path.read_text(encoding="utf-8")
    new_version = _strip_release_prefix(release_version)
    kind = _version_file_kind(path)

    if kind == "package_json":
        updated_content, old_version = _update_package_json(path, content, new_version)
    elif kind == "pyproject":
        updated_content, old_version = _update_pyproject_like(
            path,
            content,
            new_version,
            skip_if_missing_static_version=not strict,
        )
    else:
        updated_content, old_version = _update_cargo_toml(
            path,
            content,
            new_version,
            skip_if_missing_static_version=not strict,
        )

    if updated_content == content:
        return None
    return VersionFileUpdate(
        path=path,
        old_version=old_version,
        new_version=new_version,
        content=updated_content,
    )


def plan_version_file_updates(
    project_root: Path,
    release_version: str,
    *,
    bump_mode: str,
    explicit_paths: Sequence[str],
) -> list[VersionFileUpdate]:
    """Plan version updates for discovered or configured files."""

    normalized_mode = bump_mode.strip().lower()
    if normalized_mode == "off":
        return []
    if normalized_mode != "auto":
        raise click.ClickException(
            f"Unknown release.version_bump_mode '{bump_mode}'. Supported values: auto, off."
        )

    targets = _resolve_version_file_targets(project_root, explicit_paths)
    updates: list[VersionFileUpdate] = []
    for target in targets:
        update = _plan_single_version_file_update(
            target.path,
            release_version,
            strict=target.explicit,
        )
        if update is not None:
            updates.append(update)
    return updates


def apply_version_file_updates(updates: Sequence[VersionFileUpdate]) -> None:
    """Write planned version file updates to disk."""

    for update in updates:
        update.path.write_text(update.content, encoding="utf-8")

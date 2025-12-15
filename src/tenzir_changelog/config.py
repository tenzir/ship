"""Configuration helpers for tenzir-changelog."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, MutableMapping, cast

import yaml

from .utils import normalize_string_choices, parse_components

ExportStyle = Literal["standard", "compact"]
CONFIG_RELATIVE_PATH = Path("config.yaml")
PACKAGE_METADATA_FILENAME = "package.yaml"
CHANGELOG_DIRECTORY_NAME = "changelog"

EXPORT_STYLE_STANDARD: ExportStyle = "standard"
EXPORT_STYLE_COMPACT: ExportStyle = "compact"
EXPORT_STYLE_CHOICES: tuple[ExportStyle, ...] = (
    EXPORT_STYLE_STANDARD,
    EXPORT_STYLE_COMPACT,
)


def default_config_path(project_root: Path) -> Path:
    """Return the default config path for a project root."""
    return project_root / CONFIG_RELATIVE_PATH


def package_metadata_path(project_root: Path) -> Path:
    """Return the expected package metadata path for a project root."""

    return project_root.parent / PACKAGE_METADATA_FILENAME


@dataclass
class Config:
    """Structured representation of the changelog config."""

    id: str
    name: str
    description: str = ""
    repository: str | None = None
    export_style: ExportStyle = EXPORT_STYLE_STANDARD
    components: dict[str, str] = field(default_factory=dict)
    modules: str | None = None  # glob pattern for nested changelog projects


def load_config(path: Path) -> Config:
    """Load the configuration from disk."""
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, MutableMapping):
        raise ValueError("Config root must be a mapping")

    project_value_raw = raw.get("id", raw.get("project"))
    if isinstance(project_value_raw, str):
        project_value = project_value_raw.strip()
    else:
        project_value = str(raw.get("project_name", raw.get("product", "")) or "").strip()
    if not project_value:
        raise ValueError("Config missing 'id'")

    name_raw = raw.get("name", project_value)
    description_raw = raw.get("description", "")
    repository_raw = raw.get("repository")
    export_style_raw = raw.get("export_style")
    export_style: ExportStyle = EXPORT_STYLE_STANDARD
    if export_style_raw is not None:
        if not isinstance(export_style_raw, str):
            raise ValueError("Config option 'export_style' must be a string.")
        normalized_export_style = export_style_raw.strip().lower()
        if normalized_export_style not in EXPORT_STYLE_CHOICES:
            allowed = ", ".join(EXPORT_STYLE_CHOICES)
            raise ValueError(f"Config option 'export_style' must be one of: {allowed}")
        export_style = cast(ExportStyle, normalized_export_style)

    components = parse_components(raw.get("components"))
    modules_raw = raw.get("modules")
    modules = str(modules_raw).strip() if modules_raw else None

    return Config(
        id=project_value,
        name=str(name_raw or "Unnamed Project"),
        description=str(description_raw or ""),
        repository=(str(repository_raw) if repository_raw else None),
        export_style=export_style,
        components=components,
        modules=modules,
    )


def load_package_config(path: Path) -> Config:
    """Load configuration metadata from a package manifest."""

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, MutableMapping):
        raise ValueError("Package metadata must be a mapping")

    package_id = str(raw.get("id", "")).strip()
    if not package_id:
        raise ValueError(f"Package metadata at {path} missing required 'id'")

    package_name = str(raw.get("name", "")).strip()
    if not package_name:
        raise ValueError(f"Package metadata at {path} missing required 'name'")

    description_raw = raw.get("description", "")
    repository_raw = raw.get("repository")
    export_style_raw = raw.get("export_style")
    export_style: ExportStyle = EXPORT_STYLE_STANDARD
    if export_style_raw is not None:
        if not isinstance(export_style_raw, str):
            raise ValueError("Package metadata option 'export_style' must be a string.")
        normalized_export_style = export_style_raw.strip().lower()
        if normalized_export_style not in EXPORT_STYLE_CHOICES:
            allowed = ", ".join(EXPORT_STYLE_CHOICES)
            raise ValueError(f"Package metadata option 'export_style' must be one of: {allowed}")
        export_style = cast(ExportStyle, normalized_export_style)

    components = parse_components(raw.get("components"))
    modules_raw = raw.get("modules")
    modules = str(modules_raw).strip() if modules_raw else None

    return Config(
        id=package_id,
        name=package_name,
        description=str(description_raw or ""),
        repository=(str(repository_raw) if repository_raw else None),
        export_style=export_style,
        components=components,
        modules=modules,
    )


def load_project_config(project_root: Path) -> Config:
    """Load a project config, falling back to package metadata when needed."""

    config_path = default_config_path(project_root)
    if config_path.exists():
        return load_config(config_path)

    package_path = package_metadata_path(project_root)
    if package_path.exists():
        return load_package_config(package_path)

    raise FileNotFoundError(
        f"No config found at {config_path} and no package metadata at {package_path}."
    )


def dump_config(config: Config) -> dict[str, Any]:
    """Convert a Config into a plain dictionary suitable for YAML output."""
    data: dict[str, Any] = {
        "id": config.id,
        "name": config.name,
    }
    if config.description:
        data["description"] = config.description
    if config.repository:
        data["repository"] = config.repository
    if config.export_style != EXPORT_STYLE_STANDARD:
        data["export_style"] = config.export_style
    if config.components:
        data["components"] = dict(config.components)
    if config.modules:
        data["modules"] = config.modules
    return data


def save_config(config: Config, path: Path) -> None:
    """Write the configuration to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(dump_config(config), handle, sort_keys=False)


def load_configs(roots: list[Path]) -> list[tuple[Path, Config]]:
    """Load configurations from multiple project roots.

    Returns a list of tuples containing (project_root, config) for each root.
    Raises an error if any root doesn't have a valid config.
    """
    result: list[tuple[Path, Config]] = []
    seen_roots: set[Path] = set()

    for root in roots:
        resolved_root = root.resolve()
        if resolved_root in seen_roots:
            raise ValueError(f"Duplicate root specified: {root}")
        seen_roots.add(resolved_root)

        try:
            config = load_project_config(resolved_root)
        except FileNotFoundError as error:
            raise ValueError(
                f"No changelog configuration found for {resolved_root}. "
                "Provide a config.yaml or package.yaml."
            ) from error
        result.append((resolved_root, config))

    # Warn about name collisions
    names = [cfg.name for _, cfg in result]
    if len(names) != len(set(names)):
        from collections import Counter

        duplicates = [name for name, count in Counter(names).items() if count > 1]
        from .utils import log_warning

        log_warning(f"Multiple projects share the same name: {', '.join(duplicates)}")

    return result

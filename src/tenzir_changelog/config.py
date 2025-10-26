"""Configuration helpers for tenzir-changelog."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, MutableMapping, cast

import yaml

from .utils import normalize_string_choices

ExportStyle = Literal["standard", "compact"]
CONFIG_RELATIVE_PATH = Path("config.yaml")

EXPORT_STYLE_STANDARD: ExportStyle = "standard"
EXPORT_STYLE_COMPACT: ExportStyle = "compact"
EXPORT_STYLE_CHOICES: tuple[ExportStyle, ...] = (
    EXPORT_STYLE_STANDARD,
    EXPORT_STYLE_COMPACT,
)


def default_config_path(project_root: Path) -> Path:
    """Return the default config path for a project root."""
    return project_root / CONFIG_RELATIVE_PATH


@dataclass
class Config:
    """Structured representation of the changelog config."""

    id: str
    name: str
    description: str = ""
    repository: str | None = None
    intro_template: str | None = None
    assets_dir: str | None = None
    export_style: ExportStyle = EXPORT_STYLE_STANDARD
    components: tuple[str, ...] = ()


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

    components = normalize_string_choices(raw.get("components"))

    return Config(
        id=project_value,
        name=str(name_raw or "Unnamed Project"),
        description=str(description_raw or ""),
        repository=(str(repository_raw) if repository_raw else None),
        intro_template=(str(raw["intro_template"]) if raw.get("intro_template") else None),
        assets_dir=str(raw["assets_dir"]) if raw.get("assets_dir") else None,
        export_style=export_style,
        components=components,
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
    if config.intro_template:
        data["intro_template"] = config.intro_template
    if config.assets_dir:
        data["assets_dir"] = config.assets_dir
    if config.export_style != EXPORT_STYLE_STANDARD:
        data["export_style"] = config.export_style
    if config.components:
        data["components"] = list(config.components)
    return data


def save_config(config: Config, path: Path) -> None:
    """Write the configuration to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(dump_config(config), handle, sort_keys=False)

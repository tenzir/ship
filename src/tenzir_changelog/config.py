"""Configuration helpers for tenzir-changelog."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping

import yaml

CONFIG_RELATIVE_PATH = Path("config.yaml")


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

    workspace_raw = raw.get("workspace")
    fallback_mapping: Mapping[str, Any] = (
        workspace_raw if isinstance(workspace_raw, Mapping) else {}
    )
    name_raw = raw.get("name", fallback_mapping.get("name", project_value))
    description_raw = raw.get("description", fallback_mapping.get("description", ""))
    repository_raw = raw.get("repository", fallback_mapping.get("repository"))

    return Config(
        id=project_value,
        name=str(name_raw or "Unnamed Project"),
        description=str(description_raw or ""),
        repository=(str(repository_raw) if repository_raw else None),
        intro_template=(str(raw["intro_template"]) if raw.get("intro_template") else None),
        assets_dir=str(raw["assets_dir"]) if raw.get("assets_dir") else None,
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
    return data


def save_config(config: Config, path: Path) -> None:
    """Write the configuration to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(dump_config(config), handle, sort_keys=False)

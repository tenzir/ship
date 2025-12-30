"""Configuration helpers for tenzir-changelog."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, MutableMapping, cast

import yaml

from .utils import parse_components

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
class ReleaseConfig:
    """Configuration for release operations."""

    commit_message: str = "Release {version}"


@dataclass
class Config:
    """Structured representation of the changelog config."""

    id: str
    name: str
    description: str = ""
    repository: str | None = None
    export_style: ExportStyle = EXPORT_STYLE_STANDARD
    explicit_links: bool = False
    omit_pr: bool = False
    omit_author: bool = False
    components: dict[str, str] = field(default_factory=dict)
    modules: str | None = None  # glob pattern for nested changelog projects
    release: ReleaseConfig = field(default_factory=ReleaseConfig)


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

    explicit_links_raw = raw.get("explicit_links")
    explicit_links = False
    if explicit_links_raw is not None:
        if not isinstance(explicit_links_raw, bool):
            raise ValueError("Config option 'explicit_links' must be a boolean.")
        explicit_links = explicit_links_raw

    omit_pr_raw = raw.get("omit_pr")
    omit_pr = False
    if omit_pr_raw is not None:
        if not isinstance(omit_pr_raw, bool):
            raise ValueError("Config option 'omit_pr' must be a boolean.")
        omit_pr = omit_pr_raw

    omit_author_raw = raw.get("omit_author")
    omit_author = False
    if omit_author_raw is not None:
        if not isinstance(omit_author_raw, bool):
            raise ValueError("Config option 'omit_author' must be a boolean.")
        omit_author = omit_author_raw

    components = parse_components(raw.get("components"))
    modules_raw = raw.get("modules")
    modules = str(modules_raw).strip() if modules_raw else None

    # Parse release config
    release_config = ReleaseConfig()
    release_raw = raw.get("release")
    if release_raw is not None:
        if not isinstance(release_raw, MutableMapping):
            raise ValueError("Config option 'release' must be a mapping.")
        commit_message = release_raw.get("commit_message")
        if commit_message is not None:
            release_config = ReleaseConfig(commit_message=str(commit_message))

    return Config(
        id=project_value,
        name=str(name_raw or "Unnamed Project"),
        description=str(description_raw or ""),
        repository=(str(repository_raw) if repository_raw else None),
        export_style=export_style,
        explicit_links=explicit_links,
        omit_pr=omit_pr,
        omit_author=omit_author,
        components=components,
        modules=modules,
        release=release_config,
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

    explicit_links_raw = raw.get("explicit_links")
    explicit_links = False
    if explicit_links_raw is not None:
        if not isinstance(explicit_links_raw, bool):
            raise ValueError("Package metadata option 'explicit_links' must be a boolean.")
        explicit_links = explicit_links_raw

    omit_pr_raw = raw.get("omit_pr")
    omit_pr = False
    if omit_pr_raw is not None:
        if not isinstance(omit_pr_raw, bool):
            raise ValueError("Package metadata option 'omit_pr' must be a boolean.")
        omit_pr = omit_pr_raw

    omit_author_raw = raw.get("omit_author")
    omit_author = False
    if omit_author_raw is not None:
        if not isinstance(omit_author_raw, bool):
            raise ValueError("Package metadata option 'omit_author' must be a boolean.")
        omit_author = omit_author_raw

    components = parse_components(raw.get("components"))
    modules_raw = raw.get("modules")
    modules = str(modules_raw).strip() if modules_raw else None

    # Parse release config
    release_config = ReleaseConfig()
    release_raw = raw.get("release")
    if release_raw is not None:
        if not isinstance(release_raw, MutableMapping):
            raise ValueError("Package metadata option 'release' must be a mapping.")
        commit_message = release_raw.get("commit_message")
        if commit_message is not None:
            release_config = ReleaseConfig(commit_message=str(commit_message))

    return Config(
        id=package_id,
        name=package_name,
        description=str(description_raw or ""),
        repository=(str(repository_raw) if repository_raw else None),
        export_style=export_style,
        explicit_links=explicit_links,
        omit_pr=omit_pr,
        omit_author=omit_author,
        components=components,
        modules=modules,
        release=release_config,
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
    if config.explicit_links:
        data["explicit_links"] = config.explicit_links
    if config.omit_pr:
        data["omit_pr"] = config.omit_pr
    if config.omit_author:
        data["omit_author"] = config.omit_author
    if config.components:
        data["components"] = dict(config.components)
    if config.modules:
        data["modules"] = config.modules
    if config.release.commit_message != "Release {version}":
        data["release"] = {"commit_message": config.release.commit_message}
    return data


def save_config(config: Config, path: Path) -> None:
    """Write the configuration to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(dump_config(config), handle, sort_keys=False)

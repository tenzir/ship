"""Configuration helpers for tenzir-ship."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, MutableMapping, cast

import yaml

from .utils import parse_components

ExportStyle = Literal["standard", "compact"]
ReleaseVersionBumpMode = Literal["auto", "off"]
CONFIG_RELATIVE_PATH = Path("config.yaml")
PACKAGE_METADATA_FILENAME = "package.yaml"
CHANGELOG_DIRECTORY_NAME = "changelog"

EXPORT_STYLE_STANDARD: ExportStyle = "standard"
EXPORT_STYLE_COMPACT: ExportStyle = "compact"
EXPORT_STYLE_CHOICES: tuple[ExportStyle, ...] = (
    EXPORT_STYLE_STANDARD,
    EXPORT_STYLE_COMPACT,
)
DEFAULT_RELEASE_COMMIT_MESSAGE = "Release v{version}"


def default_config_path(project_root: Path) -> Path:
    """Return the default config path for a project root."""
    return project_root / CONFIG_RELATIVE_PATH


def package_metadata_path(project_root: Path) -> Path:
    """Return the expected package metadata path for a changelog project root."""

    return project_root.parent / PACKAGE_METADATA_FILENAME


@dataclass
class ReleaseConfig:
    """Configuration for release operations."""

    commit_message: str = DEFAULT_RELEASE_COMMIT_MESSAGE
    version_bump_mode: ReleaseVersionBumpMode = "auto"
    version_files: list[str] = field(default_factory=list)
    # Entries tagged with any of these components stay in unreleased/.
    exclude_components: list[str] = field(default_factory=list)


def _parse_string_list(value: object, option: str, *, item_label: str) -> list[str]:
    """Parse a list of non-empty strings from a release option."""
    if not isinstance(value, list):
        raise ValueError(f"{option} must be a list of {item_label}s.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{option} must contain only strings.")
        stripped = item.strip()
        if not stripped:
            raise ValueError(f"{option} must not contain empty {item_label}s.")
        result.append(stripped)
    return result


def _parse_release_config(release_raw: object, source: str) -> ReleaseConfig:
    """Parse the ``release`` section of a config or package manifest.

    ``source`` prefixes error messages, for example ``"Config option"``.
    """
    release_config = ReleaseConfig()
    if release_raw is None:
        return release_config
    if not isinstance(release_raw, MutableMapping):
        raise ValueError(f"{source} 'release' must be a mapping.")
    commit_message = release_raw.get("commit_message")
    version_bump_mode_raw = release_raw.get("version_bump_mode")
    version_bump_mode: ReleaseVersionBumpMode = "auto"
    if version_bump_mode_raw is not None:
        if not isinstance(version_bump_mode_raw, str):
            raise ValueError(f"{source} 'release.version_bump_mode' must be a string.")
        normalized_mode = version_bump_mode_raw.strip().lower()
        if normalized_mode not in {"auto", "off"}:
            raise ValueError(f"{source} 'release.version_bump_mode' must be one of: auto, off.")
        version_bump_mode = cast(ReleaseVersionBumpMode, normalized_mode)

    version_files_raw = release_raw.get("version_files")
    version_files: list[str] = []
    if version_files_raw is not None:
        version_files = _parse_string_list(
            version_files_raw, f"{source} 'release.version_files'", item_label="path"
        )

    exclude_components_raw = release_raw.get("exclude_components")
    exclude_components: list[str] = []
    if exclude_components_raw is not None:
        exclude_components = _parse_string_list(
            exclude_components_raw,
            f"{source} 'release.exclude_components'",
            item_label="label",
        )

    return ReleaseConfig(
        commit_message=(
            str(commit_message) if commit_message is not None else release_config.commit_message
        ),
        version_bump_mode=version_bump_mode,
        version_files=version_files,
        exclude_components=exclude_components,
    )


def _check_excluded_components(
    release_config: ReleaseConfig, components: dict[str, str], source: str
) -> None:
    """Reject excluded components that the config does not declare."""
    if not components:
        return
    declared = {component.lower() for component in components}
    unknown = [c for c in release_config.exclude_components if c.lower() not in declared]
    if unknown:
        allowed = ", ".join(components)
        unknown_display = ", ".join(f"'{c}'" for c in unknown)
        raise ValueError(
            f"{source} 'release.exclude_components' names unknown component(s) "
            f"{unknown_display}. Allowed components: {allowed}"
        )


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
    require_pr: bool = False
    omit_author: bool = False
    require_author: bool = False
    components: dict[str, str] = field(default_factory=dict)
    modules: str | None = None  # glob pattern for nested changelog projects
    release: ReleaseConfig = field(default_factory=ReleaseConfig)


def load_config(path: Path) -> Config:
    """Load the configuration from disk."""
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, MutableMapping):
        raise ValueError("Config root must be a mapping")

    project_value_raw = raw.get("id")
    project_value = project_value_raw.strip() if isinstance(project_value_raw, str) else ""
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
        export_style = normalized_export_style

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

    require_pr_raw = raw.get("require_pr")
    require_pr = False
    if require_pr_raw is not None:
        if not isinstance(require_pr_raw, bool):
            raise ValueError("Config option 'require_pr' must be a boolean.")
        require_pr = require_pr_raw
    if require_pr and omit_pr:
        raise ValueError("Config options 'require_pr' and 'omit_pr' are mutually exclusive.")

    omit_author_raw = raw.get("omit_author")
    omit_author = False
    if omit_author_raw is not None:
        if not isinstance(omit_author_raw, bool):
            raise ValueError("Config option 'omit_author' must be a boolean.")
        omit_author = omit_author_raw

    require_author_raw = raw.get("require_author")
    require_author = False
    if require_author_raw is not None:
        if not isinstance(require_author_raw, bool):
            raise ValueError("Config option 'require_author' must be a boolean.")
        require_author = require_author_raw
    if require_author and omit_author:
        raise ValueError(
            "Config options 'require_author' and 'omit_author' are mutually exclusive."
        )

    components = parse_components(raw.get("components"))
    modules_raw = raw.get("modules")
    modules = str(modules_raw).strip() if modules_raw else None

    release_config = _parse_release_config(raw.get("release"), "Config option")
    _check_excluded_components(release_config, components, "Config option")

    return Config(
        id=project_value,
        name=str(name_raw or "Unnamed Project"),
        description=str(description_raw or ""),
        repository=(str(repository_raw) if repository_raw else None),
        export_style=export_style,
        explicit_links=explicit_links,
        omit_pr=omit_pr,
        require_pr=require_pr,
        omit_author=omit_author,
        require_author=require_author,
        components=components,
        modules=modules,
        release=release_config,
    )


def load_package_config(path: Path) -> Config:
    """Load changelog configuration metadata from a package manifest."""

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
        export_style = normalized_export_style

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

    require_pr_raw = raw.get("require_pr")
    require_pr = False
    if require_pr_raw is not None:
        if not isinstance(require_pr_raw, bool):
            raise ValueError("Package metadata option 'require_pr' must be a boolean.")
        require_pr = require_pr_raw
    if require_pr and omit_pr:
        raise ValueError("Config options 'require_pr' and 'omit_pr' are mutually exclusive.")

    omit_author_raw = raw.get("omit_author")
    omit_author = False
    if omit_author_raw is not None:
        if not isinstance(omit_author_raw, bool):
            raise ValueError("Package metadata option 'omit_author' must be a boolean.")
        omit_author = omit_author_raw

    require_author_raw = raw.get("require_author")
    require_author = False
    if require_author_raw is not None:
        if not isinstance(require_author_raw, bool):
            raise ValueError("Package metadata option 'require_author' must be a boolean.")
        require_author = require_author_raw
    if require_author and omit_author:
        raise ValueError(
            "Config options 'require_author' and 'omit_author' are mutually exclusive."
        )

    components = parse_components(raw.get("components"))
    modules_raw = raw.get("modules")
    modules = str(modules_raw).strip() if modules_raw else None

    release_config = _parse_release_config(raw.get("release"), "Package metadata option")
    _check_excluded_components(release_config, components, "Package metadata option")

    return Config(
        id=package_id,
        name=package_name,
        description=str(description_raw or ""),
        repository=(str(repository_raw) if repository_raw else None),
        export_style=export_style,
        explicit_links=explicit_links,
        omit_pr=omit_pr,
        require_pr=require_pr,
        omit_author=omit_author,
        require_author=require_author,
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
    if config.require_pr:
        data["require_pr"] = config.require_pr
    if config.omit_author:
        data["omit_author"] = config.omit_author
    if config.require_author:
        data["require_author"] = config.require_author
    if config.components:
        data["components"] = dict(config.components)
    if config.modules:
        data["modules"] = config.modules
    release_data: dict[str, Any] = {}
    if config.release.commit_message != DEFAULT_RELEASE_COMMIT_MESSAGE:
        release_data["commit_message"] = config.release.commit_message
    if config.release.version_bump_mode != "auto":
        release_data["version_bump_mode"] = config.release.version_bump_mode
    if config.release.version_files:
        release_data["version_files"] = list(config.release.version_files)
    if config.release.exclude_components:
        release_data["exclude_components"] = list(config.release.exclude_components)
    if release_data:
        data["release"] = release_data
    return data


def save_config(config: Config, path: Path) -> None:
    """Write the configuration to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(dump_config(config), handle, sort_keys=False)

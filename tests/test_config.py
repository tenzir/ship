"""Unit tests for configuration helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tenzir_ship.config import (
    DEFAULT_RELEASE_COMMIT_MESSAGE,
    Config,
    ReleaseConfig,
    dump_config,
    load_config,
    load_package_config,
    load_project_config,
)


def write_yaml(path: Path, content: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")


def test_load_config_supports_flat_id_field(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(
        config_path,
        {
            "id": "node",
            "name": "Node Project",
            "description": "Docs for Node.",
            "repository": "tenzir/node",
        },
    )

    config = load_config(config_path)

    assert config.id == "node"
    assert config.name == "Node Project"
    assert config.description == "Docs for Node."
    assert config.repository == "tenzir/node"


def test_dump_config_omits_empty_fields() -> None:
    config = Config(id="node", name="Node Project")

    payload = dump_config(config)

    assert payload == {"id": "node", "name": "Node Project"}


def test_load_config_supports_require_pr(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(config_path, {"id": "node", "name": "Node Project", "require_pr": True})

    config = load_config(config_path)

    assert config.require_pr is True


def test_load_config_defaults_require_pr_to_false(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(config_path, {"id": "node", "name": "Node Project"})

    config = load_config(config_path)

    assert config.require_pr is False


def test_load_config_rejects_non_bool_require_pr(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(config_path, {"id": "node", "name": "Node Project", "require_pr": "yes"})

    with pytest.raises(ValueError, match="require_pr"):
        load_config(config_path)


def test_load_config_rejects_require_pr_with_omit_pr(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(
        config_path,
        {
            "id": "node",
            "name": "Node Project",
            "omit_pr": True,
            "require_pr": True,
        },
    )

    with pytest.raises(ValueError, match="mutually exclusive"):
        load_config(config_path)


def test_load_package_config_rejects_require_pr_with_omit_pr(tmp_path: Path) -> None:
    package_path = tmp_path / "package.yaml"
    write_yaml(
        package_path,
        {
            "id": "pkg",
            "name": "Package",
            "omit_pr": True,
            "require_pr": True,
        },
    )

    with pytest.raises(ValueError, match="mutually exclusive"):
        load_package_config(package_path)


def test_load_package_config_supports_require_pr(tmp_path: Path) -> None:
    package_path = tmp_path / "package.yaml"
    write_yaml(package_path, {"id": "pkg", "name": "Package", "require_pr": True})

    config = load_package_config(package_path)

    assert config.require_pr is True


def test_dump_config_includes_require_pr_only_when_true() -> None:
    default_payload = dump_config(Config(id="node", name="Node Project"))
    require_pr_payload = dump_config(Config(id="node", name="Node Project", require_pr=True))

    assert "require_pr" not in default_payload
    assert require_pr_payload["require_pr"] is True


def test_load_project_config_uses_package_metadata(tmp_path: Path) -> None:
    changelog_root = tmp_path / "package" / "changelog"
    changelog_root.mkdir(parents=True)
    write_yaml(changelog_root.parent / "package.yaml", {"id": "pkg", "name": "Package"})

    config = load_project_config(changelog_root)

    assert config.id == "pkg"
    assert config.name == "Package"


def test_load_package_config_requires_id(tmp_path: Path) -> None:
    package_path = tmp_path / "package.yaml"
    write_yaml(package_path, {"name": "Package"})

    with pytest.raises(ValueError, match="missing required 'id'"):
        load_package_config(package_path)


def test_load_project_config_requires_config_yaml_or_package_metadata(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No config found"):
        load_project_config(tmp_path)


def test_load_config_uses_tag_prefixed_default_release_commit_message(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(
        config_path,
        {
            "id": "demo",
            "name": "Demo",
        },
    )

    config = load_config(config_path)

    assert config.release.commit_message == DEFAULT_RELEASE_COMMIT_MESSAGE


def test_load_config_release_version_bump_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(
        config_path,
        {
            "id": "demo",
            "name": "Demo",
            "release": {
                "version_bump_mode": "off",
                "version_files": ["../package.json", "python/pyproject.toml"],
            },
        },
    )

    config = load_config(config_path)

    assert config.release.version_bump_mode == "off"
    assert config.release.version_files == ["../package.json", "python/pyproject.toml"]


def test_load_config_rejects_invalid_release_version_bump_mode(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(
        config_path,
        {
            "id": "demo",
            "name": "Demo",
            "release": {"version_bump_mode": "manual"},
        },
    )

    with pytest.raises(ValueError, match="release.version_bump_mode"):
        load_config(config_path)


def test_load_config_rejects_invalid_release_version_files_type(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(
        config_path,
        {
            "id": "demo",
            "name": "Demo",
            "release": {"version_files": "pyproject.toml"},
        },
    )

    with pytest.raises(ValueError, match="release.version_files"):
        load_config(config_path)


def test_dump_config_includes_release_version_settings() -> None:
    config = Config(
        id="demo",
        name="Demo",
        release=ReleaseConfig(
            version_bump_mode="off",
            version_files=["../package.json"],
        ),
    )

    payload = dump_config(config)

    assert payload["release"]["version_bump_mode"] == "off"
    assert payload["release"]["version_files"] == ["../package.json"]

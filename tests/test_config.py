"""Unit tests for configuration helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from tenzir_changelog.config import Config, dump_config, load_config


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


def test_load_config_supports_legacy_workspace_mapping(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_yaml(
        config_path,
        {
            "workspace": {
                "name": "Legacy Project",
                "description": "An older layout",
                "repository": "tenzir/legacy",
            },
            "project": "legacy",
        },
    )

    config = load_config(config_path)

    assert config.id == "legacy"
    assert config.name == "Legacy Project"
    assert config.description == "An older layout"
    assert config.repository == "tenzir/legacy"


def test_dump_config_omits_empty_fields() -> None:
    config = Config(id="node", name="Node Project")

    payload = dump_config(config)

    assert payload == {"id": "node", "name": "Node Project"}

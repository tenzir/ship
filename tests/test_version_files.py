"""Unit tests for package-manager version file helpers."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from tenzir_ship.version_files import (
    SUPPORTED_AUTO_VERSION_FILES,
    _update_package_yaml,
    resolve_version_file_targets,
)

PACKAGE_YAML = Path("package.yaml")


def _update(
    content: str,
    *,
    new_version: str = "1.2.0",
    strict: bool = False,
    insert: bool = True,
) -> tuple[str, str | None]:
    return _update_package_yaml(
        PACKAGE_YAML,
        content,
        new_version,
        skip_if_missing_static_version=not strict,
        insert_if_missing=insert,
    )


def test_package_yaml_is_a_supported_version_file() -> None:
    assert "package.yaml" in SUPPORTED_AUTO_VERSION_FILES


def test_package_yaml_is_auto_detected_next_to_changelog(tmp_path: Path) -> None:
    changelog_dir = tmp_path / "changelog"
    changelog_dir.mkdir()
    package_yaml = tmp_path / "package.yaml"
    package_yaml.write_text("id: demo\nname: Demo\n", encoding="utf-8")

    assert resolve_version_file_targets(changelog_dir, []) == [package_yaml.resolve()]


@pytest.mark.parametrize(
    ("line", "old_version"),
    [
        ("version: 1.1.0", "1.1.0"),
        ("version: 1.1", "1.1"),
        ("version: '1.1.0'", "1.1.0"),
        ('version: "1.1.0"', "1.1.0"),
        ("version:", None),
        ("version: ~", None),
    ],
)
def test_update_package_yaml_replaces_existing_value(line: str, old_version: str | None) -> None:
    updated, old = _update(f"id: demo\n{line}\nname: Demo\n")

    assert updated == 'id: demo\nversion: "1.2.0"\nname: Demo\n'
    assert old == old_version


def test_update_package_yaml_preserves_trailing_comment() -> None:
    updated, old = _update("id: demo\nversion: 1.1.0   # bumped by release\n")

    assert updated == 'id: demo\nversion: "1.2.0"   # bumped by release\n'
    assert old == "1.1.0"


def test_update_package_yaml_is_idempotent() -> None:
    content = 'id: demo\nversion: "1.2.0"\n'

    assert _update(content) == (content, "1.2.0")


def test_update_package_yaml_only_touches_top_level_version() -> None:
    content = (
        "# Leading comment.\n"
        "id: demo\n"
        "name: Demo\n"
        "description: |\n"
        "  version: 0.0.1 is part of this block scalar.\n"
        "\n"
        "  More text.\n"
        "dependencies:\n"
        "  - id: other\n"
        "    version: 0.9.0\n"
        "settings:\n"
        "  version: 3\n"
        "version: 1.1.0\n"
    )

    updated, old = _update(content)

    assert updated == content.replace("version: 1.1.0\n", 'version: "1.2.0"\n')
    assert old == "1.1.0"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            "id: demo\nname: Demo  # display name\n# Comment.\ndescription: |\n  Text.\n",
            'id: demo\nname: Demo  # display name\nversion: "1.2.0"\n'
            "# Comment.\ndescription: |\n  Text.\n",
        ),
        (
            "name: Demo\nid: demo\n",
            'name: Demo\nversion: "1.2.0"\nid: demo\n',
        ),
        (
            "description: Text.\nid: demo\nauthor: Tenzir\n",
            'description: Text.\nid: demo\nversion: "1.2.0"\nauthor: Tenzir\n',
        ),
        (
            "# Header comment.\n---\ndescription: Text.\n",
            '# Header comment.\n---\nversion: "1.2.0"\ndescription: Text.\n',
        ),
        (
            "id: demo\nname: Demo",
            'id: demo\nname: Demo\nversion: "1.2.0"\n',
        ),
        (
            "id: demo\r\nname: Demo\r\ndescription: Text.\r\n",
            'id: demo\r\nname: Demo\r\nversion: "1.2.0"\r\ndescription: Text.\r\n',
        ),
        (
            "name: |\n  Demo\nid: demo\n",
            'name: |\n  Demo\nversion: "1.2.0"\nid: demo\n',
        ),
        ("", 'version: "1.2.0"\n'),
    ],
)
def test_update_package_yaml_inserts_missing_version(content: str, expected: str) -> None:
    updated, old = _update(content)

    assert updated == expected
    assert old is None


def test_update_package_yaml_skips_missing_version_without_insertion() -> None:
    content = "id: demo\nname: Demo\n"

    assert _update(content, insert=False) == (content, None)


def test_update_package_yaml_rejects_missing_version_when_strict() -> None:
    with pytest.raises(click.ClickException, match="missing a top-level 'version' field"):
        _update("id: demo\nname: Demo\n", strict=True, insert=False)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("- id: demo\n", "Expected a YAML mapping"),
        ("id: [demo\n", "Cannot parse YAML"),
        ("id: demo\nversion:\n  major: 1\n", "to be a scalar value"),
        ("{id: demo, name: Demo}\n", "flow-style YAML mapping"),
    ],
)
def test_update_package_yaml_rejects_unsupported_content(content: str, message: str) -> None:
    with pytest.raises(click.ClickException, match=message):
        _update(content)

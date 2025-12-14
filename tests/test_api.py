from __future__ import annotations

from pathlib import Path

import pytest

from typing import Sequence

from tenzir_changelog import Changelog
from tenzir_changelog.config import Config, save_config
from tenzir_changelog import cli as cli_module
from tenzir_changelog.entries import read_entry


def _bootstrap_project(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    save_config(Config(id="project", name="Project"), project_dir / "config.yaml")
    return project_dir


def test_python_api_add_entry_creates_file(tmp_path: Path) -> None:
    project_dir = _bootstrap_project(tmp_path)
    client = Changelog(root=project_dir)

    path = client.add(
        title="API entry",
        entry_type="feature",
        components=["core"],
        authors=["codex"],
        prs=["42"],
        description="Body",
    )

    assert path.exists()
    assert path.parent == project_dir / "unreleased"
    contents = path.read_text(encoding="utf-8")
    assert "API entry" in contents
    assert "feature" in contents


def test_python_api_show_delegates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_dir = _bootstrap_project(tmp_path)
    # populate data needed for context
    client = Changelog(root=project_dir)

    captured: dict[str, object] = {}

    def fake_run_show_entries(
        ctx: cli_module.CLIContext,
        *,
        identifiers: Sequence[str] | None,
        view: str,
        project_filter: Sequence[str] | None,
        component_filter: Sequence[str] | None,
        banner: bool,
        compact: bool | None,
        include_emoji: bool,
        include_modules: bool = True,
        explicit_links: bool = False,
    ) -> None:
        captured["ctx"] = ctx
        captured["identifiers"] = identifiers
        captured["view"] = view
        captured["project_filter"] = project_filter
        captured["component_filter"] = component_filter
        captured["banner"] = banner
        captured["compact"] = compact
        captured["include_emoji"] = include_emoji
        captured["include_modules"] = include_modules
        captured["explicit_links"] = explicit_links

    monkeypatch.setattr("tenzir_changelog.api.run_show_entries", fake_run_show_entries)

    client.show(
        identifiers=["latest"],
        view="table",
        project_filter=["project"],
        component_filter=["core"],
        banner=True,
        include_emoji=False,
    )

    assert captured["ctx"] is client.context
    assert captured["identifiers"] == ["latest"]
    assert captured["view"] == "table"
    assert captured["project_filter"] == ["project"]
    assert captured["component_filter"] == ["core"]
    assert captured["banner"] is True
    assert captured["compact"] is None
    assert captured["include_emoji"] is False


def test_python_api_add_handles_missing_authors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project_dir = _bootstrap_project(tmp_path)
    monkeypatch.setattr("tenzir_changelog.cli.detect_github_login", lambda log_success=False: None)
    client = Changelog(root=project_dir)

    path = client.add(
        title="No author entry",
        entry_type="feature",
        description="Body",
        authors=None,
    )

    entry = read_entry(path)
    assert entry.metadata.get("authors") is None


def test_python_api_add_defaults_entry_type(tmp_path: Path) -> None:
    project_dir = _bootstrap_project(tmp_path)
    client = Changelog(root=project_dir)

    path = client.add(
        title="Default type entry",
        description="Body",
    )

    entry = read_entry(path)
    assert entry.metadata.get("type") == "feature"

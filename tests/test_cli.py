"""Integration-style tests for the tenzir-changelog CLI."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import click
from click.testing import CliRunner
import yaml

from tenzir_changelog.cli import INFO_PREFIX, cli
from tenzir_changelog.entries import read_entry


def test_bootstrap_add_and_release(tmp_path: Path) -> None:
    runner = CliRunner()
    project_root = tmp_path

    bootstrap_input = (
        "\n"  # Project name (accept default)
        "\n"  # Project description
        "\n"  # Repository slug
        "node\n"  # Product name
    )
    result = runner.invoke(
        cli,
        ["--root", str(project_root), "bootstrap"],
        input=bootstrap_input,
    )
    assert result.exit_code == 0, result.output
    workspace_root = project_root / "changelog"
    config_path = workspace_root / "config.yaml"
    assert workspace_root.exists()
    assert config_path.exists()

    # Add entries via CLI, relying on defaults for type/project.
    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "add",
            "--title",
            "Exciting Feature",
            "--type",
            "feature",
            "--description",
            "Adds an exciting capability.",
            "--author",
            "octocat",
            "--pr",
            "42",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    add_bugfix = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "add",
            "--title",
            "Fix ingest crash",
            "--type",
            "bugfix",
            "--description",
            "Resolves ingest worker crash when tokens expire.",
            "--author",
            "bob",
            "--pr",
            "102",
            "--pr",
            "115",
        ],
    )
    assert add_bugfix.exit_code == 0, add_bugfix.output

    entries_dir = workspace_root / "unreleased"
    entry_files = sorted(entries_dir.glob("*.md"))
    assert len(entry_files) == 2

    feature_entry = entries_dir / "exciting-feature.md"
    assert feature_entry.exists()
    entry_text = feature_entry.read_text(encoding="utf-8")
    assert "created:" in entry_text
    assert "pr: 42" in entry_text
    assert "project:" not in entry_text
    parsed_entry = read_entry(feature_entry)
    assert isinstance(parsed_entry.metadata["created"], date)
    assert parsed_entry.created_at == parsed_entry.metadata["created"]

    bugfix_entry = entries_dir / "fix-ingest-crash.md"
    assert bugfix_entry.exists()
    bugfix_text = bugfix_entry.read_text(encoding="utf-8")
    assert "prs:" in bugfix_text
    assert "- 102" in bugfix_text and "- 115" in bugfix_text
    assert "project:" not in bugfix_text

    intro_file = project_root / "intro.md"
    intro_file.write_text("Welcome to the release!\n\n![Image](assets/hero.png)\n")

    release_result = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "release",
            "create",
            "v1.0.0",
            "--description",
            "First stable release.",
            "--intro-file",
            str(intro_file),
            "--compact",
            "--yes",
        ],
    )
    assert release_result.exit_code == 0, release_result.output
    release_dir = workspace_root / "releases" / "v1.0.0"
    release_path = release_dir / "notes.md"
    manifest_path = release_dir / "manifest.yaml"
    assert release_path.exists()
    assert manifest_path.exists()

    release_text = release_path.read_text(encoding="utf-8")
    first_line = release_text.lstrip().splitlines()[0]
    assert first_line == "First stable release.", release_text
    assert "First stable release." in release_text
    assert "- **Exciting Feature**: Adds an exciting capability." in release_text
    assert (
        "- **Fix ingest crash**: Resolves ingest worker crash when tokens expire." in release_text
    )
    assert "![Image](assets/hero.png)" in release_text

    manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["version"] == "v1.0.0"
    assert isinstance(manifest_data["created"], date)
    assert "entries" in manifest_data
    assert "project" not in manifest_data
    assert "description" not in manifest_data
    assert "title" not in manifest_data
    assert "exciting-feature" in manifest_data["entries"]
    assert "fix-ingest-crash" in manifest_data["entries"]

    release_entries_dir = release_dir / "entries"
    assert release_entries_dir.is_dir()
    assert (release_entries_dir / "exciting-feature.md").exists()
    assert (release_entries_dir / "fix-ingest-crash.md").exists()
    assert not any(entries_dir.iterdir())

    show_result = runner.invoke(
        cli,
        ["--root", str(workspace_root), "show"],
    )
    assert show_result.exit_code == 0, show_result.output
    plain_show = click.utils.strip_ansi(show_result.output)
    assert "Name:" not in plain_show
    assert "Types:" not in plain_show
    assert "exciting-feature" in plain_show
    assert "v1.0.0" in plain_show

    show_banner = runner.invoke(
        cli,
        ["--root", str(workspace_root), "show", "--banner"],
    )
    assert show_banner.exit_code == 0, show_banner.output
    banner_output = click.utils.strip_ansi(show_banner.output)
    assert "Name: " in banner_output
    assert "Types: " in banner_output

    release_show = runner.invoke(
        cli,
        ["--root", str(workspace_root), "show", "--release", "v1.0.0"],
    )
    assert release_show.exit_code == 0, release_show.output
    release_plain = click.utils.strip_ansi(release_show.output)
    assert "Included Entries" in release_plain
    assert "exciting-feature" in release_plain
    assert "fix-ingest-crash" in release_plain

    export_md = runner.invoke(
        cli,
        ["--root", str(workspace_root), "export", "--release", "v1.0.0"],
    )
    assert export_md.exit_code == 0, export_md.output
    assert "## Features" in export_md.output
    assert "### Exciting Feature" in export_md.output
    assert "By [octocat](https://github.com/octocat)" in export_md.output
    assert "in #42" in export_md.output
    assert "### Fix ingest crash" in export_md.output
    assert "#102" in export_md.output and "#115" in export_md.output

    export_compact = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "export",
            "--release",
            "v1.0.0",
            "--compact",
        ],
    )
    assert export_compact.exit_code == 0, export_compact.output
    assert "## Features" in export_compact.output
    assert "- **Exciting Feature**: Adds an exciting capability." in export_compact.output
    assert "## Bug fixes" in export_compact.output
    assert (
        "- **Fix ingest crash**: Resolves ingest worker crash when tokens expire."
        in export_compact.output
    )

    export_json = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "export",
            "--release",
            "v1.0.0",
            "--format",
            "json",
            "--compact",
        ],
    )
    assert export_json.exit_code == 0, export_json.output
    payload = json.loads(export_json.output)
    assert payload["version"] == "v1.0.0"
    assert payload["project"] == "node"
    feature_entry = next(
        entry for entry in payload["entries"] if entry["title"] == "Exciting Feature"
    )
    assert "v1.0.0" in feature_entry["versions"]
    assert feature_entry["pr"] == 42
    assert feature_entry["prs"] == [42]
    assert feature_entry["project"] == "node"
    assert feature_entry.get("excerpt") == "Adds an exciting capability."

    bugfix_entry = next(
        entry for entry in payload["entries"] if entry["title"] == "Fix ingest crash"
    )
    assert bugfix_entry["prs"] == [102, 115]
    assert bugfix_entry["project"] == "node"
    assert bugfix_entry.get("excerpt") == "Resolves ingest worker crash when tokens expire."
    assert payload.get("compact") is True

    validate_result = runner.invoke(
        cli,
        ["--root", str(workspace_root), "validate"],
    )
    assert validate_result.exit_code == 0, validate_result.output


def test_missing_project_reports_info_message(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(tmp_path), "show"])
    assert result.exit_code == 1
    expected_root = tmp_path.resolve()
    plain_prefix = click.utils.strip_ansi(INFO_PREFIX)
    expected_plain_output = (
        f"{plain_prefix}no tenzir-changelog project detected at {expected_root}.\n"
        f"{plain_prefix}run from your project root or provide --root.\n"
    )
    assert click.utils.strip_ansi(result.output) == expected_plain_output
    assert "Error:" not in result.output

"""Integration-style tests for the tenzir-changelog CLI."""

from __future__ import annotations

import json
from pathlib import Path

import click
from click.testing import CliRunner

from tenzir_changelog.cli import INFO_PREFIX, cli


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

    # Add entries via CLI, relying on defaults for type/projects.
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
            "--project",
            "node",
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
            "--project",
            "node",
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

    entries_dir = workspace_root / "entries"
    entry_files = sorted(entries_dir.glob("*.md"))
    assert len(entry_files) == 2

    feature_entry = entries_dir / "exciting-feature.md"
    assert feature_entry.exists()
    entry_text = feature_entry.read_text(encoding="utf-8")
    assert "created:" in entry_text
    assert "pr: 42" in entry_text

    bugfix_entry = entries_dir / "fix-ingest-crash.md"
    assert bugfix_entry.exists()
    bugfix_text = bugfix_entry.read_text(encoding="utf-8")
    assert "prs:" in bugfix_text
    assert "- 102" in bugfix_text and "- 115" in bugfix_text

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
        ],
        input="\n",  # Accept confirmation prompt.
    )
    assert release_result.exit_code == 0, release_result.output
    release_path = workspace_root / "releases" / "v1.0.0.md"
    assert release_path.exists()
    release_text = release_path.read_text(encoding="utf-8")
    assert release_text.startswith("---"), release_text
    assert "- exciting-feature" in release_text
    assert "- fix-ingest-crash" in release_text
    assert "![Image](assets/hero.png)" in release_text

    show_result = runner.invoke(
        cli,
        ["--root", str(workspace_root), "show"],
    )
    assert show_result.exit_code == 0, show_result.output

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
    assert feature_entry["projects"] == ["node"]

    bugfix_entry = next(
        entry for entry in payload["entries"] if entry["title"] == "Fix ingest crash"
    )
    assert bugfix_entry["prs"] == [102, 115]
    assert bugfix_entry["projects"] == ["node"]

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

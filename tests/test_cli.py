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

    add_breaking = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "add",
            "--title",
            "Remove legacy API",
            "--type",
            "breaking",
            "--description",
            "Removes the deprecated ingest API to prepare for v1.",
            "--author",
            "codex",
        ],
    )
    assert add_breaking.exit_code == 0, add_breaking.output

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
    assert len(entry_files) == 3

    feature_entry = entries_dir / "exciting-feature.md"
    assert feature_entry.exists()
    entry_text = feature_entry.read_text(encoding="utf-8")
    assert "created:" in entry_text
    assert "pr: 42" in entry_text
    assert "project:" not in entry_text
    parsed_entry = read_entry(feature_entry)
    assert isinstance(parsed_entry.metadata["created"], date)
    assert parsed_entry.created_at == parsed_entry.metadata["created"]

    breaking_entry = entries_dir / "remove-legacy-api.md"
    assert breaking_entry.exists()
    breaking_text = breaking_entry.read_text(encoding="utf-8")
    assert "type: breaking" in breaking_text
    assert "Removes the deprecated ingest API to prepare for v1." in breaking_text

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
    assert "## 💥 Breaking changes" in release_text
    assert (
        "- **Remove legacy API**: Removes the deprecated ingest API to prepare for v1."
        in release_text
    )
    assert "- **Exciting Feature**: Adds an exciting capability." in release_text
    assert (
        "- **Fix ingest crash**: Resolves ingest worker crash when tokens expire." in release_text
    )
    assert "## 🌟 Features" in release_text
    assert "## 🐞 Bug fixes" in release_text
    assert (
        release_text.index("## 💥 Breaking changes")
        < release_text.index("## 🌟 Features")
        < release_text.index("## 🐞 Bug fixes")
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
    assert "remove-legacy-api" in manifest_data["entries"]
    assert "fix-ingest-crash" in manifest_data["entries"]

    release_entries_dir = release_dir / "entries"
    assert release_entries_dir.is_dir()
    assert (release_entries_dir / "exciting-feature.md").exists()
    assert (release_entries_dir / "remove-legacy-api.md").exists()
    assert (release_entries_dir / "fix-ingest-crash.md").exists()
    assert not any(entries_dir.iterdir())

    list_result = runner.invoke(
        cli,
        ["--root", str(workspace_root), "list"],
    )
    assert list_result.exit_code == 0, list_result.output
    plain_list = click.utils.strip_ansi(list_result.output)
    assert "Name:" not in plain_list
    assert "Types:" not in plain_list
    assert "exciting-feature" in plain_list or "Exciting Feature" in plain_list
    assert "v1.0.0" in plain_list

    list_banner = runner.invoke(
        cli,
        ["--root", str(workspace_root), "list", "--banner"],
    )
    assert list_banner.exit_code == 0, list_banner.output
    banner_output = click.utils.strip_ansi(list_banner.output)
    assert "Name: " in banner_output
    assert "Types: " in banner_output

    release_list = runner.invoke(
        cli,
        ["--root", str(workspace_root), "list", "--release", "v1.0.0"],
    )
    assert release_list.exit_code == 0, release_list.output
    release_plain = click.utils.strip_ansi(release_list.output)
    assert "Included Entries" in release_plain
    assert "exciting-feature" in release_plain
    assert "remove-legacy-api" in release_plain
    assert "fix-ingest-crash" in release_plain

    show_md = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "markdown",
            "v1.0.0",
        ],
    )
    assert show_md.exit_code == 0, show_md.output
    assert "## 💥 Breaking changes" in show_md.output
    assert "## 🌟 Features" in show_md.output
    assert "### Remove legacy API" in show_md.output
    assert "By [codex](https://github.com/codex)" in show_md.output
    assert "### Exciting Feature" in show_md.output
    assert "By [octocat](https://github.com/octocat)" in show_md.output
    assert "in #42" in show_md.output
    assert "### Fix ingest crash" in show_md.output
    assert "#102" in show_md.output and "#115" in show_md.output
    assert show_md.output.index("## 💥 Breaking changes") < show_md.output.index("## 🌟 Features")
    assert show_md.output.index("## 🌟 Features") < show_md.output.index("## 🐞 Bug fixes")

    show_md_plain = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "markdown",
            "--no-emoji",
            "v1.0.0",
        ],
    )
    assert show_md_plain.exit_code == 0, show_md_plain.output
    assert "## Breaking changes" in show_md_plain.output
    assert "## Features" in show_md_plain.output
    assert "### Remove legacy API" in show_md_plain.output
    assert "### Exciting Feature" in show_md_plain.output
    assert "### Fix ingest crash" in show_md_plain.output
    assert "## Bug fixes" in show_md_plain.output
    assert show_md_plain.output.index("## Breaking changes") < show_md_plain.output.index(
        "## Features"
    )
    assert show_md_plain.output.index("## Features") < show_md_plain.output.index("## Bug fixes")
    assert "💥" not in show_md_plain.output
    assert "🌟" not in show_md_plain.output
    assert "🐞" not in show_md_plain.output

    show_compact = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "markdown",
            "-c",
            "v1.0.0",
        ],
    )
    assert show_compact.exit_code == 0, show_compact.output
    assert "## 💥 Breaking changes" in show_compact.output
    assert "## 🌟 Features" in show_compact.output
    assert "- **Remove legacy API**: Removes the deprecated ingest API to prepare for v1." in (
        show_compact.output
    )
    assert "- **Exciting Feature**: Adds an exciting capability." in show_compact.output
    assert "## 🐞 Bug fixes" in show_compact.output
    assert (
        "- **Fix ingest crash**: Resolves ingest worker crash when tokens expire."
        in show_compact.output
    )
    assert show_compact.output.index("## 💥 Breaking changes") < show_compact.output.index(
        "## 🌟 Features"
    )
    assert show_compact.output.index("## 🌟 Features") < show_compact.output.index(
        "## 🐞 Bug fixes"
    )

    show_compact_plain = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "markdown",
            "--no-emoji",
            "-c",
            "v1.0.0",
        ],
    )
    assert show_compact_plain.exit_code == 0, show_compact_plain.output
    assert "## Breaking changes" in show_compact_plain.output
    assert "## Features" in show_compact_plain.output
    assert "- **Remove legacy API**: Removes the deprecated ingest API to prepare for v1." in (
        show_compact_plain.output
    )
    assert "- **Exciting Feature**: Adds an exciting capability." in show_compact_plain.output
    assert "- **Fix ingest crash**: Resolves ingest worker crash when tokens expire." in (
        show_compact_plain.output
    )
    assert "## Bug fixes" in show_compact_plain.output
    assert show_compact_plain.output.index("## Breaking changes") < show_compact_plain.output.index(
        "## Features"
    )
    assert show_compact_plain.output.index("## Features") < show_compact_plain.output.index(
        "## Bug fixes"
    )
    assert "💥" not in show_compact_plain.output
    assert "🌟" not in show_compact_plain.output
    assert "🐞" not in show_compact_plain.output

    show_json = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "json",
            "-c",
            "v1.0.0",
        ],
    )
    assert show_json.exit_code == 0, show_json.output
    payload = json.loads(show_json.output)
    assert payload["version"] == "v1.0.0"
    assert payload["project"] == "node"
    assert len(payload["entries"]) == 3
    breaking_entry = payload["entries"][0]
    assert breaking_entry["title"] == "Remove legacy API"
    assert breaking_entry["type"] == "breaking"
    assert "v1.0.0" in breaking_entry["versions"]
    assert breaking_entry["authors"] == ["codex"]
    assert breaking_entry.get("excerpt") == "Removes the deprecated ingest API to prepare for v1."
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

    show_json_plain = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "json",
            "--no-emoji",
            "-c",
            "v1.0.0",
        ],
    )
    assert show_json_plain.exit_code == 0, show_json_plain.output
    payload_plain = json.loads(show_json_plain.output)
    assert payload_plain["entries"][0]["title"] == "Remove legacy API"
    assert payload_plain["entries"][0]["type"] == "breaking"
    plain_feature = next(
        entry for entry in payload_plain["entries"] if entry["title"] == "Exciting Feature"
    )
    assert plain_feature["prs"] == [42]
    assert all("🌟" not in entry["title"] for entry in payload_plain["entries"])
    assert all("💥" not in entry["title"] for entry in payload_plain["entries"])

    validate_result = runner.invoke(
        cli,
        ["--root", str(workspace_root), "validate"],
    )
    assert validate_result.exit_code == 0, validate_result.output


def test_missing_project_reports_info_message(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(tmp_path), "list"])
    assert result.exit_code == 1
    expected_root = tmp_path.resolve()
    plain_prefix = click.utils.strip_ansi(INFO_PREFIX)
    expected_plain_output = (
        f"{plain_prefix}no tenzir-changelog project detected at {expected_root}.\n"
        f"{plain_prefix}run from your project root or provide --root.\n"
    )
    assert click.utils.strip_ansi(result.output) == expected_plain_output
    assert "Error:" not in result.output


def test_compact_export_style_from_config(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    config_path = workspace_root / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "id: sample",
                "name: Sample Project",
                "export_style: compact",
            ]
        ),
        encoding="utf-8",
    )

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "add",
            "--title",
            "Compact Feature",
            "--type",
            "feature",
            "--description",
            "Adds compact defaults.",
            "--author",
            "",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    release_result = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "release",
            "v0.1.0",
            "--description",
            "Alpha release.",
            "--yes",
        ],
    )
    assert release_result.exit_code == 0, release_result.output

    release_notes_path = workspace_root / "releases" / "v0.1.0" / "notes.md"
    release_notes = release_notes_path.read_text(encoding="utf-8")
    assert "- **Compact Feature**: Adds compact defaults." in release_notes
    assert "### Compact Feature" not in release_notes

    show_result = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "markdown",
            "v0.1.0",
        ],
    )
    assert show_result.exit_code == 0, show_result.output
    assert "- **Compact Feature**: Adds compact defaults." in show_result.output


def test_show_unreleased_token(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / "config.yaml").write_text(
        "\n".join(
            [
                "id: sample",
                "name: Sample Project",
            ]
        ),
        encoding="utf-8",
    )

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "add",
            "--title",
            "Pending Feature",
            "--type",
            "feature",
            "--description",
            "Show unreleased entries via token.",
            "--author",
            "",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    terminal_result = runner.invoke(
        cli,
        ["--root", str(workspace_root), "show", "unreleased"],
    )
    assert terminal_result.exit_code == 0, terminal_result.output
    plain_output = click.utils.strip_ansi(terminal_result.output)
    assert "Pending Feature" in plain_output

    dash_terminal = runner.invoke(
        cli,
        ["--root", str(workspace_root), "show", "--", "-"],
    )
    assert dash_terminal.exit_code == 0, dash_terminal.output
    dash_output = click.utils.strip_ansi(dash_terminal.output)
    assert "Pending Feature" in dash_output

    markdown_result = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "markdown",
            "unreleased",
        ],
    )
    assert markdown_result.exit_code == 0, markdown_result.output
    assert "# Unreleased Changes" in markdown_result.output
    assert "### Pending Feature" in markdown_result.output

    markdown_plain = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "markdown",
            "--no-emoji",
            "unreleased",
        ],
    )
    assert markdown_plain.exit_code == 0, markdown_plain.output
    assert "### Pending Feature" in markdown_plain.output
    assert "🌟 Pending Feature" not in markdown_plain.output

    markdown_dash = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "markdown",
            "--",
            "-",
        ],
    )
    assert markdown_dash.exit_code == 0, markdown_dash.output
    assert "# Unreleased Changes" in markdown_dash.output

    json_result = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "json",
            "unreleased",
        ],
    )
    assert json_result.exit_code == 0, json_result.output
    payload = json.loads(json_result.output)
    assert payload["version"] is None
    assert payload["entries"]
    pending_entry = payload["entries"][0]
    assert pending_entry["title"] == "Pending Feature"
    assert pending_entry["project"] == "sample"

    json_plain = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "json",
            "--no-emoji",
            "unreleased",
        ],
    )
    assert json_plain.exit_code == 0, json_plain.output
    payload_no_emoji = json.loads(json_plain.output)
    assert payload_no_emoji["entries"][0]["title"] == "Pending Feature"

    json_dash = runner.invoke(
        cli,
        [
            "--root",
            str(workspace_root),
            "show",
            "--format",
            "json",
            "--",
            "-",
        ],
    )
    assert json_dash.exit_code == 0, json_dash.output
    dash_payload = json.loads(json_dash.output)
    assert dash_payload["entries"][0]["title"] == "Pending Feature"

    list_unreleased = runner.invoke(
        cli,
        ["--root", str(workspace_root), "list", "unreleased"],
    )
    assert list_unreleased.exit_code == 0, list_unreleased.output

    list_dash = runner.invoke(
        cli,
        ["--root", str(workspace_root), "list", "--", "-"],
    )
    assert list_dash.exit_code == 0, list_dash.output

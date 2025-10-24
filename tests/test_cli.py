"""Integration-style tests for the tenzir-changelog CLI."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import click
from click.testing import CliRunner
import yaml

from tenzir_changelog.cli import INFO_PREFIX, cli
from tenzir_changelog.entries import ENTRY_PREFIX_WIDTH, read_entry


def test_add_initializes_and_release(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    config_path = project_dir / "config.yaml"
    assert not config_path.exists()

    # Add entries via CLI, relying on defaults for type/project.
    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
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
    assert config_path.exists()

    add_breaking = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
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
            str(project_dir),
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

    entries_dir = project_dir / "unreleased"
    entry_files = sorted(entries_dir.glob("*.md"))
    assert len(entry_files) == 3

    feature_entry_matches = list(entries_dir.glob("*-exciting-feature.md"))
    assert feature_entry_matches
    feature_entry = feature_entry_matches[0]
    assert feature_entry.stem.split("-", 1)[0].isdigit()
    assert len(feature_entry.stem.split("-", 1)[0]) >= ENTRY_PREFIX_WIDTH
    entry_text = feature_entry.read_text(encoding="utf-8")
    assert "created:" in entry_text
    assert "prs:" in entry_text
    assert "- 42" in entry_text
    assert "project:" not in entry_text
    parsed_entry = read_entry(feature_entry)
    assert isinstance(parsed_entry.metadata["created"], date)
    assert parsed_entry.created_at == parsed_entry.metadata["created"]

    breaking_entry_matches = list(entries_dir.glob("*-remove-legacy-api.md"))
    assert breaking_entry_matches
    breaking_entry = breaking_entry_matches[0]
    breaking_text = breaking_entry.read_text(encoding="utf-8")
    assert "type: breaking" in breaking_text
    assert "Removes the deprecated ingest API to prepare for v1." in breaking_text

    bugfix_entry_matches = list(entries_dir.glob("*-fix-ingest-crash.md"))
    assert bugfix_entry_matches
    bugfix_entry = bugfix_entry_matches[0]
    bugfix_text = bugfix_entry.read_text(encoding="utf-8")
    assert "prs:" in bugfix_text
    assert "- 102" in bugfix_text and "- 115" in bugfix_text
    assert "project:" not in bugfix_text

    feature_entry_id = feature_entry.stem
    bugfix_entry_id = bugfix_entry.stem

    get_feature = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-c",
            feature_entry_id,
        ],
    )
    assert get_feature.exit_code == 0, get_feature.output
    feature_plain = click.utils.strip_ansi(get_feature.output)
    assert "Exciting Feature" in feature_plain
    assert feature_entry_id in feature_plain

    intro_file = tmp_path / "intro.md"
    intro_file.write_text("Welcome to the release!\n\n![Image](assets/hero.png)\n")

    release_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
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
    release_dir = project_dir / "releases" / "v1.0.0"
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
        " (By @codex)" in release_text
    )
    assert (
        "- **Exciting Feature**: Adds an exciting capability. (By @octocat in #42)" in release_text
    )
    assert (
        "- **Fix ingest crash**: Resolves ingest worker crash when tokens expire."
        " (By @bob in #102 and #115)" in release_text
    )
    assert "## 🚀 Features" in release_text
    assert "## 🐞 Bug fixes" in release_text
    assert (
        release_text.index("## 💥 Breaking changes")
        < release_text.index("## 🚀 Features")
        < release_text.index("## 🐞 Bug fixes")
    )
    assert "![Image](assets/hero.png)" in release_text

    manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert "version" not in manifest_data
    assert isinstance(manifest_data["created"], date)
    assert "entries" not in manifest_data
    assert "project" not in manifest_data
    assert "description" not in manifest_data
    assert "title" not in manifest_data

    release_entries_dir = release_dir / "entries"
    assert release_entries_dir.is_dir()
    assert list(release_entries_dir.glob("*-exciting-feature.md"))
    assert list(release_entries_dir.glob("*-remove-legacy-api.md"))
    assert list(release_entries_dir.glob("*-fix-ingest-crash.md"))
    release_entry_stems = {path.stem for path in release_entries_dir.glob("*.md")}
    assert any(stem.endswith("exciting-feature") for stem in release_entry_stems)
    assert any(stem.endswith("remove-legacy-api") for stem in release_entry_stems)
    assert any(stem.endswith("fix-ingest-crash") for stem in release_entry_stems)
    assert not any(entries_dir.iterdir())

    list_result = runner.invoke(
        cli,
        ["--root", str(project_dir), "show"],
    )
    assert list_result.exit_code == 0, list_result.output
    plain_list = click.utils.strip_ansi(list_result.output)
    assert "Name:" not in plain_list
    assert "Types:" not in plain_list
    assert "exciting-feature" in plain_list or "Exciting Feature" in plain_list
    assert "v1.0.0" in plain_list

    list_banner = runner.invoke(
        cli,
        ["--root", str(project_dir), "show", "--banner"],
    )
    assert list_banner.exit_code == 0, list_banner.output
    banner_output = click.utils.strip_ansi(list_banner.output)
    assert "Name: " in banner_output
    assert "Types: " in banner_output

    release_list = runner.invoke(
        cli,
        ["--root", str(project_dir), "show", "v1.0.0"],
    )
    assert release_list.exit_code == 0, release_list.output
    release_plain = click.utils.strip_ansi(release_list.output)
    assert "Included Entries" in release_plain
    assert "exciting-feature" in release_plain
    assert "remove-legacy-api" in release_plain
    assert "fix-ingest-crash" in release_plain

    get_md = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "v1.0.0",
        ],
    )
    assert get_md.exit_code == 0, get_md.output
    assert "First stable release." not in get_md.output
    assert "## 💥 Breaking changes" in get_md.output
    assert "## 🚀 Features" in get_md.output
    assert "### Remove legacy API" in get_md.output
    assert "By @codex" in get_md.output
    assert "### Exciting Feature" in get_md.output
    assert "By @octocat" in get_md.output
    assert "in #42" in get_md.output
    assert "### Fix ingest crash" in get_md.output
    assert "#102" in get_md.output and "#115" in get_md.output
    assert get_md.output.index("## 💥 Breaking changes") < get_md.output.index("## 🚀 Features")
    assert get_md.output.index("## 🚀 Features") < get_md.output.index("## 🐞 Bug fixes")

    get_md_plain = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "--no-emoji",
            "v1.0.0",
        ],
    )
    assert get_md_plain.exit_code == 0, get_md_plain.output
    assert "First stable release." not in get_md_plain.output
    assert "## Breaking changes" in get_md_plain.output
    assert "## Features" in get_md_plain.output
    assert "### Remove legacy API" in get_md_plain.output
    assert "### Exciting Feature" in get_md_plain.output
    assert "### Fix ingest crash" in get_md_plain.output
    assert "## Bug fixes" in get_md_plain.output
    assert get_md_plain.output.index("## Breaking changes") < get_md_plain.output.index(
        "## Features"
    )
    assert get_md_plain.output.index("## Features") < get_md_plain.output.index("## Bug fixes")
    assert "💥" not in get_md_plain.output
    assert "🚀" not in get_md_plain.output
    assert "🐞" not in get_md_plain.output

    get_compact = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "--compact",
            "v1.0.0",
        ],
    )
    assert get_compact.exit_code == 0, get_compact.output
    assert "First stable release." not in get_compact.output
    assert "## 💥 Breaking changes" in get_compact.output
    assert "## 🚀 Features" in get_compact.output
    assert (
        "- **Remove legacy API**: Removes the deprecated ingest API to prepare for v1."
        " (By @codex)" in get_compact.output
    )
    assert (
        "- **Exciting Feature**: Adds an exciting capability."
        " (By @octocat in #42)" in get_compact.output
    )
    assert "## 🐞 Bug fixes" in get_compact.output
    assert (
        "- **Fix ingest crash**: Resolves ingest worker crash when tokens expire."
        " (By @bob in #102 and #115)" in get_compact.output
    )
    assert get_compact.output.index("## 💥 Breaking changes") < get_compact.output.index(
        "## 🚀 Features"
    )
    assert get_compact.output.index("## 🚀 Features") < get_compact.output.index("## 🐞 Bug fixes")
    get_compact_plain = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "--no-emoji",
            "--compact",
            "v1.0.0",
        ],
    )
    assert get_compact_plain.exit_code == 0, get_compact_plain.output
    assert "First stable release." not in get_compact_plain.output
    assert "## Breaking changes" in get_compact_plain.output
    assert "## Features" in get_compact_plain.output
    assert (
        "- **Remove legacy API**: Removes the deprecated ingest API to prepare for v1."
        " (By @codex)" in get_compact_plain.output
    )
    assert (
        "- **Exciting Feature**: Adds an exciting capability."
        " (By @octocat in #42)" in get_compact_plain.output
    )
    assert (
        "- **Fix ingest crash**: Resolves ingest worker crash when tokens expire."
        " (By @bob in #102 and #115)" in get_compact_plain.output
    )
    assert "## Bug fixes" in get_compact_plain.output
    assert get_compact_plain.output.index("## Breaking changes") < get_compact_plain.output.index(
        "## Features"
    )
    assert get_compact_plain.output.index("## Features") < get_compact_plain.output.index(
        "## Bug fixes"
    )
    assert "💥" not in get_compact_plain.output
    assert "🚀" not in get_compact_plain.output
    assert "🐞" not in get_compact_plain.output

    get_json = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-j",
            "--compact",
            "v1.0.0",
        ],
    )
    assert get_json.exit_code == 0, get_json.output
    payload = json.loads(get_json.output)
    assert payload["version"] == "v1.0.0"
    assert payload["project"] == "project"
    assert len(payload["entries"]) == 3
    breaking_entry = payload["entries"][0]
    assert breaking_entry["title"] == "Remove legacy API"
    assert breaking_entry["type"] == "breaking"
    assert breaking_entry["version"] == "v1.0.0"
    assert breaking_entry["authors"] == ["codex"]
    assert breaking_entry.get("excerpt") == "Removes the deprecated ingest API to prepare for v1."
    feature_entry = next(
        entry for entry in payload["entries"] if entry["title"] == "Exciting Feature"
    )
    assert feature_entry["version"] == "v1.0.0"
    assert feature_entry["prs"] == [42]
    assert "pr" not in feature_entry
    assert feature_entry["project"] == "project"
    assert feature_entry.get("excerpt") == "Adds an exciting capability."

    bugfix_entry = next(
        entry for entry in payload["entries"] if entry["title"] == "Fix ingest crash"
    )
    assert bugfix_entry["prs"] == [102, 115]
    assert bugfix_entry["project"] == "project"
    assert bugfix_entry.get("excerpt") == "Resolves ingest worker crash when tokens expire."
    assert payload.get("compact") is True

    single_entry_json = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-j",
            feature_entry_id,
        ],
    )
    assert single_entry_json.exit_code == 0, single_entry_json.output
    single_payload = json.loads(single_entry_json.output)
    assert single_payload["title"] == f"Entry {feature_entry_id}"
    assert single_payload["project"] == "project"
    assert single_payload["entries"][0]["id"] == feature_entry_id
    assert single_payload["entries"][0]["prs"] == [42]
    assert single_payload["entries"][0]["title"] == "Exciting Feature"
    assert single_payload["created"] == parsed_entry.created_at.isoformat()

    multi_entry_json = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-j",
            feature_entry_id,
            bugfix_entry_id,
        ],
    )
    assert multi_entry_json.exit_code == 0, multi_entry_json.output
    multi_payload = json.loads(multi_entry_json.output)
    assert multi_payload["title"] == "Selected Entries"
    exported_titles = {entry["title"] for entry in multi_payload["entries"]}
    assert exported_titles == {"Exciting Feature", "Fix ingest crash"}

    multi_entry_markdown = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            feature_entry_id,
            bugfix_entry_id,
        ],
    )
    assert multi_entry_markdown.exit_code == 0, multi_entry_markdown.output
    assert "# Selected Entries" in multi_entry_markdown.output
    assert "### Exciting Feature" in multi_entry_markdown.output
    assert "### Fix ingest crash" in multi_entry_markdown.output

    get_json_plain = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-j",
            "--no-emoji",
            "--compact",
            "v1.0.0",
        ],
    )
    assert get_json_plain.exit_code == 0, get_json_plain.output
    payload_plain = json.loads(get_json_plain.output)
    assert payload_plain["entries"][0]["title"] == "Remove legacy API"
    assert payload_plain["entries"][0]["type"] == "breaking"
    plain_feature = next(
        entry for entry in payload_plain["entries"] if entry["title"] == "Exciting Feature"
    )
    assert plain_feature["prs"] == [42]
    assert all("🚀" not in entry["title"] for entry in payload_plain["entries"])
    assert all("💥" not in entry["title"] for entry in payload_plain["entries"])

    get_missing_entry = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-c",
            "nonexistent-entry",
        ],
    )
    assert get_missing_entry.exit_code != 0, get_missing_entry.output
    assert "No entry found matching" in get_missing_entry.output

    validate_result = runner.invoke(
        cli,
        ["--root", str(project_dir), "validate"],
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
        f"{plain_prefix}run 'tenzir-changelog add' from your project root or provide --root.\n"
    )
    assert click.utils.strip_ansi(result.output) == expected_plain_output
    assert "Error:" not in result.output


def test_compact_export_style_from_config(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    config_path = project_dir / "config.yaml"
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
            str(project_dir),
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
            str(project_dir),
            "release",
            "v0.1.0",
            "--description",
            "Alpha release.",
            "--yes",
        ],
    )
    assert release_result.exit_code == 0, release_result.output

    release_notes_path = project_dir / "releases" / "v0.1.0" / "notes.md"
    release_notes = release_notes_path.read_text(encoding="utf-8")
    assert "- **Compact Feature**: Adds compact defaults." in release_notes
    assert "### Compact Feature" not in release_notes

    get_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "v0.1.0",
        ],
    )
    assert get_result.exit_code == 0, get_result.output
    assert "Alpha release." not in get_result.output
    assert "- **Compact Feature**: Adds compact defaults." in get_result.output


def test_get_unreleased_token(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "config.yaml").write_text(
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
            str(project_dir),
            "add",
            "--title",
            "Pending Feature",
            "--type",
            "feature",
            "--description",
            "Get unreleased entries via token.",
            "--author",
            "",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    terminal_result = runner.invoke(cli, ["--root", str(project_dir), "show", "-c", "unreleased"])
    assert terminal_result.exit_code == 0, terminal_result.output
    plain_output = click.utils.strip_ansi(terminal_result.output)
    assert "Pending Feature" in plain_output

    dash_terminal = runner.invoke(cli, ["--root", str(project_dir), "show", "-c", "--", "-"])
    assert dash_terminal.exit_code == 0, dash_terminal.output
    dash_output = click.utils.strip_ansi(dash_terminal.output)
    assert "Pending Feature" in dash_output

    markdown_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
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
            str(project_dir),
            "show",
            "-m",
            "--no-emoji",
            "unreleased",
        ],
    )
    assert markdown_plain.exit_code == 0, markdown_plain.output
    assert "### Pending Feature" in markdown_plain.output
    assert "🚀 Pending Feature" not in markdown_plain.output

    markdown_dash = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
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
            str(project_dir),
            "show",
            "-j",
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
            str(project_dir),
            "show",
            "-j",
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
            str(project_dir),
            "show",
            "-j",
            "--",
            "-",
        ],
    )
    assert json_dash.exit_code == 0, json_dash.output
    dash_payload = json.loads(json_dash.output)
    assert dash_payload["entries"][0]["title"] == "Pending Feature"

    list_unreleased = runner.invoke(
        cli,
        ["--root", str(project_dir), "show", "unreleased"],
    )
    assert list_unreleased.exit_code == 0, list_unreleased.output

    list_dash = runner.invoke(
        cli,
        ["--root", str(project_dir), "show", "--", "-"],
    )
    assert list_dash.exit_code == 0, list_dash.output

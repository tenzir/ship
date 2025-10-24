"""Integration-style tests for the tenzir-changelog CLI."""

from __future__ import annotations

import json
import subprocess
import pytest
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

    release_preview = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v1.0.0",
            "--description",
            "First stable release.",
            "--intro-file",
            str(intro_file),
            "--compact",
        ],
    )
    assert release_preview.exit_code == 1
    assert "Re-run with --yes" in click.utils.strip_ansi(release_preview.output)

    release_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
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
    assert "- Removes the deprecated ingest API to prepare for v1. (by @codex)" in release_text
    assert "- Adds an exciting capability. (by @octocat in #42)" in release_text
    assert (
        "- Resolves ingest worker crash when tokens expire. (by @bob in #102 and #115)"
        in release_text
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
    assert manifest_data["description"] == "First stable release."
    assert manifest_data["intro"] == "Welcome to the release!\n\n![Image](assets/hero.png)"
    assert "entries" not in manifest_data
    assert manifest_data.get("title", "").endswith("v1.0.0")

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

    idempotent_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v1.0.0",
        ],
    )
    assert idempotent_result.exit_code == 0, idempotent_result.output
    assert "already up to date" in idempotent_result.output

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
        "- Removes the deprecated ingest API to prepare for v1. (by @codex)" in get_compact.output
    )
    assert "- Adds an exciting capability. (by @octocat in #42)" in get_compact.output
    assert "## 🐞 Bug fixes" in get_compact.output
    assert (
        "- Resolves ingest worker crash when tokens expire. (by @bob in #102 and #115)"
        in get_compact.output
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
        "- Removes the deprecated ingest API to prepare for v1. (by @codex)"
        in get_compact_plain.output
    )
    assert "- Adds an exciting capability. (by @octocat in #42)" in get_compact_plain.output
    assert (
        "- Resolves ingest worker crash when tokens expire. (by @bob in #102 and #115)"
        in get_compact_plain.output
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
            "create",
            "v0.1.0",
            "--description",
            "Alpha release.",
            "--yes",
        ],
    )
    assert release_result.exit_code == 0, release_result.output

    release_notes_path = project_dir / "releases" / "v0.1.0" / "notes.md"
    release_notes = release_notes_path.read_text(encoding="utf-8")
    assert "- Adds compact defaults." in release_notes
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
    assert "- Adds compact defaults." in get_result.output


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


def test_release_create_appends_entries(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    add_alpha = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Alpha Feature",
            "--type",
            "feature",
            "--description",
            "Ships the alpha feature.",
            "--author",
            "codex",
        ],
    )
    assert add_alpha.exit_code == 0, add_alpha.output

    add_beta = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Beta Fix",
            "--type",
            "bugfix",
            "--description",
            "Fixes beta bug.",
            "--author",
            "codex",
        ],
    )
    assert add_beta.exit_code == 0, add_beta.output

    create_initial = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v0.3.0",
            "--yes",
        ],
    )
    assert create_initial.exit_code == 0, create_initial.output

    release_entries_dir = project_dir / "releases" / "v0.3.0" / "entries"
    initial_entries = {path.stem for path in release_entries_dir.glob("*.md")}
    assert len(initial_entries) == 2
    unreleased_dir = project_dir / "unreleased"
    assert not any(unreleased_dir.iterdir())

    add_gamma = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Gamma Change",
            "--type",
            "change",
            "--description",
            "Introduces gamma tweak.",
            "--author",
            "codex",
        ],
    )
    assert add_gamma.exit_code == 0, add_gamma.output

    gamma_entry = next(path.stem for path in unreleased_dir.glob("*.md"))

    append_preview = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v0.3.0",
        ],
    )
    assert append_preview.exit_code == 1
    assert "append 1 new entries" in click.utils.strip_ansi(append_preview.output)

    append_apply = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v0.3.0",
            "--yes",
        ],
    )
    assert append_apply.exit_code == 0, append_apply.output
    new_release_entries = {path.stem for path in release_entries_dir.glob("*.md")}
    assert gamma_entry in new_release_entries
    assert not any(unreleased_dir.iterdir())

    manifest_path = project_dir / "releases" / "v0.3.0" / "manifest.yaml"
    manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert "entries" not in manifest_data
    notes_text = (project_dir / "releases" / "v0.3.0" / "notes.md").read_text(encoding="utf-8")
    assert "Gamma Change" in notes_text


def test_release_create_semver_bumps(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Seed first release explicitly.
    add_alpha = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Alpha",
            "--type",
            "feature",
            "--description",
            "Ships alpha.",
            "--author",
            "codex",
        ],
    )
    assert add_alpha.exit_code == 0, add_alpha.output

    first_release = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v1.2.3",
            "--yes",
        ],
    )
    assert first_release.exit_code == 0, first_release.output

    # Patch bump.
    add_beta = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Beta",
            "--type",
            "bugfix",
            "--description",
            "Fixes beta defect.",
            "--author",
            "codex",
        ],
    )
    assert add_beta.exit_code == 0, add_beta.output

    patch_release = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "--patch",
            "--yes",
        ],
    )
    assert patch_release.exit_code == 0, patch_release.output
    assert (project_dir / "releases" / "v1.2.4").exists()

    # Minor bump should reuse prefix and reset patch component.
    add_gamma = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Gamma",
            "--type",
            "change",
            "--description",
            "Tweaks gamma.",
            "--author",
            "codex",
        ],
    )
    assert add_gamma.exit_code == 0, add_gamma.output

    minor_release = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "--minor",
            "--yes",
        ],
    )
    assert minor_release.exit_code == 0, minor_release.output
    assert (project_dir / "releases" / "v1.3.0").exists()

    # Major bump.
    add_delta = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Delta",
            "--type",
            "feature",
            "--description",
            "Adds delta.",
            "--author",
            "codex",
        ],
    )
    assert add_delta.exit_code == 0, add_delta.output

    major_release = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "--major",
            "--yes",
        ],
    )
    assert major_release.exit_code == 0, major_release.output
    assert (project_dir / "releases" / "v2.0.0").exists()

    # Guard when no baseline exists.
    empty_dir = tmp_path / "another"
    empty_dir.mkdir()
    add_entry = runner.invoke(
        cli,
        [
            "--root",
            str(empty_dir),
            "add",
            "--title",
            "Lone",
            "--type",
            "feature",
            "--description",
            "First entry.",
            "--author",
            "codex",
        ],
    )
    assert add_entry.exit_code == 0, add_entry.output
    bump_without_seed = runner.invoke(
        cli,
        [
            "--root",
            str(empty_dir),
            "release",
            "create",
            "--patch",
            "--yes",
        ],
    )
    assert bump_without_seed.exit_code != 0
    assert "No existing release" in bump_without_seed.output


def test_release_notes_command(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    add_release_entry = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Delta Feature",
            "--type",
            "feature",
            "--description",
            "Adds delta feature.",
            "--author",
            "codex",
        ],
    )
    assert add_release_entry.exit_code == 0, add_release_entry.output

    create_release = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v2.0.0",
            "--description",
            "Second major release.",
            "--yes",
        ],
    )
    assert create_release.exit_code == 0, create_release.output

    add_unreleased_entry = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Epsilon Fix",
            "--type",
            "bugfix",
            "--description",
            "Fixes epsilon bug.",
            "--author",
            "codex",
        ],
    )
    assert add_unreleased_entry.exit_code == 0, add_unreleased_entry.output

    notes_markdown = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "notes",
            "v2.0.0",
        ],
    )
    assert notes_markdown.exit_code == 0, notes_markdown.output
    assert "Second major release." in notes_markdown.output
    assert "Delta Feature" in notes_markdown.output

    notes_json = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "notes",
            "-j",
            "v2.0.0",
        ],
    )
    assert notes_json.exit_code == 0, notes_json.output
    payload = json.loads(notes_json.output)
    assert payload["version"] == "v2.0.0"
    assert payload["entries"][0]["title"] == "Delta Feature"

    notes_unreleased = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "notes",
            "-",
        ],
    )
    assert notes_unreleased.exit_code == 0, notes_unreleased.output
    assert "Unreleased Changes" in notes_unreleased.output
    assert "Epsilon Fix" in notes_unreleased.output


def test_release_publish_uses_gh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    add_entry = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Zeta Launch",
            "--type",
            "feature",
            "--description",
            "Finalizes zeta work.",
            "--author",
            "codex",
        ],
    )
    assert add_entry.exit_code == 0, add_entry.output

    create_release = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v3.0.0",
            "--yes",
        ],
    )
    assert create_release.exit_code == 0, create_release.output

    config_path = project_dir / "config.yaml"
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config_data["repository"] = "tenzir/example"
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")

    recorded_command: dict[str, list[str] | bool] = {}
    commands: list[list[str]] = []

    def fake_which(command: str) -> str:
        assert command == "gh"
        return "/usr/bin/gh"

    def fake_run(args: list[str], *, check: bool, stdout=None, stderr=None) -> None:
        commands.append(args)
        if len(args) >= 3 and args[1:3] == ["release", "view"]:
            raise subprocess.CalledProcessError(returncode=1, cmd=args)
        recorded_command["args"] = args
        recorded_command["check"] = check

    monkeypatch.setattr("tenzir_changelog.cli.shutil.which", fake_which)
    monkeypatch.setattr("tenzir_changelog.cli.subprocess.run", fake_run)

    publish_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "publish",
            "v3.0.0",
            "--yes",
        ],
    )
    assert publish_result.exit_code == 0, publish_result.output
    assert recorded_command["check"] is True
    args = recorded_command["args"]
    assert args[:3] == ["/usr/bin/gh", "release", "create"]
    assert "v3.0.0" in args
    assert "--repo" in args and "tenzir/example" in args
    assert "--notes-file" in args
    # Ensure existence check ran first.
    assert commands[0][:3] == ["/usr/bin/gh", "release", "view"]


def test_release_publish_updates_existing_release(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    add_entry = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Eta Update",
            "--type",
            "feature",
            "--description",
            "Ships eta.",
            "--author",
            "codex",
        ],
    )
    assert add_entry.exit_code == 0, add_entry.output

    create_release = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v4.0.0",
            "--yes",
        ],
    )
    assert create_release.exit_code == 0, create_release.output

    config_path = project_dir / "config.yaml"
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config_data["repository"] = "tenzir/example"
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")

    calls: list[list[str]] = []

    def fake_which(command: str) -> str:
        assert command == "gh"
        return "/usr/bin/gh"

    def fake_run(args: list[str], *, check: bool, stdout=None, stderr=None) -> None:
        calls.append(args)
        if len(args) >= 3 and args[1:3] == ["release", "edit"]:
            return
        if len(args) >= 3 and args[1:3] == ["release", "view"]:
            return  # release exists
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr("tenzir_changelog.cli.shutil.which", fake_which)
    monkeypatch.setattr("tenzir_changelog.cli.subprocess.run", fake_run)

    publish_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "publish",
            "v4.0.0",
            "--yes",
        ],
    )
    assert publish_result.exit_code == 0, publish_result.output
    assert calls[0][:3] == ["/usr/bin/gh", "release", "view"]
    assert calls[1][:3] == ["/usr/bin/gh", "release", "edit"]

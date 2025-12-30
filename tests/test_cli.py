"""Integration-style tests for the tenzir-changelog CLI."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import date, datetime
from pathlib import Path

import click
import pytest
import yaml
from click.testing import CliRunner

from tenzir_changelog import __version__
from tenzir_changelog.cli import INFO_PREFIX, cli, main
from tenzir_changelog.config import Config, save_config
from tenzir_changelog.entries import read_entry, write_entry


def test_cli_version_option(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--version"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == __version__


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

    feature_entry_matches = list(entries_dir.glob("exciting-feature.md"))
    assert feature_entry_matches
    feature_entry = feature_entry_matches[0]
    assert feature_entry.stem == "exciting-feature"
    entry_text = feature_entry.read_text(encoding="utf-8")
    assert "created:" in entry_text
    assert "pr: 42" in entry_text  # singular form for single PR
    assert "project:" not in entry_text
    parsed_entry = read_entry(feature_entry)
    assert isinstance(parsed_entry.metadata["created"], datetime)
    assert parsed_entry.created_at == parsed_entry.metadata["created"]

    breaking_entry_matches = list(entries_dir.glob("remove-legacy-api.md"))
    assert breaking_entry_matches
    breaking_entry = breaking_entry_matches[0]
    breaking_text = breaking_entry.read_text(encoding="utf-8")
    assert "type: breaking" in breaking_text
    assert "Removes the deprecated ingest API to prepare for v1." in breaking_text

    bugfix_entry_matches = list(entries_dir.glob("fix-ingest-crash.md"))
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
            "--intro-file",
            str(intro_file),
            "--compact",
        ],
    )
    assert release_preview.exit_code == 1
    assert "re-run with --yes to apply these updates." in click.utils.strip_ansi(
        release_preview.output
    )

    release_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v1.0.0",
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
    assert "Welcome to the release!" in release_text
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
    assert "description" not in manifest_data
    assert manifest_data["intro"] == "Welcome to the release!\n\n![Image](assets/hero.png)"
    assert "entries" not in manifest_data
    assert manifest_data.get("title", "").endswith("v1.0.0")

    release_entries_dir = release_dir / "entries"
    assert release_entries_dir.is_dir()
    assert list(release_entries_dir.glob("exciting-feature.md"))
    assert list(release_entries_dir.glob("remove-legacy-api.md"))
    assert list(release_entries_dir.glob("fix-ingest-crash.md"))
    release_entry_stems = {path.stem for path in release_entries_dir.glob("*.md")}
    assert "exciting-feature" in release_entry_stems
    assert "remove-legacy-api" in release_entry_stems
    assert "fix-ingest-crash" in release_entry_stems
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
    assert breaking_entry["authors"] == [{"handle": "codex", "url": "https://github.com/codex"}]
    assert breaking_entry.get("excerpt") == "Removes the deprecated ingest API to prepare for v1."
    feature_entry = next(
        entry for entry in payload["entries"] if entry["title"] == "Exciting Feature"
    )
    assert feature_entry["prs"] == [{"number": 42}]
    assert "pr" not in feature_entry
    assert feature_entry["project"] == "project"
    assert feature_entry.get("excerpt") == "Adds an exciting capability."

    bugfix_entry = next(
        entry for entry in payload["entries"] if entry["title"] == "Fix ingest crash"
    )
    assert bugfix_entry["prs"] == [{"number": 102}, {"number": 115}]
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
    assert single_payload["entries"][0]["prs"] == [{"number": 42}]
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
    assert plain_feature["prs"] == [{"number": 42}]
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


def test_add_infers_metadata_from_gh_context(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    gh_stub = project_dir / "gh"
    gh_stub.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import sys",
                "args = sys.argv[1:]",
                "if len(args) >= 2 and args[0] == 'api' and args[1] == 'user':",
                "    sys.stdout.write('codex\\n')",
                "    sys.exit(0)",
                "if len(args) >= 2 and args[0] == 'pr' and args[1] == 'view':",
                "    sys.stdout.write('123\\n')",
                "    sys.exit(0)",
                "sys.exit(1)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    gh_stub.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{project_dir}{os.pathsep}{env.get('PATH', '')}"
    for key in (
        "TENZIR_CHANGELOG_AUTHOR",
        "GH_USERNAME",
        "GH_USER",
        "GITHUB_ACTOR",
        "GITHUB_USER",
    ):
        env[key] = ""

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "GH Context Entry",
            "--type",
            "feature",
            "--description",
            "Entry inherits metadata from gh.",
        ],
        env=env,
    )
    assert add_result.exit_code == 0, add_result.output

    entries_dir = project_dir / "unreleased"
    entry_files = list(entries_dir.glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    assert entry.metadata["authors"] == ["codex"]
    assert entry.metadata["prs"] == [123]


def _create_project_with_entry(
    root: Path,
    project_id: str,
    project_name: str,
    *,
    entry_id: str,
    title: str,
    created: datetime | date,
    entry_type: str = "feature",
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    save_config(Config(id=project_id, name=project_name), root / "config.yaml")
    write_entry(
        root,
        {
            "title": title,
            "type": entry_type,
            "created": created,
        },
        body=f"{title} body.",
        entry_id=entry_id,
        default_project=project_id,
    )


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


def _write_package_metadata(path: Path, *, package_id: str = "pkg", name: str = "Package") -> None:
    path.write_text(
        yaml.safe_dump({"id": package_id, "name": name}, sort_keys=False),
        encoding="utf-8",
    )


def test_package_mode_uses_package_metadata(tmp_path: Path) -> None:
    runner = CliRunner()
    package_dir = tmp_path / "demo"
    changelog_root = package_dir / "changelog"
    changelog_root.mkdir(parents=True)
    _write_package_metadata(package_dir / "package.yaml")

    result = runner.invoke(cli, ["--root", str(changelog_root), "show"])
    assert result.exit_code == 0, result.output


def test_package_mode_requires_id_and_name(tmp_path: Path) -> None:
    runner = CliRunner()
    package_dir = tmp_path / "broken"
    changelog_root = package_dir / "changelog"
    changelog_root.mkdir(parents=True)
    (package_dir / "package.yaml").write_text(yaml.safe_dump({"id": "pkg"}), encoding="utf-8")

    result = runner.invoke(cli, ["--root", str(changelog_root), "show"])
    assert result.exit_code == 1
    assert "missing required 'name'" in result.output


def test_package_mode_detects_root_from_package_directories(tmp_path: Path) -> None:
    runner = CliRunner()
    package_dir = tmp_path / "workspace"
    changelog_root = package_dir / "changelog"
    changelog_root.mkdir(parents=True)
    _write_package_metadata(package_dir / "package.yaml", package_id="workspace", name="Workspace")

    original_cwd = os.getcwd()
    try:
        os.chdir(package_dir)
        package_invocation = runner.invoke(cli, ["show"])
    finally:
        os.chdir(original_cwd)
    assert package_invocation.exit_code == 0, package_invocation.output

    try:
        os.chdir(changelog_root)
        changelog_invocation = runner.invoke(cli, ["show"])
    finally:
        os.chdir(original_cwd)
    assert changelog_invocation.exit_code == 0, changelog_invocation.output


def test_package_mode_bootstraps_changelog_from_package_root(tmp_path: Path) -> None:
    runner = CliRunner()
    package_dir = tmp_path / "workspace"
    package_dir.mkdir()
    _write_package_metadata(package_dir / "package.yaml", package_id="workspace", name="Workspace")

    original_cwd = os.getcwd()
    try:
        os.chdir(package_dir)
        result = runner.invoke(
            cli,
            [
                "add",
                "--title",
                "Bootstrap Package",
                "--type",
                "feature",
                "--author",
                "codex",
                "--description",
                "Initialized changelog project from package root.",
            ],
            env={"EDITOR": "true"},
        )
    finally:
        os.chdir(original_cwd)

    assert result.exit_code == 0, result.output

    changelog_root = package_dir / "changelog"
    assert changelog_root.is_dir()
    assert (changelog_root / "unreleased").is_dir()
    assert not (changelog_root / "releases").exists()

    created_entries = list((changelog_root / "unreleased").glob("*.md"))
    assert created_entries, "Expected an entry to be created in package mode"

    assert not (package_dir / "config.yaml").exists()
    assert not (changelog_root / "config.yaml").exists()


def test_bootstrap_creates_changelog_subdirectory(tmp_path: Path) -> None:
    """Running add in empty directory should create changelog/ subdirectory."""
    runner = CliRunner()
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()

    original_cwd = os.getcwd()
    try:
        os.chdir(project_dir)
        result = runner.invoke(
            cli,
            [
                "add",
                "--title",
                "First entry",
                "--type",
                "feature",
                "--author",
                "test",
                "--description",
                "Test description.",
            ],
            env={"EDITOR": "true"},
        )
    finally:
        os.chdir(original_cwd)

    assert result.exit_code == 0, result.output

    # Should create changelog/ subdirectory, not in project root
    changelog_root = project_dir / "changelog"
    assert changelog_root.is_dir()
    assert (changelog_root / "config.yaml").exists()
    assert (changelog_root / "unreleased").is_dir()

    # Should NOT create in project root
    assert not (project_dir / "config.yaml").exists()
    assert not (project_dir / "unreleased").exists()


def test_add_handles_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    save_config(Config(id="project", name="Project"), project_dir / "config.yaml")

    def raise_interrupt(*_: object, **__: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("tenzir_changelog.cli.click.edit", raise_interrupt)

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Interrupted",
            "--type",
            "feature",
            "--author",
            "codex",
        ],
    )

    assert result.exit_code == 130
    plain_output = click.utils.strip_ansi(result.output)
    assert "operation cancelled by user (Ctrl+C)." in plain_output


def test_show_orders_rows_oldest_to_newest(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    save_config(Config(id="project", name="Project"), project_dir / "config.yaml")

    write_entry(
        project_dir,
        {
            "title": "Oldest",
            "type": "change",
            "created": date(2024, 1, 1),
        },
        "First body",
        default_project="project",
    )
    write_entry(
        project_dir,
        {
            "title": "Middle",
            "type": "change",
            "created": date(2024, 2, 1),
        },
        "Second body",
        default_project="project",
    )
    write_entry(
        project_dir,
        {
            "title": "Newest",
            "type": "change",
            "created": date(2024, 3, 1),
        },
        "Third body",
        default_project="project",
    )

    result = runner.invoke(cli, ["--root", str(project_dir), "show"])
    assert result.exit_code == 0, result.output

    plain_output = click.utils.strip_ansi(result.output)
    data_rows = [line for line in plain_output.splitlines() if line.startswith("│")]
    row_numbers = [row.split("│")[1].strip() for row in data_rows]
    assert row_numbers == ["3", "2", "1"]
    assert [row.split("│")[4].strip() for row in data_rows] == ["Oldest", "Middle", "Newest"]
    dates = [row.split("│")[2].strip() for row in data_rows]
    assert dates == sorted(dates)

    newest_card = runner.invoke(cli, ["--root", str(project_dir), "show", "-c", "1"])
    assert newest_card.exit_code == 0, newest_card.output
    newest_plain = click.utils.strip_ansi(newest_card.output)
    assert "Newest" in newest_plain
    assert "Middle" not in newest_plain
    assert "Oldest" not in newest_plain

    oldest_card = runner.invoke(cli, ["--root", str(project_dir), "show", "-c", "3"])
    assert oldest_card.exit_code == 0, oldest_card.output
    oldest_plain = click.utils.strip_ansi(oldest_card.output)
    assert "Oldest" in oldest_plain


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
            "--intro",
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


def test_component_filtering(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "config.yaml").write_text(
        "\n".join(
            [
                "id: sample",
                "name: Sample Project",
                "components:",
                "  - cli",
                "  - docs",
            ]
        ),
        encoding="utf-8",
    )

    add_cli = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "CLI Entry",
            "--type",
            "change",
            "--component",
            "cli",
            "--description",
            "Touches the CLI.",
            "--author",
            "codex",
        ],
    )
    assert add_cli.exit_code == 0, add_cli.output

    add_docs = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Docs Entry",
            "--type",
            "feature",
            "--component",
            "docs",
            "--description",
            "Updates documentation.",
            "--author",
            "codex",
        ],
    )
    assert add_docs.exit_code == 0, add_docs.output

    table_docs = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "--component",
            "docs",
        ],
    )
    assert table_docs.exit_code == 0, table_docs.output
    table_plain = click.utils.strip_ansi(table_docs.output)
    assert "Docs Entry" in table_plain
    assert "CLI Entry" not in table_plain

    markdown_docs = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "--component",
            "docs",
            "unreleased",
        ],
    )
    assert markdown_docs.exit_code == 0, markdown_docs.output
    assert "CLI Entry" not in markdown_docs.output

    json_docs = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-j",
            "--component",
            "docs",
            "unreleased",
        ],
    )
    assert json_docs.exit_code == 0, json_docs.output
    payload = json.loads(json_docs.output)
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["title"] == "Docs Entry"
    assert payload["entries"][0]["components"] == ["docs"]

    bad_filter = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "--component",
            "qa",
        ],
    )
    assert bad_filter.exit_code != 0
    assert "Unknown component filter" in bad_filter.output


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


def test_release_notes_collapse_soft_breaks(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    save_config(Config(id="project", name="Project"), project_dir / "config.yaml")

    metadata = {
        "title": "Invert show table order",
        "type": "breaking",
        "authors": ["codex"],
    }
    body = (
        "`tenzir-changelog show` now renders the primary changelog table with\n"
        "backward-counting row numbers, so `#1` consistently targets the newest change\n"
        "while older entries climb toward the top.\n"
    )
    write_entry(project_dir, metadata, body, default_project="project")

    create_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v0.1.0",
            "--intro",
            "Test release.",
            "--yes",
        ],
    )
    assert create_result.exit_code == 0, create_result.output

    notes_path = project_dir / "releases" / "v0.1.0" / "notes.md"
    assert notes_path.exists()
    notes_text = notes_path.read_text(encoding="utf-8")
    assert "table with backward-counting row numbers" in notes_text
    assert "table with\nbackward-counting" not in notes_text


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
            "--intro",
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

    recorded_args: list[str] = []
    recorded_check: bool = False
    commands: list[list[str]] = []

    def fake_which(command: str) -> str:
        assert command == "gh"
        return "/usr/bin/gh"

    def fake_run(
        args: list[str], *, check: bool, stdout: object = None, stderr: object = None
    ) -> None:
        nonlocal recorded_args, recorded_check
        commands.append(args)
        if len(args) >= 3 and args[1:3] == ["release", "view"]:
            raise subprocess.CalledProcessError(returncode=1, cmd=args)
        recorded_args = args
        recorded_check = check

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
    assert recorded_check is True
    assert recorded_args[:3] == ["/usr/bin/gh", "release", "create"]
    assert "v3.0.0" in recorded_args
    assert "--repo" in recorded_args and "tenzir/example" in recorded_args
    assert "--notes-file" in recorded_args
    # Ensure existence check ran first.
    assert commands[0][:3] == ["/usr/bin/gh", "release", "view"]


def test_release_publish_updates_existing_release(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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

    def fake_run(
        args: list[str], *, check: bool, stdout: object = None, stderr: object = None
    ) -> None:
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


def test_release_publish_handles_abort(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
            "Abort Test",
            "--type",
            "feature",
            "--description",
            "Used to simulate ctrl-c.",
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
            "v5.0.0",
            "--yes",
        ],
    )
    assert create_release.exit_code == 0, create_release.output

    config_path = project_dir / "config.yaml"
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config_data["repository"] = "tenzir/example"
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")

    def fake_which(command: str) -> str:
        assert command == "gh"
        return "/usr/bin/gh"

    def fake_run(
        args: list[str], *, check: bool, stdout: object = None, stderr: object = None
    ) -> None:
        if len(args) >= 3 and args[1:3] == ["release", "view"]:
            return
        raise AssertionError("gh CLI should not run when publish is aborted")

    def fake_confirm(*args: object, **kwargs: object) -> bool:
        raise click.Abort()

    monkeypatch.setattr("tenzir_changelog.cli.shutil.which", fake_which)
    monkeypatch.setattr("tenzir_changelog.cli.subprocess.run", fake_run)
    monkeypatch.setattr("tenzir_changelog.cli.click.confirm", fake_confirm)

    publish_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "publish",
            "v5.0.0",
        ],
    )

    assert publish_result.exit_code == 130
    plain_output = click.utils.strip_ansi(publish_result.output)
    assert "operation cancelled by user (Ctrl+C)." in plain_output


def test_release_publish_creates_git_tag(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Initialize a Git repository with a single commit.
    subprocess.run(["git", "init"], cwd=project_dir, check=True, stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.com"],
        cwd=project_dir,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"],
        cwd=project_dir,
        check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=project_dir,
        check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=project_dir,
        check=True,
    )
    remote_dir = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote_dir)],
        check=True,
        stdout=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_dir)],
        cwd=project_dir,
        check=True,
    )
    (project_dir / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit", "--no-gpg-sign"],
        cwd=project_dir,
        check=True,
        stdout=subprocess.PIPE,
    )

    # Write minimal configuration and release artifacts.
    config_path = project_dir / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "id": "demo",
                "name": "Demo",
                "repository": "tenzir/example",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    release_dir = project_dir / "releases" / "v9.9.9"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.yaml").write_text(
        "version: v9.9.9\ncreated: 2024-01-01\n",
        encoding="utf-8",
    )
    (release_dir / "notes.md").write_text("Ready for launch.\n", encoding="utf-8")

    # Stub the gh CLI so the publish command can run end-to-end.
    gh_log = project_dir / "gh.log"
    gh_stub = project_dir / "gh"
    gh_stub.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import os",
                "import sys",
                "from pathlib import Path",
                "log = os.environ.get('GH_LOG')",
                "if log:",
                "    with open(log, 'a', encoding='utf-8') as handle:",
                "        handle.write(' '.join(sys.argv[1:]) + '\\n')",
                "if len(sys.argv) >= 3 and sys.argv[1] == 'release' and sys.argv[2] == 'view':",
                "    sys.exit(1)",
                "sys.exit(0)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    gh_stub.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{project_dir}{os.pathsep}{env.get('PATH', '')}"
    env["GH_LOG"] = str(gh_log)

    publish_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "publish",
            "v9.9.9",
            "--tag",
            "--yes",
        ],
        env=env,
    )

    assert publish_result.exit_code == 0, publish_result.output
    publish_plain = click.utils.strip_ansi(publish_result.output)
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    branch_name = branch_result.stdout.strip()
    assert branch_name
    assert f"pushed branch {branch_name} to remote origin/{branch_name}." in publish_plain
    assert "pushed git tag v9.9.9 to remote origin." in publish_plain

    tag_result = subprocess.run(
        ["git", "tag", "--list", "v9.9.9"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "v9.9.9" in [line.strip() for line in tag_result.stdout.splitlines()]

    gh_calls = gh_log.read_text(encoding="utf-8").strip().splitlines()
    assert any(line.startswith("release create v9.9.9") for line in gh_calls)


def test_release_publish_skips_existing_tag(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    subprocess.run(["git", "init"], cwd=project_dir, check=True, stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.com"],
        cwd=project_dir,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"],
        cwd=project_dir,
        check=True,
    )
    remote_dir = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote_dir)],
        check=True,
        stdout=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_dir)],
        cwd=project_dir,
        check=True,
    )
    (project_dir / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit", "--no-gpg-sign"],
        cwd=project_dir,
        check=True,
        stdout=subprocess.PIPE,
    )

    config_path = project_dir / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "id": "demo",
                "name": "Demo",
                "repository": "tenzir/example",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    release_dir = project_dir / "releases" / "v9.9.9"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.yaml").write_text(
        "version: v9.9.9\ncreated: 2024-01-01\n",
        encoding="utf-8",
    )
    (release_dir / "notes.md").write_text("Ready for launch.\n", encoding="utf-8")

    subprocess.run(
        ["git", "tag", "-a", "v9.9.9", "-m", "Existing release"],
        cwd=project_dir,
        check=True,
        stdout=subprocess.PIPE,
    )

    gh_log = project_dir / "gh.log"
    gh_stub = project_dir / "gh"
    gh_stub.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import os",
                "import sys",
                "log = os.environ.get('GH_LOG')",
                "if log:",
                "    with open(log, 'a', encoding='utf-8') as handle:",
                "        handle.write(' '.join(sys.argv[1:]) + '\\n')",
                "if len(sys.argv) >= 3 and sys.argv[1] == 'release' and sys.argv[2] == 'view':",
                "    sys.exit(1)",
                "sys.exit(0)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    gh_stub.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{project_dir}{os.pathsep}{env.get('PATH', '')}"
    env["GH_LOG"] = str(gh_log)

    publish_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "publish",
            "v9.9.9",
            "--tag",
            "--yes",
        ],
        env=env,
    )

    assert publish_result.exit_code == 0, publish_result.output

    publish_plain = click.utils.strip_ansi(publish_result.output)
    assert "git tag v9.9.9 already exists; skipping creation." in publish_plain
    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    branch_name = branch_result.stdout.strip()
    assert branch_name
    assert f"pushed branch {branch_name} to remote origin/{branch_name}." in publish_plain
    assert "pushed git tag v9.9.9 to remote origin." in publish_plain

    gh_calls = gh_log.read_text(encoding="utf-8").strip().splitlines()
    assert any(line.startswith("release create v9.9.9") for line in gh_calls)


def test_add_description_file(tmp_path: Path) -> None:
    """Test --description-file reads content from a file."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    desc_file = tmp_path / "desc.md"
    desc_file.write_text("This is the description from a file.", encoding="utf-8")

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "File Description Test",
            "--type",
            "feature",
            "--description-file",
            str(desc_file),
        ],
        env={"TENZIR_CHANGELOG_AUTHOR": "test-user"},
    )
    assert result.exit_code == 0, result.output

    entry_files = list((project_dir / "unreleased").glob("*.md"))
    assert len(entry_files) == 1
    content = entry_files[0].read_text(encoding="utf-8")
    assert "This is the description from a file." in content


def test_add_description_file_stdin(tmp_path: Path) -> None:
    """Test --description-file - reads from stdin."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Stdin Description Test",
            "--type",
            "feature",
            "--description-file",
            "-",
        ],
        input="Description from stdin.",
        env={"TENZIR_CHANGELOG_AUTHOR": "test-user"},
    )
    assert result.exit_code == 0, result.output

    entry_files = list((project_dir / "unreleased").glob("*.md"))
    assert len(entry_files) == 1
    content = entry_files[0].read_text(encoding="utf-8")
    assert "Description from stdin." in content


def test_add_description_mutual_exclusivity(tmp_path: Path) -> None:
    """Test that --description and --description-file cannot be used together."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    desc_file = tmp_path / "desc.md"
    desc_file.write_text("File content", encoding="utf-8")

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Mutual Exclusivity Test",
            "--type",
            "feature",
            "--description",
            "Inline text",
            "--description-file",
            str(desc_file),
        ],
    )
    assert result.exit_code != 0
    assert "Use only one of --description or --description-file" in result.output


def test_add_description_file_not_found(tmp_path: Path) -> None:
    """Test error handling for missing description file."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Missing File Test",
            "--type",
            "feature",
            "--description-file",
            str(tmp_path / "nonexistent.md"),
        ],
    )
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_add_description_file_empty(tmp_path: Path) -> None:
    """Test that empty description file results in empty body."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    desc_file = tmp_path / "empty.md"
    desc_file.write_text("", encoding="utf-8")

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Empty File Test",
            "--type",
            "feature",
            "--description-file",
            str(desc_file),
        ],
        env={"TENZIR_CHANGELOG_AUTHOR": "test-user"},
    )
    assert result.exit_code == 0, result.output

    entry_files = list((project_dir / "unreleased").glob("*.md"))
    assert len(entry_files) == 1


def test_add_co_author_with_explicit_author(tmp_path: Path) -> None:
    """Test that --co-author is additive to explicit --author."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Co-authored Feature",
            "--type",
            "feature",
            "--description",
            "A feature with multiple authors.",
            "--author",
            "mavam",
            "--co-author",
            "claude",
        ],
    )
    assert result.exit_code == 0, result.output

    entry_files = list((project_dir / "unreleased").glob("*.md"))
    assert len(entry_files) == 1
    entry_text = entry_files[0].read_text(encoding="utf-8")
    # Both authors should be present
    assert "authors:" in entry_text
    assert "mavam" in entry_text
    assert "claude" in entry_text


def test_add_multiple_co_authors(tmp_path: Path) -> None:
    """Test that multiple --co-author flags work correctly."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Multi Co-authored Feature",
            "--type",
            "feature",
            "--description",
            "A feature with many authors.",
            "--author",
            "mavam",
            "--co-author",
            "claude",
            "--co-author",
            "copilot",
        ],
    )
    assert result.exit_code == 0, result.output

    entry_files = list((project_dir / "unreleased").glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    assert entry.metadata.get("authors") == ["mavam", "claude", "copilot"]


def test_add_co_author_deduplication(tmp_path: Path) -> None:
    """Test that duplicate authors are removed while preserving order."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Deduplicated Feature",
            "--type",
            "feature",
            "--description",
            "A feature with duplicate authors.",
            "--author",
            "mavam",
            "--co-author",
            "mavam",
            "--co-author",
            "claude",
        ],
    )
    assert result.exit_code == 0, result.output

    entry_files = list((project_dir / "unreleased").glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    # mavam should appear only once, order preserved
    assert entry.metadata.get("authors") == ["mavam", "claude"]


def test_add_co_author_without_explicit_author(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that --co-author triggers author inference and adds to it."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Mock the GitHub login detection to return a known value
    monkeypatch.setenv("TENZIR_CHANGELOG_AUTHOR", "inferred-user")

    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Inferred Co-authored Feature",
            "--type",
            "feature",
            "--description",
            "A feature using inference plus co-author.",
            "--co-author",
            "claude",
        ],
    )
    assert result.exit_code == 0, result.output

    entry_files = list((project_dir / "unreleased").glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    # Should have inferred user first, then co-author
    assert entry.metadata.get("authors") == ["inferred-user", "claude"]


def test_explicit_links_flag_in_show_command(tmp_path: Path) -> None:
    """Test that --explicit-links converts @mentions and PRs to Markdown links."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # First create a config with repository set (needed for PR links)
    config_path = project_dir / "config.yaml"
    config_path.write_text(
        "id: test-project\nname: Test Project\nrepository: octocat/test-repo\n",
        encoding="utf-8",
    )

    # Create an entry with an author and PR
    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Explicit Links Test",
            "--type",
            "feature",
            "--description",
            "A test entry.",
            "--author",
            "octocat",
            "--pr",
            "42",
        ],
    )
    assert result.exit_code == 0, result.output

    # Test without --explicit-links (default) - plain references
    show_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "unreleased",
        ],
    )
    assert show_result.exit_code == 0, show_result.output
    # Should have plain @mention and plain #PR
    assert "@octocat" in show_result.output
    assert "#42" in show_result.output
    assert "[@octocat](https://github.com/octocat)" not in show_result.output
    assert "[#42](https://github.com/octocat/test-repo/pull/42)" not in show_result.output

    # Test with --explicit-links - full Markdown links
    show_linked_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "--explicit-links",
            "unreleased",
        ],
    )
    assert show_linked_result.exit_code == 0, show_linked_result.output
    # Should have linked @mention and linked PR
    assert "[@octocat](https://github.com/octocat)" in show_linked_result.output
    assert "[#42](https://github.com/octocat/test-repo/pull/42)" in show_linked_result.output


def test_explicit_links_flag_in_release_notes_command(tmp_path: Path) -> None:
    """Test that --explicit-links works in release notes command."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create a config with repository set
    config_path = project_dir / "config.yaml"
    config_path.write_text(
        "id: test-project\nname: Test Project\nrepository: octocat/test-repo\n",
        encoding="utf-8",
    )

    # Create an entry with an author and PR
    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Release Notes Link Test",
            "--type",
            "feature",
            "--description",
            "A test entry.",
            "--author",
            "octocat",
            "--pr",
            "99",
        ],
    )
    assert result.exit_code == 0, result.output

    # Create a release
    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v1.0.0",
            "--yes",
        ],
    )
    assert result.exit_code == 0, result.output

    # Test without --explicit-links (default)
    notes_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "notes",
            "v1.0.0",
        ],
    )
    assert notes_result.exit_code == 0, notes_result.output
    # Should have plain @mention and plain #PR
    assert "@octocat" in notes_result.output
    assert "#99" in notes_result.output
    assert "[@octocat](https://github.com/octocat)" not in notes_result.output

    # Test with --explicit-links
    notes_linked_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "notes",
            "--explicit-links",
            "v1.0.0",
        ],
    )
    assert notes_linked_result.exit_code == 0, notes_linked_result.output
    # Should have linked @mention and linked PR
    assert "[@octocat](https://github.com/octocat)" in notes_linked_result.output
    assert "[#99](https://github.com/octocat/test-repo/pull/99)" in notes_linked_result.output


def test_explicit_links_preserves_full_names(tmp_path: Path) -> None:
    """Test that --explicit-links preserves full names without linking."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create an entry with a full name author (contains spaces)
    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Full Name Author Test",
            "--type",
            "feature",
            "--description",
            "A test entry.",
            "--author",
            "Jane Doe",
        ],
    )
    assert result.exit_code == 0, result.output

    # Test with --explicit-links
    show_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "--explicit-links",
            "unreleased",
        ],
    )
    assert show_result.exit_code == 0, show_result.output
    # Full names should NOT be linked (no @-prefix, no link)
    assert "Jane Doe" in show_result.output
    assert "[@Jane Doe]" not in show_result.output


def test_explicit_links_without_repository(tmp_path: Path) -> None:
    """Test --explicit-links behavior when no repository is configured."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # No repository in config - just id and name
    config_path = project_dir / "config.yaml"
    config_path.write_text(
        "id: test-project\nname: Test Project\n",
        encoding="utf-8",
    )

    # Create an entry with a GitHub handle author and PR
    result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "No Repo Test",
            "--type",
            "feature",
            "--description",
            "A test entry.",
            "--author",
            "octocat",
            "--pr",
            "42",
        ],
    )
    assert result.exit_code == 0, result.output

    # Test with --explicit-links but no repository configured
    show_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "show",
            "-m",
            "--explicit-links",
            "unreleased",
        ],
    )
    assert show_result.exit_code == 0, show_result.output
    # Author should still be linked (GitHub profiles work independently)
    assert "[@octocat](https://github.com/octocat)" in show_result.output
    # PR should NOT be linked (no repository to construct URL)
    assert "#42" in show_result.output
    assert "[#42](" not in show_result.output


def test_release_create_emits_only_version_to_stdout(tmp_path: Path) -> None:
    """Verify that release create emits only the version to stdout.

    Status messages (checkmarks, info) must go to stderr so that scripts
    can capture just the version via stdout without ANSI pollution.
    """
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create an entry to release.
    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Feature",
            "--type",
            "feature",
            "--description",
            "A test feature.",
            "--author",
            "tester",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    # Create a release and capture stdout/stderr separately.
    release_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "create",
            "v1.0.0",
            "--yes",
        ],
        catch_exceptions=False,
    )
    assert release_result.exit_code == 0, release_result.output

    # stdout must contain ONLY the version string (with trailing newline).
    assert release_result.stdout.strip() == "v1.0.0"

    # stderr must contain the status messages.
    assert "release manifest written" in release_result.stderr

    # stdout must NOT contain status messages or ANSI codes.
    assert "manifest" not in release_result.stdout
    assert "\033[" not in release_result.stdout


def test_release_create_rejects_non_semver_version(tmp_path: Path) -> None:
    """Test release create enforces semantic versioning."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Feature",
            "--type",
            "feature",
            "--description",
            "A test feature.",
            "--author",
            "tester",
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
            "not-a-version",
            "--yes",
        ],
    )
    assert release_result.exit_code != 0
    assert "valid semantic version" in release_result.output


def test_release_version_command(tmp_path: Path) -> None:
    """Test the release version command outputs the latest version."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create an entry and release.
    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Feature",
            "--type",
            "feature",
            "--description",
            "A test feature.",
            "--author",
            "tester",
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
            "v2.0.0",
            "--yes",
        ],
    )
    assert release_result.exit_code == 0, release_result.output

    # Get the version.
    version_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "version",
        ],
    )
    assert version_result.exit_code == 0, version_result.output
    assert version_result.stdout.strip() == "v2.0.0"


def test_release_version_bare_flag(tmp_path: Path) -> None:
    """Test the release version --bare flag strips the v prefix."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create an entry and release.
    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Feature",
            "--type",
            "feature",
            "--description",
            "A test feature.",
            "--author",
            "tester",
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
            "v3.1.4",
            "--yes",
        ],
    )
    assert release_result.exit_code == 0, release_result.output

    # Get the version with --bare.
    version_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "version",
            "--bare",
        ],
    )
    assert version_result.exit_code == 0, version_result.output
    assert version_result.stdout.strip() == "3.1.4"


def test_release_version_no_releases(tmp_path: Path) -> None:
    """Test the release version command fails when no releases exist."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Initialize project without any releases.
    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Feature",
            "--type",
            "feature",
            "--description",
            "A test feature.",
            "--author",
            "tester",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    # Get the version should fail.
    version_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "version",
        ],
    )
    assert version_result.exit_code != 0
    assert "No releases found" in version_result.output


def test_release_publish_defaults_to_latest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that release publish without version uses the latest release."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create an entry and release.
    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Feature",
            "--type",
            "feature",
            "--description",
            "A test feature.",
            "--author",
            "tester",
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
            "v1.5.0",
            "--yes",
        ],
    )
    assert release_result.exit_code == 0, release_result.output

    # Set up a config with repository so publish doesn't complain about missing repo.
    config_path = project_dir / "config.yaml"
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config_data["repository"] = "owner/repo"
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")

    # Mock the gh CLI to capture what version is being published.
    recorded_args: list[str] = []
    commands: list[list[str]] = []

    def fake_which(command: str) -> str:
        assert command == "gh"
        return "/usr/bin/gh"

    def fake_run(
        args: list[str], *, check: bool, stdout: object = None, stderr: object = None
    ) -> None:
        nonlocal recorded_args
        commands.append(args)
        if len(args) >= 3 and args[1:3] == ["release", "view"]:
            raise subprocess.CalledProcessError(returncode=1, cmd=args)
        recorded_args = args

    monkeypatch.setattr("tenzir_changelog.cli.shutil.which", fake_which)
    monkeypatch.setattr("tenzir_changelog.cli.subprocess.run", fake_run)

    # Publish without specifying version.
    publish_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "release",
            "publish",
            "--yes",
        ],
    )
    assert publish_result.exit_code == 0, publish_result.output

    # Verify that gh was called with v1.5.0 (the latest release).
    assert "v1.5.0" in recorded_args, f"Expected v1.5.0 in recorded args: {recorded_args}"
    assert recorded_args[:3] == ["/usr/bin/gh", "release", "create"]


def test_add_omit_pr_config(tmp_path: Path) -> None:
    """Test that omit_pr config prevents PR from being auto-detected or added."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create config with omit_pr: true
    config = Config(id="test", name="Test Project", omit_pr=True)
    save_config(config, project_dir / "config.yaml")

    # Create a stub gh that would return PR 123 if called
    gh_stub = project_dir / "gh"
    gh_stub.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import sys",
                "if 'pr' in sys.argv and 'view' in sys.argv:",
                "    sys.stdout.write('123\\n')",
                "    sys.exit(0)",
                "sys.exit(1)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    gh_stub.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{project_dir}{os.pathsep}{env.get('PATH', '')}"

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Entry",
            "--type",
            "feature",
            "--author",
            "testuser",
            "--description",
            "Entry without PR.",
        ],
        env=env,
    )
    assert add_result.exit_code == 0, add_result.output

    # Verify entry has no PR field
    entries_dir = project_dir / "unreleased"
    entry_files = list(entries_dir.glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    assert "pr" not in entry.metadata
    assert "prs" not in entry.metadata


def test_add_omit_pr_config_warns_on_explicit_pr(tmp_path: Path) -> None:
    """Test that --pr emits warning when omit_pr is configured."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create config with omit_pr: true
    config = Config(id="test", name="Test Project", omit_pr=True)
    save_config(config, project_dir / "config.yaml")

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Entry",
            "--type",
            "feature",
            "--author",
            "testuser",
            "--pr",
            "456",
            "--description",
            "Entry with ignored PR.",
        ],
    )
    assert add_result.exit_code == 0, add_result.output
    assert "omit_pr: true" in add_result.output

    # Verify entry has no PR field despite explicit --pr
    entries_dir = project_dir / "unreleased"
    entry_files = list(entries_dir.glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    assert "pr" not in entry.metadata
    assert "prs" not in entry.metadata


def test_add_omit_author_config(tmp_path: Path) -> None:
    """Test that omit_author config prevents author from being auto-detected or added."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create config with omit_author: true
    config = Config(id="test", name="Test Project", omit_author=True)
    save_config(config, project_dir / "config.yaml")

    # Set env var that would normally auto-detect author
    env = os.environ.copy()
    env["GITHUB_ACTOR"] = "autouser"

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Entry",
            "--type",
            "feature",
            "--description",
            "Entry without author.",
        ],
        env=env,
    )
    assert add_result.exit_code == 0, add_result.output

    # Verify entry has no author field
    entries_dir = project_dir / "unreleased"
    entry_files = list(entries_dir.glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    assert "author" not in entry.metadata
    assert "authors" not in entry.metadata


def test_add_omit_author_config_warns_on_explicit_author(tmp_path: Path) -> None:
    """Test that --author emits warning when omit_author is configured."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create config with omit_author: true
    config = Config(id="test", name="Test Project", omit_author=True)
    save_config(config, project_dir / "config.yaml")

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Entry",
            "--type",
            "feature",
            "--author",
            "someuser",
            "--description",
            "Entry with ignored author.",
        ],
    )
    assert add_result.exit_code == 0, add_result.output
    assert "omit_author: true" in add_result.output

    # Verify entry has no author field despite explicit --author
    entries_dir = project_dir / "unreleased"
    entry_files = list(entries_dir.glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    assert "author" not in entry.metadata
    assert "authors" not in entry.metadata


def test_add_omit_author_config_warns_on_co_author(tmp_path: Path) -> None:
    """Test that --co-author emits warning when omit_author is configured."""
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create config with omit_author: true
    config = Config(id="test", name="Test Project", omit_author=True)
    save_config(config, project_dir / "config.yaml")

    add_result = runner.invoke(
        cli,
        [
            "--root",
            str(project_dir),
            "add",
            "--title",
            "Test Entry",
            "--type",
            "feature",
            "--co-author",
            "coauthor1",
            "--description",
            "Entry with ignored co-author.",
        ],
    )
    assert add_result.exit_code == 0, add_result.output
    assert "omit_author: true" in add_result.output

    # Verify entry has no author field despite explicit --co-author
    entries_dir = project_dir / "unreleased"
    entry_files = list(entries_dir.glob("*.md"))
    assert len(entry_files) == 1
    entry = read_entry(entry_files[0])
    assert "author" not in entry.metadata
    assert "authors" not in entry.metadata

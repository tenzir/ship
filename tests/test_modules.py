"""Tests for module discovery and module-related functionality."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from tenzir_changelog.cli import cli
from tenzir_changelog.config import Config
from tenzir_changelog.modules import discover_modules, discover_modules_from_config
from tenzir_changelog.validate import validate_modules, run_validation_with_modules


def write_yaml(path: Path, content: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")


def create_module(base: Path, module_id: str, module_name: str) -> Path:
    """Create a minimal module directory with config."""
    module_root = base / module_id / "changelog"
    module_root.mkdir(parents=True)
    write_yaml(
        module_root / "config.yaml",
        {"id": module_id, "name": module_name},
    )
    (module_root / "unreleased").mkdir()
    return module_root


def create_entry(module_root: Path, title: str, entry_type: str = "feature") -> Path:
    """Create a minimal changelog entry."""
    slug = title.lower().replace(" ", "-")
    entry_path = module_root / "unreleased" / f"{slug}.md"
    entry_path.write_text(
        f"---\ntitle: {title}\ntype: {entry_type}\ncreated: 2025-01-01T00:00:00Z\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return entry_path


# --- Module Discovery Tests ---


def test_discover_modules_finds_matching_projects(tmp_path: Path) -> None:
    """Modules matching the glob pattern are discovered."""
    packages = tmp_path / "packages"
    create_module(packages, "foo", "Foo Package")
    create_module(packages, "bar", "Bar Package")

    parent_root = tmp_path / "changelog"
    parent_root.mkdir()

    modules = list(discover_modules(parent_root, "../packages/*/changelog"))

    assert len(modules) == 2
    ids = {m.config.id for m in modules}
    assert ids == {"foo", "bar"}


def test_discover_modules_empty_when_no_matches(tmp_path: Path) -> None:
    """Empty list when glob pattern matches nothing."""
    parent_root = tmp_path / "changelog"
    parent_root.mkdir()

    modules = list(discover_modules(parent_root, "../packages/*/changelog"))

    assert modules == []


def test_discover_modules_from_config_empty_when_no_glob(tmp_path: Path) -> None:
    """Returns empty list when config has no modules field."""
    parent_root = tmp_path / "changelog"
    parent_root.mkdir()
    config = Config(id="parent", name="Parent Project")

    modules = discover_modules_from_config(parent_root, config)

    assert modules == []


def test_discover_modules_skips_invalid_configs(tmp_path: Path) -> None:
    """Directories without valid config.yaml are skipped."""
    packages = tmp_path / "packages"
    create_module(packages, "valid", "Valid Package")

    # Create invalid module (missing id)
    invalid_root = packages / "invalid" / "changelog"
    invalid_root.mkdir(parents=True)
    write_yaml(invalid_root / "config.yaml", {"name": "Missing ID"})

    parent_root = tmp_path / "changelog"
    parent_root.mkdir()

    modules = list(discover_modules(parent_root, "../packages/*/changelog"))

    assert len(modules) == 1
    assert modules[0].config.id == "valid"


def test_discover_modules_handles_relative_paths(tmp_path: Path) -> None:
    """Module relative_path is set correctly for display."""
    packages = tmp_path / "packages"
    create_module(packages, "foo", "Foo Package")

    parent_root = tmp_path / "changelog"
    parent_root.mkdir()

    modules = list(discover_modules(parent_root, "../packages/*/changelog"))

    assert len(modules) == 1
    # relative_path should contain the ../ prefix
    assert "../" in modules[0].relative_path or "packages" in modules[0].relative_path


def test_discover_modules_sorted_by_id(tmp_path: Path) -> None:
    """Modules are returned sorted by ID."""
    packages = tmp_path / "packages"
    create_module(packages, "zebra", "Zebra Package")
    create_module(packages, "alpha", "Alpha Package")
    create_module(packages, "middle", "Middle Package")

    parent_root = tmp_path / "changelog"
    parent_root.mkdir()
    config = Config(id="parent", name="Parent", modules="../packages/*/changelog")

    modules = discover_modules_from_config(parent_root, config)

    ids = [m.config.id for m in modules]
    assert ids == ["alpha", "middle", "zebra"]


# --- Validation Tests ---


def test_validate_modules_detects_duplicate_ids(tmp_path: Path) -> None:
    """Duplicate module IDs are reported as validation issues."""
    packages = tmp_path / "packages"
    create_module(packages, "foo", "Foo Package")

    # Create another module with same ID
    dup_root = packages / "foo-dup" / "changelog"
    dup_root.mkdir(parents=True)
    write_yaml(dup_root / "config.yaml", {"id": "foo", "name": "Duplicate Foo"})
    (dup_root / "unreleased").mkdir()

    parent_root = tmp_path / "changelog"
    parent_root.mkdir()
    config = Config(id="parent", name="Parent", modules="../packages/*/changelog")

    modules = discover_modules_from_config(parent_root, config)
    issues = validate_modules(parent_root, config, modules)

    assert len(issues) == 1
    assert "Duplicate module ID 'foo'" in issues[0].message


def test_validate_modules_detects_parent_id_collision(tmp_path: Path) -> None:
    """Module ID colliding with parent ID is reported."""
    packages = tmp_path / "packages"
    # Create module with same ID as parent
    create_module(packages, "parent", "Collision Package")

    parent_root = tmp_path / "changelog"
    parent_root.mkdir()
    config = Config(id="parent", name="Parent", modules="../packages/*/changelog")

    modules = discover_modules_from_config(parent_root, config)
    issues = validate_modules(parent_root, config, modules)

    assert len(issues) == 1
    assert "Duplicate module ID 'parent'" in issues[0].message


def test_run_validation_with_modules_prefixes_issues(tmp_path: Path) -> None:
    """Module validation issues are prefixed with module ID."""
    packages = tmp_path / "packages"
    mod_root = create_module(packages, "mymod", "My Module")

    # Create invalid entry (missing type)
    entry_path = mod_root / "unreleased" / "bad-entry.md"
    entry_path.write_text(
        "---\ntitle: Bad Entry\ncreated: 2025-01-01T00:00:00Z\n---\n\nBody.\n",
        encoding="utf-8",
    )

    parent_root = tmp_path / "changelog"
    parent_root.mkdir()
    write_yaml(parent_root / "config.yaml", {"id": "parent", "name": "Parent"})
    (parent_root / "unreleased").mkdir()

    config = Config(id="parent", name="Parent", modules="../packages/*/changelog")
    modules = discover_modules_from_config(parent_root, config)

    issues = run_validation_with_modules(parent_root, config, modules)

    # Find the module issue
    module_issues = [i for i in issues if "[mymod]" in i.message]
    assert len(module_issues) >= 1
    assert "Unknown type" in module_issues[0].message


# --- CLI Tests ---


def test_cli_modules_command_no_config(tmp_path: Path) -> None:
    """modules command reports when no modules are configured."""
    runner = CliRunner()
    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(project_dir / "config.yaml", {"id": "test", "name": "Test"})

    result = runner.invoke(cli, ["--root", str(project_dir), "modules"])

    assert result.exit_code == 0
    assert "No modules configured" in result.output


def test_cli_modules_command_lists_modules(tmp_path: Path) -> None:
    """modules command lists discovered modules."""
    packages = tmp_path / "packages"
    create_module(packages, "foo", "Foo Package")
    create_module(packages, "bar", "Bar Package")

    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(
        project_dir / "config.yaml",
        {"id": "parent", "name": "Parent", "modules": "../packages/*/changelog"},
    )
    (project_dir / "unreleased").mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(project_dir), "modules"])

    assert result.exit_code == 0
    assert "foo" in result.output
    assert "bar" in result.output
    assert "Foo Package" in result.output
    assert "Bar Package" in result.output


def test_cli_show_includes_modules_by_default(tmp_path: Path) -> None:
    """show command includes module entries by default."""
    packages = tmp_path / "packages"
    mod_root = create_module(packages, "mymod", "My Module")
    create_entry(mod_root, "Module Feature")

    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(
        project_dir / "config.yaml",
        {"id": "parent", "name": "Parent", "modules": "../packages/*/changelog"},
    )
    (project_dir / "unreleased").mkdir()
    # Create parent entry
    create_entry(project_dir, "Parent Feature")

    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(project_dir), "show"])

    assert result.exit_code == 0
    assert "Module Feature" in result.output
    assert "Parent Feature" in result.output


def test_cli_validate_with_modules(tmp_path: Path) -> None:
    """validate command checks parent and modules."""
    packages = tmp_path / "packages"
    mod_root = create_module(packages, "mymod", "My Module")
    create_entry(mod_root, "Valid Entry")

    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(
        project_dir / "config.yaml",
        {"id": "parent", "name": "Parent", "modules": "../packages/*/changelog"},
    )
    (project_dir / "unreleased").mkdir()
    create_entry(project_dir, "Parent Entry")

    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(project_dir), "validate"])

    assert result.exit_code == 0
    assert "all changelog files look good" in result.output


# --- Release Notes with Modules Tests ---


def create_released_entry(
    module_root: Path, title: str, version: str, entry_type: str = "feature"
) -> Path:
    """Create a changelog entry in a release directory."""
    slug = title.lower().replace(" ", "-")
    release_dir = module_root / "releases" / version / "entries"
    release_dir.mkdir(parents=True, exist_ok=True)
    entry_path = release_dir / f"{slug}.md"
    entry_path.write_text(
        f"---\ntitle: {title}\ntype: {entry_type}\ncreated: 2025-01-01T00:00:00Z\nauthors:\n  - testuser\n---\n\nEntry body text.\n",
        encoding="utf-8",
    )
    # Also create the manifest
    manifest_path = module_root / "releases" / version / "manifest.yaml"
    if not manifest_path.exists():
        write_yaml(
            manifest_path,
            {
                "created": "2025-01-01",
                "title": f"Release {version}",
                "entries": [slug],
            },
        )
    else:
        # Append entry to existing manifest
        manifest = yaml.safe_load(manifest_path.read_text())
        if slug not in manifest["entries"]:
            manifest["entries"].append(slug)
            write_yaml(manifest_path, manifest)
    return entry_path


def test_release_notes_includes_module_sections(tmp_path: Path) -> None:
    """release notes includes module sections with released entries."""
    packages = tmp_path / "packages"
    mod_root = create_module(packages, "mymod", "My Module")
    create_released_entry(mod_root, "Module Feature One", "v1.0.0", "feature")
    create_released_entry(mod_root, "Module Bugfix", "v1.0.0", "bugfix")

    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(
        project_dir / "config.yaml",
        {"id": "parent", "name": "Parent", "modules": "../packages/*/changelog"},
    )
    (project_dir / "unreleased").mkdir()
    create_entry(project_dir, "Parent Feature")

    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(project_dir), "release", "notes", "unreleased"])

    assert result.exit_code == 0
    # Main project entry with full body
    assert "Parent Feature" in result.output
    assert "Body." in result.output  # Full body for main project
    # Module section appears
    assert "## My Module" in result.output
    # Module entries are compact (title only, no body)
    assert "Module Feature One" in result.output
    assert "Module Bugfix" in result.output
    # Separator between main and modules
    assert "---" in result.output


def test_release_notes_module_entries_are_compact(tmp_path: Path) -> None:
    """Module entries show title and attribution, not body."""
    packages = tmp_path / "packages"
    mod_root = create_module(packages, "mymod", "My Module")
    create_released_entry(mod_root, "Some Feature", "v1.0.0", "feature")

    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(
        project_dir / "config.yaml",
        {"id": "parent", "name": "Parent", "modules": "../packages/*/changelog"},
    )
    (project_dir / "unreleased").mkdir()
    create_entry(project_dir, "Parent Feature")

    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(project_dir), "release", "notes", "unreleased"])

    assert result.exit_code == 0
    # Module entry appears as bullet with emoji prefix and title
    assert "- 🚀 Some Feature" in result.output
    # Attribution appears
    assert "testuser" in result.output
    # Body text should NOT appear in module section
    # (The body "Entry body text." should not be in the module section)
    lines = result.output.split("## My Module")[1] if "## My Module" in result.output else ""
    assert "Entry body text" not in lines


def test_release_notes_excludes_unreleased_module_entries(tmp_path: Path) -> None:
    """Only released module entries are included, not unreleased."""
    packages = tmp_path / "packages"
    mod_root = create_module(packages, "mymod", "My Module")
    create_entry(mod_root, "Unreleased Module Feature")  # Unreleased

    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(
        project_dir / "config.yaml",
        {"id": "parent", "name": "Parent", "modules": "../packages/*/changelog"},
    )
    (project_dir / "unreleased").mkdir()
    create_entry(project_dir, "Parent Feature")

    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(project_dir), "release", "notes", "unreleased"])

    assert result.exit_code == 0
    # Parent entry is included
    assert "Parent Feature" in result.output
    # Module with no released entries should not have a section
    assert "## My Module" not in result.output
    # Unreleased module entry should not appear
    assert "Unreleased Module Feature" not in result.output


def test_release_notes_json_includes_modules(tmp_path: Path) -> None:
    """JSON output includes modules array with released entries."""
    import json

    packages = tmp_path / "packages"
    mod_root = create_module(packages, "mymod", "My Module")
    create_released_entry(mod_root, "Module Feature", "v1.0.0", "feature")

    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(
        project_dir / "config.yaml",
        {"id": "parent", "name": "Parent", "modules": "../packages/*/changelog"},
    )
    (project_dir / "unreleased").mkdir()
    create_entry(project_dir, "Parent Feature")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(project_dir), "release", "notes", "unreleased", "--json"]
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "modules" in data
    assert len(data["modules"]) == 1
    assert data["modules"][0]["id"] == "mymod"
    assert data["modules"][0]["name"] == "My Module"
    assert len(data["modules"][0]["entries"]) == 1
    assert data["modules"][0]["entries"][0]["title"] == "Module Feature"


def test_release_notes_no_modules_no_separator(tmp_path: Path) -> None:
    """When no modules exist, no separator is added."""
    project_dir = tmp_path / "changelog"
    project_dir.mkdir()
    write_yaml(project_dir / "config.yaml", {"id": "test", "name": "Test"})
    (project_dir / "unreleased").mkdir()
    create_entry(project_dir, "Test Feature")

    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(project_dir), "release", "notes", "unreleased"])

    assert result.exit_code == 0
    assert "Test Feature" in result.output
    # No separator when no modules
    assert "---" not in result.output

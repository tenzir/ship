"""CLI package for tenzir-changelog.

This package contains the modular CLI implementation:
- _core.py: CLIContext, decorators, shared utilities, main entry point
- _rendering.py: Rich rendering functions
- _show.py: show command and related functions
- _export.py: markdown and JSON export formatting
- _manifests.py: release manifest operations
- _add.py: add command for creating entries
- _validate.py: validate command
- _release.py: release command group
"""

from __future__ import annotations

# Re-export core types and utilities
from ._core import (
    CLIContext,
    INFO_PREFIX,
    create_cli_context,
    compact_option,
    explicit_links_option,
    DEFAULT_ENTRY_TYPE,
    DEFAULT_PROJECT_ID,
    ENTRY_TYPE_STYLES,
    ENTRY_TYPE_EMOJIS,
    ENTRY_EXPORT_ORDER,
    VERSION_FLAGS,
    _command_help_text,
    _format_author,
    _format_section_title,
    _parse_pr_numbers,
    _build_prs_structured,
    _build_authors_structured,
    _filter_entries_by_project,
    _normalize_component_filters,
    _filter_entries_by_component,
    _join_with_conjunction,
    _collect_author_pr_text,
    _format_author_line,
    _create_cli_group,
    main,
)

# Re-export rendering utilities
from ._rendering import (
    IdentifierResolution,
    ColumnSpec,
    _print_renderable,
    _entries_table_layout,
    _ellipsis_cell,
    _add_table_column,
    _render_project_header,
    _render_entries,
    _render_release,
    _render_single_entry,
    _render_entries_multi_project,
    _render_release_notes,
    _render_release_notes_compact,
    _render_module_entries_compact,
    _compose_release_document,
    _build_entry_title,
    _build_entry_metadata_line,
    _build_entry_body,
    _sort_entries_for_display,
    _build_release_sort_order,
    _release_entry_sort_key,
)

# Re-export show command
from ._show import (
    ShowView,
    show_entries,
    run_show_entries,
)

# Re-export export functions
from ._export import (
    _entry_to_dict,
    _build_release_payload,
    _render_markdown_release_block,
    _export_markdown_release,
    _export_markdown_compact,
    _export_json_payload,
)

# Re-export manifest operations
from ._manifests import (
    _get_module_latest_version,
    _get_sorted_release_manifests,
    _get_release_manifest_before,
    _get_latest_release_manifest,
    _gather_module_released_entries,
)

# Re-export add command
from ._add import (
    ENTRY_TYPE_CHOICES,
    ENTRY_TYPE_SHORTCUTS,
    create_entry,
    add,
)

# Re-export validate command
from ._validate import (
    run_validate,
    validate_cmd,
)

# Re-export release commands
from ._release import (
    create_release,
    render_release_notes,
    publish_release,
    release_group,
)

# Re-export detect_github_login from utils for backwards compatibility
from ..utils import detect_github_login

# Create the main CLI group
cli = _create_cli_group()

# Register all commands with the cli group
cli.add_command(show_entries)
cli.add_command(add)
cli.add_command(validate_cmd)
cli.add_command(release_group)


__all__ = [
    # Core
    "cli",
    "main",
    "CLIContext",
    "INFO_PREFIX",
    "create_cli_context",
    "compact_option",
    "explicit_links_option",
    "DEFAULT_ENTRY_TYPE",
    "DEFAULT_PROJECT_ID",
    "ENTRY_TYPE_STYLES",
    "ENTRY_TYPE_EMOJIS",
    "ENTRY_EXPORT_ORDER",
    "VERSION_FLAGS",
    # Show
    "ShowView",
    "show_entries",
    "run_show_entries",
    # Export
    "_entry_to_dict",
    "_build_release_payload",
    "_render_markdown_release_block",
    "_export_markdown_release",
    "_export_markdown_compact",
    "_export_json_payload",
    # Manifests
    "_get_module_latest_version",
    "_get_sorted_release_manifests",
    "_get_release_manifest_before",
    "_get_latest_release_manifest",
    "_gather_module_released_entries",
    # Add command
    "ENTRY_TYPE_CHOICES",
    "ENTRY_TYPE_SHORTCUTS",
    "create_entry",
    "add",
    # Release
    "create_release",
    "render_release_notes",
    "publish_release",
    "release_group",
    # Validate
    "run_validate",
    "validate_cmd",
    # Rendering
    "IdentifierResolution",
    "ColumnSpec",
    "_render_release_notes",
    "_render_release_notes_compact",
    "_compose_release_document",
]

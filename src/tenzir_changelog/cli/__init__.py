"""CLI package for tenzir-changelog.

This package contains the modular CLI implementation:
- _core.py: CLIContext, decorators, shared utilities
- _rendering.py: Rich rendering functions
- _show.py: show command and related functions

Functions not yet extracted are imported from _cli_legacy.py.
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
    _get_latest_release_manifest,
)

# Import remaining commands and functions from legacy CLI module
# These will be extracted into separate modules in the future
from .._cli_legacy import (
    cli,
    main,
    create_entry,
    create_release,
    render_release_notes,
    publish_release,
    run_validate,
    detect_github_login,
)

# Register the show command from new modular implementation
# Note: The legacy cli already has show_entries registered, but we can override it
# For now, we use the legacy cli which has all commands registered


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
    "_get_latest_release_manifest",
    # Add/Release/Validate (from legacy)
    "create_entry",
    "create_release",
    "render_release_notes",
    "publish_release",
    "run_validate",
    # Rendering
    "IdentifierResolution",
    "ColumnSpec",
    "_render_release_notes",
    "_render_release_notes_compact",
    "_compose_release_document",
]

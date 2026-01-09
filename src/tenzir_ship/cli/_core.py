"""Core CLI infrastructure: context, decorators, and shared utilities."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path
from typing import (
    Any,
    Callable,
    Iterable,
    Mapping,
    Optional,
    TypeVar,
)

import click

from .. import __version__ as package_version
from ..config import (
    CHANGELOG_DIRECTORY_NAME,
    Config,
    PACKAGE_METADATA_FILENAME,
    default_config_path,
    load_project_config,
    package_metadata_path,
    save_config,
)
from ..entries import Entry, entry_directory
from ..modules import Module, discover_modules_from_config
from ..utils import (
    INFO_PREFIX,
    abort_on_user_interrupt,
    configure_logging,
    log_debug,
    log_info,
    log_success,
    slugify,
)

F = TypeVar("F", bound=Callable[..., Any])

__all__ = [
    "CLIContext",
    "INFO_PREFIX",
    "create_cli_context",
    "cli",
    "compact_option",
    "explicit_links_option",
    "DEFAULT_ENTRY_TYPE",
    "DEFAULT_PROJECT_ID",
    "ENTRY_TYPE_STYLES",
    "ENTRY_TYPE_EMOJIS",
    "ENTRY_EXPORT_ORDER",
    "VERSION_FLAGS",
    # Formatting and filtering utilities
    "_command_help_text",
    "_format_author",
    "_format_section_title",
    "_parse_pr_numbers",
    "_build_prs_structured",
    "_build_authors_structured",
    "_filter_entries_by_project",
    "_normalize_component_filters",
    "_filter_entries_by_component",
    "_join_with_conjunction",
    "_collect_author_pr_text",
    "_format_author_line",
    "_create_cli_group",
    "main",
]

VERSION_FLAGS = {"--version", "-V"}

DEFAULT_ENTRY_TYPE = "feature"
DEFAULT_PROJECT_ID = "project"

# Style mappings for entry types
ENTRY_TYPE_STYLES: dict[str, str] = {
    "feature": "green",
    "bugfix": "red",
    "breaking": "bold red",
    "change": "blue",
}

ENTRY_TYPE_EMOJIS = {
    "breaking": "💥",
    "feature": "🚀",
    "bugfix": "🐞",
    "change": "🔧",
}

ENTRY_EXPORT_ORDER = ("breaking", "feature", "change", "bugfix")

TYPE_SECTION_TITLES = {
    "breaking": "Breaking changes",
    "feature": "Features",
    "change": "Changes",
    "bugfix": "Bug fixes",
}


def _resolve_cli_version() -> str:
    try:
        return metadata_version("tenzir-ship")
    except PackageNotFoundError:
        return package_version


def _command_help_text(
    *,
    summary: str,
    command_name: str,
    verb: str,
    row_hint: str = "Row numbers (e.g., 1, 2, 3)",
    version_hint: str = "to show release details",
    include_scope: bool = False,
) -> str:
    """Build consistent help text for entry-addressing commands."""

    # Use \b (backspace) to tell Click to preserve formatting - no blank lines
    # within the block or Click will treat what follows as a new paragraph
    identifier_items = [
        f"- {row_hint}",
        "- Entry IDs, partial or full (e.g., configure,",
        "  configure-export-style-defaults)",
        f"- Version numbers (e.g., v0.2.0) {version_hint}",
    ]
    if include_scope:
        identifier_items.append("- Scope: all, unreleased, released, latest")

    identifiers_block = "\n".join(["\b", "IDENTIFIERS can be:"] + identifier_items)

    example_lines = [
        f"  tenzir-ship {command_name} 1           # {verb.capitalize()} entry #1",
        f"  tenzir-ship {command_name} 1 2 3       # {verb.capitalize()} entries #1, #2, and #3",
        f"  tenzir-ship {command_name} configure   # {verb.capitalize()} entry matching 'configure'",
        f"  tenzir-ship {command_name} v0.2.0      # {verb.capitalize()} all entries in v0.2.0",
    ]
    if include_scope:
        example_lines.extend(
            [
                f"  tenzir-ship {command_name} unreleased  # {verb.capitalize()} unreleased entries",
                f"  tenzir-ship {command_name} latest      # {verb.capitalize()} entries from latest release",
            ]
        )

    examples_block = "\n".join(["\b", "Examples:"] + example_lines)
    return f"{summary}\n\n{identifiers_block}\n\n{examples_block}"


def compact_option() -> Callable[[F], F]:
    """Shared --compact/--no-compact option for release Markdown rendering.

    Controls whether to use the compact bullet-list format (--compact) or
    the detailed section-based format (--no-compact) when rendering release
    notes and changelog entries.

    Used by: release create, show

    IMPORTANT: Keep this decorator in sync with all commands that render
    release notes to ensure consistent behavior.
    """

    def decorator(f: F) -> F:
        return click.option(
            "--compact/--no-compact",
            default=None,
            help="Use the compact layout when rendering Markdown.",
        )(f)

    return decorator


def explicit_links_option() -> Callable[[F], F]:
    """Shared --explicit-links/--no-explicit-links option for Markdown rendering.

    When enabled, converts GitHub shorthand (@mentions and #PR references)
    to explicit Markdown links. Examples:
    - @username -> [@username](https://github.com/username)
    - #123 -> [#123](https://github.com/owner/repo/pull/123)

    Useful for exporting release notes to documentation sites or other
    Markdown renderers that don't automatically link GitHub references.

    When neither flag is specified, uses the config.explicit_links setting.

    Used by: release create, show

    IMPORTANT: Keep this decorator in sync with all commands that render
    release notes to ensure consistent behavior.
    """

    def decorator(f: F) -> F:
        return click.option(
            "--explicit-links/--no-explicit-links",
            default=None,
            help="Render @mentions and PR references as explicit Markdown links.",
        )(f)

    return decorator


@dataclass
class CLIContext:
    """Shared command context."""

    project_root: Path
    config_path: Path
    _config: Optional[Config] = None
    _modules: list[Module] | None = None  # cached discovered modules

    def ensure_config(self, *, create_if_missing: bool = False) -> Config:
        if self._config is None:
            config_path = self.config_path
            project_root = config_path.parent
            self.project_root = project_root
            try:
                self._config = load_project_config(project_root)
            except FileNotFoundError:
                if not create_if_missing:
                    log_info(f"no tenzir-ship project detected at {project_root}.")
                    log_info("run 'tenzir-ship add' from your project root or provide --root.")
                    raise click.exceptions.Exit(1)
                config = _initialize_project_scaffold(
                    project_root=project_root,
                    config_path=config_path,
                )
                self._config = config
            except ValueError as error:
                raise click.ClickException(str(error)) from error
        return self._config

    def reset_config(self, config: Config) -> None:
        self._config = config

    def has_modules(self) -> bool:
        """Return True if modules are configured."""
        return self.ensure_config().modules is not None

    def get_modules(self) -> list[Module]:
        """Discover and return cached modules.

        Returns an empty list if no modules are configured.
        """
        if self._modules is None:
            config = self.ensure_config()
            self._modules = discover_modules_from_config(self.project_root, config)
        return self._modules


def _default_project_id(project_root: Path) -> str:
    slug = slugify(project_root.name)
    return slug or DEFAULT_PROJECT_ID


def _default_project_name(project_id: str) -> str:
    words = project_id.replace("-", " ").strip()
    return words.title() if words else "Changelog"


def _initialize_project_scaffold(*, project_root: Path, config_path: Path) -> Config:
    project_id = _default_project_id(project_root)
    project_name = _default_project_name(project_id)
    config = Config(id=project_id, name=project_name)
    save_config(config, config_path)
    entry_directory(project_root).mkdir(parents=True, exist_ok=True)
    log_success(f"initialized changelog project at {project_root}")
    return config


def _resolve_project_root(value: Path, *, bootstrap_in_subdir: bool = False) -> Path:
    resolved = value.resolve()

    def _has_config(path: Path) -> bool:
        return default_config_path(path).exists()

    def _is_package_root(path: Path) -> bool:
        metadata = path / PACKAGE_METADATA_FILENAME
        if not metadata.is_file():
            return False
        changelog_dir = path / CHANGELOG_DIRECTORY_NAME
        if changelog_dir.exists() and not changelog_dir.is_dir():
            return False
        return True

    def _is_package_changelog(path: Path) -> bool:
        if path.name != CHANGELOG_DIRECTORY_NAME:
            return False
        metadata = package_metadata_path(path)
        return metadata.is_file()

    if resolved.is_dir():
        if _has_config(resolved) or _is_package_changelog(resolved):
            return resolved
        if _is_package_root(resolved):
            return (resolved / CHANGELOG_DIRECTORY_NAME).resolve()
        # Check if a changelog/ subdirectory exists with a valid config.
        changelog_subdir = resolved / CHANGELOG_DIRECTORY_NAME
        if changelog_subdir.is_dir() and _has_config(changelog_subdir):
            return changelog_subdir.resolve()

    for candidate in [resolved] + list(resolved.parents):
        if not candidate.is_dir():
            continue
        if _has_config(candidate) or _is_package_changelog(candidate):
            return candidate
        if _is_package_root(candidate):
            return (candidate / CHANGELOG_DIRECTORY_NAME).resolve()

    # No existing project found. When bootstrapping without explicit --root,
    # default to changelog/ subdirectory for consistency with package mode.
    if bootstrap_in_subdir:
        return (resolved / CHANGELOG_DIRECTORY_NAME).resolve()
    return resolved


def _normalize_optional(value: Optional[str]) -> Optional[str]:
    """Convert Click sentinel values to None."""

    if value is None:
        return None
    value_class = value.__class__.__name__
    if value_class == "Sentinel":
        return None
    return value


def _mask_comment_block(text: str) -> str:
    """Strip comment lines (starting with '#') from editor input."""
    lines = []
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def _read_description_file(path: Path) -> str:
    """Read description from file or stdin (if path is '-')."""
    if str(path) == "-":
        if sys.stdin.isatty():
            raise click.ClickException(
                "No input provided on stdin. Pipe content or use --description."
            )
        return sys.stdin.read()
    if not path.exists():
        raise click.ClickException(f"Description file not found: {path}")
    return path.read_text(encoding="utf-8")


def _resolve_description_input(
    description: Optional[str],
    description_file: Optional[Path],
) -> Optional[str]:
    """Resolve description from inline text, file, or stdin."""
    if description is not None and description_file is not None:
        raise click.ClickException("Use only one of --description or --description-file, not both.")
    if description is not None:
        return description
    if description_file is not None:
        return _read_description_file(description_file)
    return None


def create_cli_context(
    *,
    root: Path | None = None,
    config: Optional[Path] = None,
    debug: bool = False,
) -> CLIContext:
    """Return a CLIContext using the same resolution logic as the CLI entry point."""

    configure_logging(debug)

    if root is None:
        # No explicit --root: bootstrap into changelog/ subdirectory if needed.
        resolved_root = _resolve_project_root(Path("."), bootstrap_in_subdir=True)
    else:
        # Explicit --root: use that directory as-is for bootstrapping.
        resolved_root = _resolve_project_root(root)

    config_path = config.resolve() if config else default_config_path(resolved_root)
    log_debug(f"resolved project root: {resolved_root}")
    log_debug(f"using config path: {config_path}")
    return CLIContext(project_root=resolved_root, config_path=config_path)


# Placeholder for the cli group - will be defined after show_entries is available
# This allows the module to be imported without circular dependencies
cli: click.Group = None  # type: ignore[assignment]


def _create_cli_group() -> click.Group:
    """Create the main CLI group. Called after all commands are defined."""

    @click.group(
        invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]}
    )
    @click.option(
        "--root",
        type=click.Path(path_type=Path, exists=True, file_okay=False),
        help="Project root containing config and changelog files.",
    )
    @click.option(
        "--config",
        type=click.Path(path_type=Path, dir_okay=False),
        help="Path to an explicit changelog config YAML file.",
    )
    @click.option(
        "--debug",
        "-d",
        is_flag=True,
        help="Enable debug logging.",
    )
    @click.pass_context
    def _cli(
        ctx: click.Context,
        root: Path | None,
        config: Optional[Path],
        debug: bool,
    ) -> None:
        """Manage changelog entries and release manifests."""

        ctx.obj = create_cli_context(root=root, config=config, debug=debug)

        if ctx.invoked_subcommand is None:
            # Import here to avoid circular import
            from ._show import show_entries

            ctx.invoke(show_entries)

    return click.version_option(version=_resolve_cli_version())(_cli)


# Shared formatting utilities used across modules


def _format_section_title(entry_type: str, include_emoji: bool) -> str:
    """Return the section title with an optional type emoji prefix."""
    section_title = TYPE_SECTION_TITLES.get(entry_type, entry_type.title())
    if not include_emoji:
        return section_title
    emoji = ENTRY_TYPE_EMOJIS.get(entry_type)
    if not emoji:
        return section_title
    return f"{emoji} {section_title}"


def _format_author(author: str, *, explicit_links: bool = False) -> str:
    """Format an author for display, adding @ prefix only for GitHub-style handles.

    Args:
        author: The author name or GitHub handle.
        explicit_links: If True, wrap GitHub handles in markdown links.
    """
    if " " in author:
        return author
    handle = f"@{author}"
    if explicit_links:
        return f"[{handle}](https://github.com/{author})"
    return handle


def _type_emoji(entry_type: str, *, include_emoji: bool = True) -> str:
    """Get the emoji for an entry type, or a bullet point if disabled."""
    if include_emoji:
        return ENTRY_TYPE_EMOJIS.get(entry_type, "\u2022")
    return "\u2022"


def _parse_pr_numbers(metadata: Mapping[str, Any]) -> list[int]:
    """Extract PR numbers from metadata, handling various formats."""
    raw = metadata.get("prs") or metadata.get("pr")
    if raw is None:
        return []
    if isinstance(raw, int):
        return [raw]
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        if raw.startswith("#"):
            raw = raw[1:]
        try:
            return [int(raw)]
        except ValueError:
            return []
    if isinstance(raw, list):
        result: list[int] = []
        for item in raw:
            if isinstance(item, int):
                result.append(item)
            elif isinstance(item, str):
                item = item.strip().lstrip("#")
                if item.isdigit():
                    result.append(int(item))
        return result
    return []


def _build_prs_structured(
    metadata: Mapping[str, Any], config: Config
) -> list[dict[str, str | int]]:
    """Build structured PR metadata for JSON export."""
    prs: list[dict[str, str | int]] = []
    for num in _parse_pr_numbers(metadata):
        entry: dict[str, str | int] = {"number": num}
        if config.repository:
            entry["url"] = f"https://github.com/{config.repository}/pull/{num}"
        prs.append(entry)
    return prs


def _build_authors_structured(metadata: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build structured author objects with URLs for JSON export."""
    raw_authors = metadata.get("authors") or []
    result: list[dict[str, str]] = []
    for author in raw_authors:
        if " " in author:
            # Full name, not a GitHub handle
            result.append({"name": author})
        else:
            # GitHub handle
            result.append({"handle": author, "url": f"https://github.com/{author}"})
    return result


def _filter_entries_by_project(
    entries: Iterable[Entry], projects: set[str], default_project: str
) -> list[Entry]:
    if not projects:
        return list(entries)
    filtered: list[Entry] = []
    for entry in entries:
        entry_project = entry.metadata.get("project") or default_project
        if entry_project in projects:
            filtered.append(entry)
    return filtered


def _normalize_component_filters(values: Iterable[str], config: Config) -> set[str]:
    """Validate and normalize component filters using config defaults."""
    normalized: set[str] = set()
    if not values:
        return normalized
    allowed_lookup = {component.lower(): component for component in config.components}
    unknown: list[str] = []
    for raw_value in values:
        stripped = raw_value.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if config.components and lowered not in allowed_lookup:
            unknown.append(stripped)
            continue
        normalized.add(allowed_lookup.get(lowered, stripped))
    if unknown:
        allowed = ", ".join(config.components)
        raise click.ClickException(
            f"Unknown component filter(s): {', '.join(sorted(unknown))}. Allowed components: {allowed}"
        )
    return normalized


def _filter_entries_by_component(entries: Iterable[Entry], components: set[str]) -> list[Entry]:
    """Filter entries by component labels (case-insensitive)."""
    if not components:
        return list(entries)
    filtered: list[Entry] = []
    for entry in entries:
        entry_components = entry.components
        if entry_components:
            normalized_entry_components = {c.lower() for c in entry_components}
            if normalized_entry_components & components:
                filtered.append(entry)
    return filtered


def _join_with_conjunction(items: list[str]) -> str:
    """Join items with commas and 'and' for the last item."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _collect_author_pr_text(
    entry: Entry, config: Config, *, explicit_links: bool = False
) -> tuple[str, str]:
    """Collect author and PR text for attribution lines."""
    metadata = entry.metadata
    # Support both plural `authors` and singular `author` keys
    authors = metadata.get("authors")
    if authors is None:
        authors = metadata.get("author")
    authors = authors or []
    if isinstance(authors, str):
        authors = [authors]
    authors = [author.strip() for author in authors if author and author.strip()]

    author_handles = [_format_author(author, explicit_links=explicit_links) for author in authors]
    author_text = _join_with_conjunction(author_handles)

    prs = _parse_pr_numbers(metadata)

    repo = config.repository
    pr_refs: list[str] = []
    for pr in prs:
        label = f"#{pr}"
        if explicit_links and repo:
            pr_refs.append(f"[{label}](https://github.com/{repo}/pull/{pr})")
        else:
            pr_refs.append(label)
    pr_text = _join_with_conjunction(pr_refs)

    return author_text, pr_text


def _format_author_line(entry: Entry, config: Config, *, explicit_links: bool = False) -> str:
    """Format the attribution line for an entry as italic markdown."""
    author_text, pr_text = _collect_author_pr_text(entry, config, explicit_links=explicit_links)

    if not author_text and not pr_text:
        return ""

    parts = []
    if author_text:
        parts.append(f"By {author_text}")
    if pr_text:
        parts.append(f"in {pr_text}")
    return "*" + " ".join(parts) + ".*"


def main(argv: list[str] | None = None) -> int:
    """Entry point for console_scripts."""
    # Import cli here to avoid circular import at module load time
    from . import cli

    args = list(argv) if argv is not None else list(sys.argv[1:])

    if any(flag in args for flag in VERSION_FLAGS):
        click.echo(_resolve_cli_version())
        return 0

    # If no command is specified, default to 'show'
    # Check if any arg is a known command
    has_command = any(arg in cli.commands for arg in args)
    if not has_command:
        # No command found, inject 'show' at the end (after options like --root)
        args.append("show")

    try:
        cli.main(args=args, prog_name="tenzir-ship", standalone_mode=False)
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        exit_code = getattr(exc, "exit_code", 1)
        return exit_code if isinstance(exit_code, int) else 1
    except KeyboardInterrupt as exc:
        try:
            abort_on_user_interrupt(exc)
        except click.exceptions.Exit as exit_exc:
            exit_code = getattr(exit_exc, "exit_code", 130)
            return exit_code if isinstance(exit_code, int) else 130
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    return 0

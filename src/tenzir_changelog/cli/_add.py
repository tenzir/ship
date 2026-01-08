"""Add command for creating changelog entries."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import Any, Optional, Sequence

import click
from rich.text import Text

from ..entries import ENTRY_TYPES, write_entry
from ..utils import (
    abort_on_user_interrupt,
    console,
    detect_github_login,
    detect_github_pr_number,
    log_info,
    log_success,
    log_warning,
)
from ._core import (
    CLIContext,
    DEFAULT_ENTRY_TYPE,
    ENTRY_TYPE_STYLES,
)

__all__ = [
    "ENTRY_TYPE_CHOICES",
    "ENTRY_TYPE_SHORTCUTS",
    "create_entry",
    "add",
    # Helper functions
    "_mask_comment_block",
    "_read_description_file",
    "_resolve_description_input",
    "_prompt_entry_body",
    "_prompt_text",
    "_prompt_optional",
    "_normalize_entry_type",
    "_prompt_entry_type",
]

# Entry type selection choices and shortcuts
ENTRY_TYPE_CHOICES = (
    ("breaking", "0"),
    ("feature", "1"),
    ("bugfix", "2"),
    ("change", "3"),
)
ENTRY_TYPE_SHORTCUTS = {
    "breaking changes": "breaking",
    "breaking": "breaking",
    "break": "breaking",
    "bc": "breaking",
    "br": "breaking",
    "0": "breaking",
    "feature": "feature",
    "f": "feature",
    "1": "feature",
    "bugfix": "bugfix",
    "b": "bugfix",
    "2": "bugfix",
    "change": "change",
    "c": "change",
    "3": "change",
}


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


def _prompt_entry_body(initial: str = "") -> str:
    log_info("launching editor for entry body (set EDITOR or pass --description to skip).")
    try:
        edited = click.edit(
            textwrap.dedent(
                """\
                # Write the entry body below. Lines starting with '#' are ignored.
                # Save and close the editor to finish. Leave empty to skip.
                """
            )
            + ("\n" + initial if initial else "\n")
        )
    except (click.exceptions.Abort, KeyboardInterrupt) as exc:
        abort_on_user_interrupt(exc)
    if edited is None:
        return ""
    return _mask_comment_block(edited)


def _prompt_text(label: str, **kwargs: Any) -> str:
    prompt_suffix = kwargs.pop("prompt_suffix", ": ")
    try:
        result = click.prompt(click.style(label, bold=True), prompt_suffix=prompt_suffix, **kwargs)
    except (click.exceptions.Abort, KeyboardInterrupt) as exc:
        abort_on_user_interrupt(exc)
    return str(result)


def _prompt_optional(prompt: str, default: Optional[str] = None) -> Optional[str]:
    value = _prompt_text(
        prompt,
        default=default or "",
        show_default=bool(default),
    )
    return value.strip() or None


def _normalize_entry_type(value: str) -> Optional[str]:
    value = value.strip().lower()
    if not value:
        return DEFAULT_ENTRY_TYPE
    return ENTRY_TYPE_SHORTCUTS.get(value)


def _prompt_entry_type(default: str = DEFAULT_ENTRY_TYPE) -> str:
    prompt_text = Text("Type: ", style="bold")
    for idx, (name, key) in enumerate(ENTRY_TYPE_CHOICES):
        prompt_text.append(name)
        prompt_text.append(" [")
        prompt_text.append(key, style="bold cyan")
        prompt_text.append("]")
        if idx < len(ENTRY_TYPE_CHOICES) - 1:
            prompt_text.append(", ")
    console.print(prompt_text)

    while True:
        try:
            key = click.getchar()
        except (KeyboardInterrupt, EOFError, click.exceptions.Abort) as exc:
            abort_on_user_interrupt(exc)
        if key in {"\r", "\n"}:
            selection = default
            break
        normalized = _normalize_entry_type(key)
        if normalized:
            selection = normalized
            break
    console.print(Text(f"  {selection}", style=ENTRY_TYPE_STYLES.get(selection, "")))
    return selection


def create_entry(
    ctx: CLIContext,
    *,
    title: Optional[str] = None,
    entry_type: Optional[str] = None,
    project_override: Optional[str] = None,
    components: Sequence[str] | None = None,
    authors: Sequence[str] | None = None,
    co_authors: Sequence[str] | None = None,
    prs: Sequence[str] | None = None,
    description: Optional[str] = None,
    allow_interactive: bool = True,
) -> Path:
    """Python wrapper for creating entries that mirrors the CLI behavior."""

    config = ctx.ensure_config(create_if_missing=True)
    project_root = ctx.project_root

    normalized_title = (title or "").strip()
    if not normalized_title:
        if not allow_interactive:
            raise click.ClickException("Title is required when running the API non-interactively.")
        normalized_title = _prompt_text("Title")
    title = normalized_title
    if entry_type:
        normalized_type = _normalize_entry_type(entry_type)
        if normalized_type is None:
            raise click.ClickException(
                f"Unknown entry type '{entry_type}'. Expected one of: {', '.join(ENTRY_TYPES)}"
            )
        entry_type = normalized_type
    else:
        entry_type = _prompt_entry_type() if allow_interactive else DEFAULT_ENTRY_TYPE

    project_value = (project_override or "").strip() or config.id
    if project_value != config.id:
        raise click.ClickException(f"Unknown project '{project_value}'. Expected '{config.id}'.")

    available_components = list(config.components)
    component_values: list[str] = []
    for raw_component in tuple(components or ()):
        candidate = raw_component.strip()
        if not candidate:
            continue
        if available_components:
            lookup = {value.lower(): value for value in available_components}
            lowered = candidate.lower()
            if lowered not in lookup:
                allowed = ", ".join(available_components)
                raise click.ClickException(
                    f"Unknown component '{candidate}'. Allowed components: {allowed}"
                )
            component_values.append(lookup[lowered])
        else:
            component_values.append(candidate)

    author_values = tuple(authors or ())
    if config.omit_author:
        if author_values or co_authors:
            log_warning("--author/--co-author ignored: config has 'omit_author: true'")
        authors_list = []
    elif author_values:
        authors_list = [author.strip() for author in author_values if author.strip()]
    else:
        inferred_author = detect_github_login(log_success=False)
        if inferred_author:
            log_info(f"detected GitHub login '@{inferred_author}' and recorded it as the author.")
            authors_list = [inferred_author]
        elif allow_interactive:
            author_value = _prompt_optional("Authors (comma separated)", default="")
            authors_list = (
                [item.strip() for item in author_value.split(",") if item.strip()]
                if author_value
                else []
            )
        else:
            authors_list = []

    # Append co-authors (always additive, unless config.omit_author is set)
    if co_authors and not config.omit_author:
        co_authors_cleaned = [a.strip() for a in co_authors if a.strip()]
        authors_list.extend(co_authors_cleaned)
        # Deduplicate while preserving order
        authors_list = list(dict.fromkeys(authors_list))

    if description is not None:
        body = description
    else:
        body = _prompt_entry_body() if allow_interactive else ""

    pr_numbers: list[int] = []
    prs_provided = tuple(prs or ())
    if config.omit_pr:
        if prs_provided:
            log_warning("--pr ignored: config has 'omit_pr: true'")
    else:
        for pr_value in prs_provided:
            pr_value = pr_value.strip()
            if not pr_value:
                continue
            try:
                pr_numbers.append(int(pr_value))
            except ValueError as exc:
                raise click.ClickException(f"PR value '{pr_value}' must be numeric.") from exc
        if not pr_numbers:
            inferred_pr = detect_github_pr_number(project_root, log_success=False)
            if inferred_pr is not None:
                log_info(f"detected open pull request #{inferred_pr} for the current branch.")
                pr_numbers.append(inferred_pr)

    metadata: dict[str, Any] = {
        "title": title,
        "type": entry_type,
        "project": project_value,
    }
    # Use singular form for single values, plural for multiple
    if authors_list:
        if len(authors_list) == 1:
            metadata["author"] = authors_list[0]
        else:
            metadata["authors"] = authors_list
    if component_values:
        if len(component_values) == 1:
            metadata["component"] = component_values[0]
        else:
            metadata["components"] = component_values
    if pr_numbers:
        if len(pr_numbers) == 1:
            metadata["pr"] = pr_numbers[0]
        else:
            metadata["prs"] = pr_numbers

    path = write_entry(project_root, metadata, body, default_project=config.id)
    try:
        display_path = path.relative_to(Path.cwd())
    except ValueError:
        display_path = path
    log_success(f"entry created: {display_path}")
    return path


@click.command("add")
@click.option("--title", help="Title for the changelog entry.")
@click.option(
    "--type",
    "entry_type",
    help="Entry type.",
)
@click.option(
    "--project",
    "project_override",
    help="Assign the entry to a project (must match the configured project).",
)
@click.option(
    "--component",
    "components",
    multiple=True,
    help="Component associated with the change (repeat for multiple).",
)
@click.option("--author", "authors", multiple=True, help="GitHub username of an author.")
@click.option(
    "--co-author",
    "co_authors",
    multiple=True,
    help="Additional author (combined with inferred/explicit author).",
)
@click.option(
    "--pr",
    "prs",
    multiple=True,
    type=str,
    help="Related pull request number (repeat for multiple).",
)
@click.option(
    "--description",
    help="Short body text for the entry (skips opening an editor).",
)
@click.option(
    "--description-file",
    type=click.Path(path_type=Path, dir_okay=False, exists=False),
    help="File containing body text for the entry. Use '-' to read from stdin.",
)
@click.pass_obj
def add(
    ctx: CLIContext,
    title: Optional[str],
    entry_type: Optional[str],
    project_override: Optional[str],
    components: tuple[str, ...],
    authors: tuple[str, ...],
    co_authors: tuple[str, ...],
    prs: tuple[str, ...],
    description: Optional[str],
    description_file: Optional[Path],
) -> None:
    """Create a new changelog entry."""
    resolved_description = _resolve_description_input(description, description_file)
    create_entry(
        ctx,
        title=title,
        entry_type=entry_type,
        project_override=project_override,
        components=components,
        authors=authors,
        co_authors=co_authors,
        prs=prs,
        description=resolved_description,
    )

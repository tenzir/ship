"""Python-friendly facade for invoking tenzir-changelog functionality."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, Optional, Sequence

from .cli import (
    CLIContext,
    ShowView,
    create_cli_context,
    create_entry,
    create_release,
    publish_release,
    render_release_notes,
    run_show_entries,
    run_validate,
)

LiteralMarkdownJson = Literal["markdown", "json"]


class Changelog:
    """High-level helper that mirrors the CLI commands for Python callers."""

    def __init__(
        self,
        *,
        root: Path | str | None = None,
        roots: Sequence[Path | str] | None = None,
        config: Path | str | None = None,
        debug: bool = False,
    ) -> None:
        if root and roots:
            raise ValueError("Provide either 'root' or 'roots', not both.")
        root_candidates: list[Path] = []
        if roots:
            root_candidates = [Path(value) for value in roots]
        elif root:
            root_candidates = [Path(root)]
        resolved_config = Path(config) if config is not None else None
        self._ctx = create_cli_context(
            roots=tuple(root_candidates),
            config=resolved_config,
            debug=debug,
        )

    @property
    def context(self) -> CLIContext:
        """Expose the underlying CLIContext for advanced scenarios."""

        return self._ctx

    def show(
        self,
        *,
        identifiers: Sequence[str] | None = None,
        view: ShowView = "table",
        project_filter: Sequence[str] | None = None,
        component_filter: Sequence[str] | None = None,
        banner: bool = False,
        compact: Optional[bool] = None,
        include_emoji: bool = True,
    ) -> None:
        """Render entries using the same layouts as ``tenzir-changelog show``."""

        run_show_entries(
            self._ctx,
            identifiers=identifiers or (),
            view=view,
            project_filter=project_filter or (),
            component_filter=component_filter or (),
            banner=banner,
            compact=compact,
            include_emoji=include_emoji,
        )

    def add(
        self,
        *,
        title: Optional[str] = None,
        entry_type: Optional[str] = None,
        project_override: Optional[str] = None,
        components: Sequence[str] | None = None,
        authors: Sequence[str] | None = None,
        co_authors: Sequence[str] | None = None,
        prs: Sequence[str] | None = None,
        description: Optional[str] = None,
    ) -> Path:
        """Create a changelog entry and return the resulting file path."""

        return create_entry(
            self._ctx,
            title=title,
            entry_type=entry_type,
            project_override=project_override,
            components=components,
            authors=authors,
            co_authors=co_authors,
            prs=prs,
            description=description,
            allow_interactive=False,
        )

    def release_create(
        self,
        *,
        version: Optional[str],
        title: Optional[str] = None,
        intro_text: Optional[str] = None,
        release_date: Optional[datetime] = None,
        intro_file: Optional[Path] = None,
        compact: Optional[bool] = None,
        assume_yes: bool = False,
        version_bump: Optional[str] = None,
    ) -> None:
        """Create or update a release manifest."""

        create_release(
            self._ctx,
            version=version,
            title=title,
            intro_text=intro_text,
            release_date=release_date,
            intro_file=intro_file,
            compact=compact,
            assume_yes=assume_yes,
            version_bump=version_bump,
            title_explicit=title is not None,
            compact_explicit=compact is not None,
        )

    def release_notes(
        self,
        identifier: str,
        *,
        view: LiteralMarkdownJson = "markdown",
        compact: Optional[bool] = None,
        include_emoji: bool = True,
    ) -> None:
        """Render release notes for a specific release or ``-`` for unreleased."""

        render_release_notes(
            self._ctx,
            identifier=identifier,
            view=view,
            compact=compact,
            include_emoji=include_emoji,
            compact_explicit=compact is not None,
        )

    def release_publish(
        self,
        *,
        version: str,
        draft: bool = False,
        prerelease: bool = False,
        create_tag: bool = False,
        assume_yes: bool = False,
    ) -> None:
        """Publish a release to GitHub using the same workflow as the CLI."""

        publish_release(
            self._ctx,
            version=version,
            draft=draft,
            prerelease=prerelease,
            create_tag=create_tag,
            assume_yes=assume_yes,
        )

    def validate(self) -> None:
        """Run the validator against the configured project."""

        run_validate(self._ctx)

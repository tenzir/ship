"""Python-friendly facade for invoking tenzir-ship functionality."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional, Sequence

from .cli import (
    CLIContext,
    ShowView,
    _get_latest_release_manifest,
    create_cli_context,
    create_entry,
    create_release,
    publish_release,
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
        config: Path | str | None = None,
        debug: bool = False,
    ) -> None:
        resolved_root = Path(root) if root is not None else None
        resolved_config = Path(config) if config is not None else None
        self._ctx = create_cli_context(
            root=resolved_root,
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
        explicit_links: bool = False,
        release_mode: bool = False,
        select_all: bool = False,
        released_only: bool = False,
    ) -> None:
        """Render entries using the same layouts as ``tenzir-ship show``.

        Args:
            identifiers: Row numbers, entry IDs, release versions, or "-".
            view: Output format ("table", "card", "markdown", "json").
            project_filter: Filter to specific project IDs.
            component_filter: Filter to specific component labels.
            banner: Display project banner above table output.
            compact: Use compact bullet-list layout.
            include_emoji: Include type emoji in output.
            explicit_links: Render @mentions and PRs as explicit Markdown links.
            release_mode: Display entries grouped by release with full metadata.
            select_all: Show all entries from all releases.
            released_only: Exclude unreleased entries (use with select_all).
        """

        run_show_entries(
            self._ctx,
            identifiers=identifiers or (),
            view=view,
            project_filter=project_filter or (),
            component_filter=component_filter or (),
            banner=banner,
            compact=compact,
            include_emoji=include_emoji,
            explicit_links=explicit_links,
            release_mode=release_mode,
            select_all=select_all,
            released_only=released_only,
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
        explicit_links: bool = False,
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
            explicit_links=explicit_links,
            assume_yes=assume_yes,
            version_bump=version_bump,
            title_explicit=title is not None,
            compact_explicit=compact is not None,
        )

    def release_version(self, *, bare: bool = False) -> str:
        """Get the latest released version.

        Args:
            bare: If True, strip the 'v' prefix from the version.

        Returns:
            The latest released version string.

        Raises:
            ValueError: If no releases exist.
        """
        manifest = _get_latest_release_manifest(self._ctx.project_root)
        if manifest is None:
            raise ValueError("No releases found. Create a release first with 'release create'.")

        version = manifest.version
        if bare:
            version = version.lstrip("vV")

        return version

    def release_publish(
        self,
        *,
        version: str | None = None,
        draft: bool = False,
        prerelease: bool = False,
        no_latest: bool = False,
        create_tag: bool = False,
        create_commit: bool = False,
        commit_message: str | None = None,
        assume_yes: bool = False,
    ) -> None:
        """Publish a release to GitHub using the same workflow as the CLI.

        If no version is provided, defaults to the latest release.
        """

        resolved_version = version
        if resolved_version is None:
            manifest = _get_latest_release_manifest(self._ctx.project_root)
            if manifest is None:
                raise ValueError("No releases found. Create a release first with 'release create'.")
            resolved_version = manifest.version

        publish_release(
            self._ctx,
            version=resolved_version,
            draft=draft,
            prerelease=prerelease,
            no_latest=no_latest,
            create_tag=create_tag,
            create_commit=create_commit,
            commit_message=commit_message,
            assume_yes=assume_yes,
        )

    def validate(self) -> None:
        """Run the validator against the configured project."""

        run_validate(self._ctx)

    def list_modules(self) -> list[dict[str, Any]]:
        """Return discovered modules as a list of dictionaries.

        Each dictionary contains:
        - id: The module's project ID
        - name: The module's display name
        - path: The absolute path to the module's changelog directory
        - relative_path: The path relative to the parent for display
        """
        return [
            {
                "id": m.config.id,
                "name": m.config.name,
                "path": str(m.root),
                "relative_path": m.relative_path,
            }
            for m in self._ctx.get_modules()
        ]

    def get_module(self, module_id: str) -> "Changelog":
        """Return a Changelog instance for a specific module.

        Args:
            module_id: The ID of the module to retrieve.

        Returns:
            A new Changelog instance configured for the module.

        Raises:
            ValueError: If no module with the given ID is found.
        """
        for module in self._ctx.get_modules():
            if module.config.id == module_id:
                return Changelog(root=module.root)
        available = [m.config.id for m in self._ctx.get_modules()]
        raise ValueError(
            f"Module '{module_id}' not found. Available: {', '.join(available) or 'none'}"
        )

"""Init command for scaffolding a changelog project."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from ..config import (
    CHANGELOG_DIRECTORY_NAME,
    Config,
    default_config_path,
    load_package_config,
    package_metadata_path,
    save_config,
)
from ..entries import entry_directory
from ..utils import abort_on_user_interrupt, guess_git_remote, log_info, log_success, slugify
from ._add import _prompt_optional, _prompt_text
from ._core import CLIContext, DEFAULT_PROJECT_ID

__all__ = ["init_cmd"]


def _default_project_id(workspace_root: Path) -> str:
    slug = slugify(workspace_root.name)
    return slug or DEFAULT_PROJECT_ID


def _default_project_name(project_id: str) -> str:
    words = project_id.replace("-", " ").strip()
    return words.title() if words else "Changelog"


def _current_cli_root_param() -> Path | None:
    root_ctx = click.get_current_context().find_root()
    value = root_ctx.params.get("root")
    if isinstance(value, Path):
        return value.resolve()
    return None


def _current_cli_config_param() -> Path | None:
    root_ctx = click.get_current_context().find_root()
    value = root_ctx.params.get("config")
    if isinstance(value, Path):
        return value.resolve()
    return None


def _resolve_workspace_root(project_root: Path) -> Path:
    explicit_root = _current_cli_root_param()
    if explicit_root is not None:
        if explicit_root.name == CHANGELOG_DIRECTORY_NAME:
            return explicit_root.parent
        return explicit_root
    if project_root.name == CHANGELOG_DIRECTORY_NAME:
        return project_root.parent
    return Path.cwd().resolve()


def _has_non_hidden_children(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any(not child.name.startswith(".") for child in path.iterdir())


def _resolve_package_mode(project_root: Path, package_mode: bool | None) -> bool:
    package_path = package_metadata_path(project_root)
    has_package_metadata = package_path.is_file()
    if package_mode is True and not has_package_metadata:
        raise click.ClickException(f"--package requires package metadata at {package_path}.")
    if package_mode is None:
        return has_package_metadata
    return package_mode


def _validate_init_target(project_root: Path) -> None:
    if project_root.exists() and not project_root.is_dir():
        raise click.ClickException(
            f"Cannot initialize project at non-directory path {project_root}."
        )

    config_path = default_config_path(project_root)
    unreleased_dir = entry_directory(project_root)
    releases_dir = project_root / "releases"
    if config_path.exists() or unreleased_dir.exists() or releases_dir.exists():
        raise click.ClickException(f"A tenzir-ship project already exists at {project_root}.")

    if _has_non_hidden_children(project_root):
        raise click.ClickException(f"Refusing to initialize non-empty directory {project_root}.")


def _confirm_initialization(message: str) -> None:
    try:
        should_continue = click.confirm(message, default=True)
    except (click.exceptions.Abort, KeyboardInterrupt) as exc:
        abort_on_user_interrupt(exc)
    if not should_continue:
        raise click.ClickException("Initialization cancelled; no files were created.")


def _build_standalone_config(
    *,
    workspace_root: Path,
    project_id: Optional[str],
    name: Optional[str],
    description: Optional[str],
    repository: Optional[str],
    assume_yes: bool,
) -> Config:
    provided_id = (project_id or "").strip() or None
    provided_name = (name or "").strip() or None
    provided_description = (description or "").strip() or None
    provided_repository = (repository or "").strip() or None

    inferred_id = _default_project_id(workspace_root)
    inferred_repository = guess_git_remote(workspace_root)

    if assume_yes:
        if provided_id is None:
            raise click.ClickException("--id is required when using --yes in standalone mode.")
        final_id = provided_id
        final_name = provided_name or _default_project_name(final_id)
        final_description = provided_description or ""
        final_repository = provided_repository or inferred_repository
        return Config(
            id=final_id,
            name=final_name,
            description=final_description,
            repository=final_repository,
        )

    final_id_optional = provided_id
    if final_id_optional is None:
        final_id_optional = _prompt_text(
            "Project ID", default=inferred_id, show_default=True
        ).strip()
    if not final_id_optional:
        raise click.ClickException("Project ID is required.")
    final_id = final_id_optional

    inferred_name = _default_project_name(final_id)
    final_name_optional = provided_name
    if final_name_optional is None:
        final_name_optional = _prompt_text(
            "Project name", default=inferred_name, show_default=True
        ).strip()
    if not final_name_optional:
        raise click.ClickException("Project name is required.")
    final_name = final_name_optional

    final_description_optional = provided_description
    if final_description_optional is None:
        final_description_optional = _prompt_optional("Description", default="") or ""
    final_description = final_description_optional

    final_repository = provided_repository
    if final_repository is None:
        final_repository = _prompt_optional("Repository", default=inferred_repository)

    return Config(
        id=final_id,
        name=final_name,
        description=final_description,
        repository=final_repository,
    )


@click.command("init")
@click.option(
    "--yes",
    "assume_yes",
    is_flag=True,
    help="Initialize the changelog scaffold without interactive prompts.",
)
@click.option(
    "--package",
    "package_mode",
    flag_value=True,
    default=None,
    help="Initialize in package mode using metadata from package.yaml.",
)
@click.option(
    "--standalone",
    "package_mode",
    flag_value=False,
    help="Initialize a standalone changelog project with config.yaml.",
)
@click.option("--id", "project_id", help="Project identifier for standalone mode.")
@click.option("--name", help="Project display name for standalone mode.")
@click.option("--description", help="Project description for standalone mode.")
@click.option(
    "--repository",
    help="GitHub repository slug (owner/name) for standalone mode.",
)
@click.pass_obj
def init_cmd(
    ctx: CLIContext,
    assume_yes: bool,
    package_mode: bool | None,
    project_id: Optional[str],
    name: Optional[str],
    description: Optional[str],
    repository: Optional[str],
) -> None:
    """Create the initial changelog scaffold."""

    explicit_config = _current_cli_config_param()
    if explicit_config is not None:
        raise click.ClickException(
            "--config is not supported with 'init'; tenzir-ship projects always use config.yaml."
        )

    project_root = ctx.project_root
    workspace_root = _resolve_workspace_root(project_root)
    project_mode = _resolve_package_mode(project_root, package_mode)
    _validate_init_target(project_root)

    if project_mode:
        if any(value is not None for value in (project_id, name, description, repository)):
            raise click.ClickException(
                "Metadata flags are not supported in package mode; update package.yaml or use --standalone."
            )
        package_path = package_metadata_path(project_root)
        try:
            config = load_package_config(package_path)
        except ValueError as error:
            raise click.ClickException(str(error)) from error

        if not assume_yes:
            log_info(f"package metadata: {package_path}")
            log_info(f"changelog root: {project_root}")
            log_info(f"project id: {config.id}")
            log_info(f"project name: {config.name}")
            _confirm_initialization("Initialize package changelog scaffold?")

        project_root.mkdir(parents=True, exist_ok=True)
        entry_directory(project_root).mkdir(parents=True, exist_ok=True)
        log_success(f"initialized package changelog at {project_root}")
        return

    config = _build_standalone_config(
        workspace_root=workspace_root,
        project_id=project_id,
        name=name,
        description=description,
        repository=repository,
        assume_yes=assume_yes,
    )

    if not assume_yes:
        log_info(f"changelog root: {project_root}")
        log_info(f"config path: {default_config_path(project_root)}")
        log_info(f"project id: {config.id}")
        log_info(f"project name: {config.name}")
        if config.repository:
            log_info(f"repository: {config.repository}")
        _confirm_initialization("Initialize changelog scaffold?")

    project_root.mkdir(parents=True, exist_ok=True)
    save_config(config, default_config_path(project_root))
    entry_directory(project_root).mkdir(parents=True, exist_ok=True)
    log_success(f"initialized changelog project at {project_root}")

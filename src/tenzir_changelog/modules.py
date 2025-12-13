"""Module discovery for nested changelog projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from .config import load_project_config
from .utils import log_warning

if TYPE_CHECKING:
    from .config import Config


@dataclass
class Module:
    """A discovered nested changelog project."""

    root: Path  # Absolute path to module's changelog directory
    config: "Config"  # Module's loaded config
    relative_path: str  # Path relative to parent (for display)


def discover_modules(parent_root: Path, glob_pattern: str) -> Iterator[Module]:
    """Discover modules matching glob pattern relative to parent.

    The glob pattern is resolved relative to the parent changelog root.
    Each matched directory must contain a valid config.yaml.

    Args:
        parent_root: The parent changelog project root directory.
        glob_pattern: Glob pattern for finding module directories.

    Yields:
        Module instances for each valid discovered module.
    """
    # Resolve the base path for globbing
    # Handle patterns like "../packages/*/changelog" by resolving relative to parent_root
    base_path = parent_root

    # Split the pattern to handle leading ../ components
    pattern_parts = Path(glob_pattern).parts
    while pattern_parts and pattern_parts[0] == "..":
        base_path = base_path.parent
        pattern_parts = pattern_parts[1:]

    # Reconstruct the remaining pattern
    remaining_pattern = str(Path(*pattern_parts)) if pattern_parts else "*"

    # Find all matching directories
    for match in sorted(base_path.glob(remaining_pattern)):
        if not match.is_dir():
            continue

        # Skip if this is the parent itself
        resolved_match = match.resolve()
        if resolved_match == parent_root.resolve():
            continue

        # Try to load the config
        try:
            config = load_project_config(resolved_match)
        except (FileNotFoundError, ValueError) as exc:
            log_warning(f"Skipping {match}: {exc}")
            continue

        # Calculate relative path for display
        try:
            relative_path = str(match.relative_to(parent_root))
        except ValueError:
            # Path is not relative to parent_root (e.g., ../packages/foo)
            relative_path = str(match.relative_to(base_path))
            if glob_pattern.startswith(".."):
                # Reconstruct the relative path with leading ../
                prefix = "../" * glob_pattern.count("../")
                relative_path = prefix + relative_path

        yield Module(
            root=resolved_match,
            config=config,
            relative_path=relative_path,
        )


def discover_modules_from_config(parent_root: Path, config: "Config") -> list[Module]:
    """Discover modules based on config's modules field.

    Args:
        parent_root: The parent changelog project root directory.
        config: The parent project's configuration.

    Returns:
        List of Module instances, sorted by module ID. Empty if no modules configured.
    """
    if not config.modules:
        return []

    modules = list(discover_modules(parent_root, config.modules))

    # Sort by module ID for deterministic ordering
    modules.sort(key=lambda m: m.config.id)

    return modules

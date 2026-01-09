"""Export functions for markdown and JSON output."""

from __future__ import annotations

from datetime import date
from typing import Optional

from ..config import Config
from ..entries import Entry
from ..releases import ReleaseManifest
from ..utils import extract_excerpt, normalize_markdown
from ._core import (
    DEFAULT_ENTRY_TYPE,
    ENTRY_EXPORT_ORDER,
    _build_authors_structured,
    _build_prs_structured,
    _collect_author_pr_text,
    _format_author_line,
    _format_section_title,
)

__all__ = [
    "_entry_to_dict",
    "_build_release_payload",
    "_render_markdown_release_block",
    "_export_markdown_release",
    "_export_markdown_compact",
    "_export_json_payload",
]


def _entry_to_dict(
    entry: Entry,
    config: Config,
    *,
    compact: bool = False,
) -> dict[str, object]:
    """Convert an entry to a dictionary for JSON export."""
    metadata = entry.metadata
    entry_type = metadata.get("type", DEFAULT_ENTRY_TYPE)
    title = metadata.get("title", "Untitled")

    data = {
        "id": entry.entry_id,
        "title": title,
        "type": entry_type,
        "created": entry.created_at.isoformat() if entry.created_at else None,
        "project": entry.project or config.id,
        "prs": _build_prs_structured(metadata, config),
        "authors": _build_authors_structured(metadata),
        "body": entry.body,
    }
    if entry.components:
        data["components"] = entry.components
    if compact:
        data["excerpt"] = extract_excerpt(entry.body)
    return data


def _build_release_payload(
    manifest: ReleaseManifest | None,
    entries: list[Entry],
    config: Config,
    *,
    compact: bool = False,
) -> dict[str, object]:
    """Build a JSON payload for a single release with entries."""
    entries_by_type: dict[str, list[Entry]] = {}
    for entry in entries:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        entries_by_type.setdefault(entry_type, []).append(entry)
    ordered_entries: list[Entry] = []
    for type_key in ENTRY_EXPORT_ORDER:
        ordered_entries.extend(entries_by_type.pop(type_key, []))
    for remaining in entries_by_type.values():
        ordered_entries.extend(remaining)

    if manifest:
        data: dict[str, object] = {
            "version": manifest.version,
            "title": manifest.title or manifest.version,
            "intro": manifest.intro or None,
            "project": config.id,
            "created": manifest.created.isoformat(),
        }
    else:
        data = {
            "version": None,
            "title": "Unreleased Changes",
            "intro": None,
            "project": config.id,
            "created": date.today().isoformat(),
        }

    payload_entries = [_entry_to_dict(entry, config, compact=compact) for entry in ordered_entries]
    data["entries"] = payload_entries
    if compact:
        data["compact"] = True
    return data


def _render_markdown_release_block(
    manifest: ReleaseManifest | None,
    entries: list[Entry],
    config: Config,
    release_index: dict[str, list[str]],
    *,
    include_emoji: bool = True,
    explicit_links: bool = False,
    compact: bool = False,
) -> str:
    """Render a single release as Markdown with H1 title, intro, and grouped entries."""
    lines: list[str] = []

    if manifest:
        title = manifest.title or manifest.version
    else:
        title = "Unreleased Changes"
    lines.append(f"# {title}")
    lines.append("")

    if manifest and manifest.intro:
        lines.append(manifest.intro)
        lines.append("")

    if not entries:
        lines.append("No changes found.")
        return "\n".join(lines).strip() + "\n"

    entries_by_type: dict[str, list[Entry]] = {}
    for entry in entries:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        entries_by_type.setdefault(entry_type, []).append(entry)

    for type_key in ENTRY_EXPORT_ORDER:
        type_entries = entries_by_type.get(type_key) or []
        if not type_entries:
            continue
        section_title = _format_section_title(type_key, include_emoji)
        lines.append(f"## {section_title}")
        lines.append("")

        if compact:
            for entry in type_entries:
                metadata = entry.metadata
                excerpt = extract_excerpt(entry.body)
                bullet_text = excerpt or metadata.get("title", "Untitled")
                component_labels = entry.components
                if component_labels:
                    components_display = ", ".join(component_labels)
                    bullet = f"- **{components_display}**: {bullet_text}"
                else:
                    bullet = f"- {bullet_text}"
                author_text, pr_text = _collect_author_pr_text(
                    entry, config, explicit_links=explicit_links
                )
                suffix_parts: list[str] = []
                if author_text:
                    suffix_parts.append(f"by {author_text}")
                if pr_text:
                    suffix_parts.append(f"in {pr_text}")
                if suffix_parts:
                    bullet = f"{bullet} ({' '.join(suffix_parts)})"
                lines.append(bullet)
            lines.append("")
        else:
            for entry in type_entries:
                metadata = entry.metadata
                entry_title = metadata.get("title", "Untitled")
                lines.append(f"### {entry_title}")
                lines.append("")
                body = entry.body.strip()
                if body:
                    lines.append(body)
                    lines.append("")
                author_line = _format_author_line(entry, config, explicit_links=explicit_links)
                if author_line:
                    lines.append(author_line)
                    lines.append("")

    raw = "\n".join(lines).strip()
    normalized = normalize_markdown(raw)
    return f"{normalized}\n"


def _export_markdown_release(
    manifest: Optional[ReleaseManifest],
    entries: list[Entry],
    config: Config,
    release_index: dict[str, list[str]],
    *,
    include_emoji: bool = True,
    explicit_links: bool = False,
) -> str:
    """Export entries as Markdown with full body text."""
    lines: list[str] = []

    if not entries:
        lines.append("No changes found.")
        return "\n".join(lines).strip() + "\n"

    entries_by_type: dict[str, list[Entry]] = {}
    for entry in entries:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        entries_by_type.setdefault(entry_type, []).append(entry)

    for type_key in ENTRY_EXPORT_ORDER:
        type_entries = entries_by_type.get(type_key) or []
        if not type_entries:
            continue
        section_title = _format_section_title(type_key, include_emoji)
        lines.append(f"## {section_title}")
        lines.append("")
        for entry in type_entries:
            metadata = entry.metadata
            title = metadata.get("title", "Untitled")
            lines.append(f"### {title}")
            lines.append("")
            body = entry.body.strip()
            if body:
                lines.append(body)
                lines.append("")
            author_line = _format_author_line(entry, config, explicit_links=explicit_links)
            if author_line:
                lines.append(author_line)
                lines.append("")

    if not lines:
        return ""
    raw = "\n".join(lines).strip()
    normalized = normalize_markdown(raw)
    return f"{normalized}\n"


def _export_markdown_compact(
    manifest: Optional[ReleaseManifest],
    entries: list[Entry],
    config: Config,
    release_index: dict[str, list[str]],
    *,
    include_emoji: bool = True,
    explicit_links: bool = False,
) -> str:
    """Export entries as compact Markdown bullet list."""
    lines: list[str] = []

    if not entries:
        lines.append("No changes found.")
        return "\n".join(lines).strip() + "\n"

    entries_by_type: dict[str, list[Entry]] = {}
    for entry in entries:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        entries_by_type.setdefault(entry_type, []).append(entry)

    for type_key in ENTRY_EXPORT_ORDER:
        type_entries = entries_by_type.get(type_key) or []
        if not type_entries:
            continue
        section_title = _format_section_title(type_key, include_emoji)
        lines.append(f"## {section_title}")
        lines.append("")
        for entry in type_entries:
            metadata = entry.metadata
            excerpt = extract_excerpt(entry.body)
            bullet_text = excerpt or metadata.get("title", "Untitled")
            component_labels = entry.components
            if component_labels:
                components_display = ", ".join(component_labels)
                bullet = f"- **{components_display}**: {bullet_text}"
            else:
                bullet = f"- {bullet_text}"
            author_text, pr_text = _collect_author_pr_text(
                entry, config, explicit_links=explicit_links
            )
            suffix_parts: list[str] = []
            if author_text:
                suffix_parts.append(f"by {author_text}")
            if pr_text:
                suffix_parts.append(f"in {pr_text}")
            if suffix_parts:
                bullet = f"{bullet} ({' '.join(suffix_parts)})"
            lines.append(bullet)
        lines.append("")

    if not lines:
        return ""
    raw = "\n".join(lines).strip()
    normalized = normalize_markdown(raw)
    return f"{normalized}\n"


def _export_json_payload(
    manifest: Optional[ReleaseManifest],
    entries: list[Entry],
    config: Config,
    *,
    compact: bool = False,
    fallback_heading: str = "Unreleased Changes",
    fallback_created: date | None = None,
) -> dict[str, object]:
    """Build JSON payload for export."""
    entries_by_type: dict[str, list[Entry]] = {}
    for entry in entries:
        entry_type = entry.metadata.get("type", DEFAULT_ENTRY_TYPE)
        entries_by_type.setdefault(entry_type, []).append(entry)
    ordered_entries: list[Entry] = []
    for type_key in ENTRY_EXPORT_ORDER:
        ordered_entries.extend(entries_by_type.pop(type_key, []))
    for remaining in entries_by_type.values():
        ordered_entries.extend(remaining)

    data: dict[str, object] = {}
    if manifest:
        data.update(
            {
                "version": manifest.version,
                "title": manifest.title or manifest.version,
                "intro": manifest.intro or None,
                "project": config.id,
                "created": manifest.created.isoformat(),
            }
        )
    else:
        created_value = fallback_created or date.today()
        data.update(
            {
                "version": None,
                "title": fallback_heading if fallback_heading else None,
                "intro": None,
                "project": config.id,
                "created": created_value.isoformat(),
            }
        )

    payload_entries = [_entry_to_dict(entry, config, compact=compact) for entry in ordered_entries]
    data["entries"] = payload_entries
    if compact:
        data["compact"] = True
    return data

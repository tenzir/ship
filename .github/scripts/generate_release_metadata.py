#!/usr/bin/env python3
"""Generate release workflow metadata from a structured tenzir-ship release plan."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural or singular + 's'}"


def _join_phrases(phrases: list[str]) -> str:
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"


def _build_intro(plan: dict[str, Any]) -> str:
    release = plan["release"]
    resolved_intro = release.get("resolved_intro")
    if isinstance(resolved_intro, str) and resolved_intro.strip():
        return resolved_intro.strip()

    project_name = str(plan["project"]["name"])
    entry_counts = release["entry_counts"]
    parts: list[str] = []
    if entry_counts.get("breaking"):
        parts.append(_pluralize(int(entry_counts["breaking"]), "breaking change"))
    if entry_counts.get("feature"):
        parts.append(_pluralize(int(entry_counts["feature"]), "feature"))
    if entry_counts.get("bugfix"):
        parts.append(_pluralize(int(entry_counts["bugfix"]), "bug fix", "bug fixes"))
    if entry_counts.get("change"):
        parts.append(_pluralize(int(entry_counts["change"]), "additional change"))

    if not parts:
        return f"This release updates {project_name}."

    if entry_counts.get("breaking") or entry_counts.get("feature"):
        lead_verb = "introduces"
    elif entry_counts.get("bugfix") and int(entry_counts["bugfix"]) == int(entry_counts["total"]):
        lead_verb = "fixes"
    else:
        lead_verb = "updates"

    first_sentence = f"This release {lead_verb} {_join_phrases(parts)} for {project_name}."

    highlights = plan.get("highlights") or []
    titles = [
        str(item.get("title", "")).strip()
        for item in highlights
        if isinstance(item, dict) and str(item.get("title", "")).strip()
    ]
    if not titles:
        return first_sentence

    if len(titles) == 1:
        second_sentence = f'The headline change is "{titles[0]}".'
    else:
        quoted = [f'"{title}"' for title in titles[:2]]
        second_sentence = f"Highlights include {_join_phrases(quoted)}."
    return f"{first_sentence} {second_sentence}"


def _emit_output(key: str, value: str) -> None:
    delimiter = "__TENZIR_SHIP_EOF__"
    print(f"{key}<<{delimiter}")
    print(value)
    print(delimiter)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: generate_release_metadata.py <release-plan.json>", file=sys.stderr)
        return 2
    plan_path = Path(sys.argv[1])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    intro = _build_intro(plan)
    _emit_output("intro", intro)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Skill tool: use_skill loads a skill body and reference list into context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from frontmatter import split_frontmatter
import paths
from skill_catalog import scan_skills

MAX_SKILL_READ_BYTES = 200_000


def _use_skill(workspace: Path, name: str) -> dict[str, Any]:
    raw_name = (name or "").strip()
    if not raw_name or "/" in raw_name or "\\" in raw_name or ".." in raw_name:
        return {
            "ok": False,
            "error": {
                "code": "INVALID_SKILL_NAME",
                "message": f"Invalid skill name '{name}'. Names cannot contain slashes or '..'.",
            },
        }

    catalog = scan_skills(workspace)
    available_names = [s.name for s in catalog.skills]
    skill_meta = next((s for s in catalog.skills if s.name == raw_name), None)

    if not skill_meta:
        avail_str = ", ".join(available_names) if available_names else "none"
        return {
            "ok": False,
            "error": {
                "code": "SKILL_NOT_FOUND",
                "message": f"Skill '{raw_name}' not found. Available skills: {avail_str}.",
            },
        }

    skill_path = (workspace / skill_meta.location).resolve()
    if not skill_path.is_file():
        return {
            "ok": False,
            "error": {
                "code": "SKILL_NOT_FOUND",
                "message": f"Skill file {skill_meta.location} does not exist.",
            },
        }

    size = skill_path.stat().st_size
    if size > MAX_SKILL_READ_BYTES:
        return {
            "ok": False,
            "error": {
                "code": "FILE_TOO_LARGE",
                "message": f"Skill file exceeds maximum size of {MAX_SKILL_READ_BYTES} bytes.",
            },
        }

    try:
        raw_text = skill_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "ok": False,
            "error": {
                "code": "NOT_UTF8_TEXT",
                "message": f"Skill file {skill_meta.location} is not valid UTF-8.",
            },
        }

    try:
        data, body = split_frontmatter(raw_text)
        desc = str(data.get("description", skill_meta.description))
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "code": "INVALID_SKILL_FRONTMATTER",
                "message": f"Failed to parse skill frontmatter: {exc}",
            },
        }

    skill_dir = skill_path.parent
    references: list[str] = []
    for ref_path in sorted(skill_dir.rglob("*")):
        if ref_path.is_file() and ref_path.name != "SKILL.md":
            rel_ref = ref_path.relative_to(skill_dir).as_posix()
            references.append(rel_ref)

    return {
        "ok": True,
        "name": raw_name,
        "description": desc,
        "content": body,
        "references": references,
        "chars": len(body),
    }


@tool
def use_skill(name: str) -> str:
    """Load the body and references of an available skill from the workspace catalog.

    name: the skill name as declared in <available_skills>.
    Success: {"ok": true, "name": ..., "description": ..., "content": ..., "references": [...], "chars": ...}.
    Error: {"ok": false, "error": {"code": ..., "message": ...}}.
    """
    return json.dumps(_use_skill(paths.WORKSPACE_DIR, name), ensure_ascii=False)

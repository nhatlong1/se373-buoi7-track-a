"""Workspace file tools: list_files, read_file, and write_file.

Paths are always relative to the workspace. Target paths are resolved and checked to remain
within the workspace (read/list) or within output/ and skills/<slug>/ (write).
Expected errors return JSON with {"ok": false, "error": {"code": ..., "message": ...}}.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from frontmatter import parse_frontmatter
import paths

MAX_READ_BYTES = 200_000


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _resolve(workspace: Path, path: str) -> tuple[Path | None, dict[str, Any] | None]:
    raw = (path or "").strip()
    if not raw:
        return None, _error(
            "INVALID_PATH", "Path cannot be empty. Use workspace-relative paths."
        )
    if Path(raw).is_absolute() or raw.startswith("~"):
        return None, _error(
            "PATH_OUTSIDE_WORKSPACE",
            f"Absolute paths are not allowed: {raw}. Use workspace-relative paths.",
        )
    root = workspace.resolve()
    target = (root / raw).resolve()
    if not target.is_relative_to(root):
        return None, _error(
            "PATH_OUTSIDE_WORKSPACE", f"Path escapes workspace boundaries: {raw}"
        )
    return target, None


def _read(workspace: Path, path: str) -> dict[str, Any]:
    target, error = _resolve(workspace, path)
    if error:
        return error
    assert target is not None
    rel = target.relative_to(workspace.resolve()).as_posix()
    if not target.exists():
        return _error("FILE_NOT_FOUND", f"File not found: {rel}")
    if target.is_dir():
        return _error("IS_A_DIRECTORY", f"Target is a directory, not a file: {rel}")
    size = target.stat().st_size
    if size > MAX_READ_BYTES:
        return _error(
            "FILE_TOO_LARGE",
            f"File {rel} is {size} bytes, exceeding maximum {MAX_READ_BYTES} bytes.",
        )
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return _error("NOT_UTF8_TEXT", f"File {rel} is not valid UTF-8 text.")
    return {"ok": True, "path": rel, "content": content}


def _write(workspace: Path, path: str, content: str) -> dict[str, Any]:
    target, error = _resolve(workspace, path)
    if error:
        return error
    assert target is not None
    root = workspace.resolve()
    output_root = (workspace / paths.OUTPUT_SUBDIR).resolve()
    skills_root = (workspace / paths.SKILLS_SUBDIR).resolve()

    rel = target.relative_to(root).as_posix()
    parts = Path(rel).parts

    is_output_write = False
    is_skill_write = False
    slug = ""

    if target.is_relative_to(output_root) and target != output_root:
        is_output_write = True
    elif parts and parts[0] == paths.SKILLS_SUBDIR:
        if len(parts) < 3:
            return _error(
                "PATH_NOT_WRITABLE",
                f"Writing directly to {paths.SKILLS_SUBDIR}/ is not allowed. Writes must be under output/ or skills/<slug>/.",
            )
        slug = parts[1]
        is_skill_write = True
    else:
        return _error(
            "PATH_NOT_WRITABLE",
            f"Writes are only allowed under output/ or skills/<slug>/. Received path: {path}",
        )

    # Frontmatter validation for exact skills/<slug>/SKILL.md
    if is_skill_write and rel == f"{paths.SKILLS_SUBDIR}/{slug}/SKILL.md":
        try:
            meta = parse_frontmatter(content)
            name = meta.get("name")
            desc = meta.get("description")
            if name != slug or not isinstance(desc, str) or not desc.strip():
                return _error(
                    "INVALID_SKILL_FRONTMATTER",
                    f"SKILL.md frontmatter must define name matching slug '{slug}' and a non-empty description.",
                )
        except Exception as exc:
            return _error(
                "INVALID_SKILL_FRONTMATTER",
                f"Invalid skill frontmatter: {exc}",
            )

    if target.is_dir():
        return _error("IS_A_DIRECTORY", f"Target is an existing directory: {rel}")

    status = "updated" if target.exists() else "created"
    target.parent.mkdir(parents=True, exist_ok=True)

    # Symlink race check on parent directory
    resolved_parent = target.parent.resolve()
    if is_output_write and not resolved_parent.is_relative_to(output_root):
        return _error("PATH_NOT_WRITABLE", f"Target directory escapes output/: {path}")
    if is_skill_write:
        allowed_parent = (skills_root / slug).resolve()
        if not resolved_parent.is_relative_to(allowed_parent):
            return _error(
                "PATH_NOT_WRITABLE",
                f"Target directory escapes skills/{slug}/: {path}",
            )

    data = content.encode("utf-8")
    target.write_bytes(data)
    return {"ok": True, "path": rel, "bytes": len(data), "status": status}


def _list(workspace: Path, path: str) -> dict[str, Any]:
    target, error = _resolve(workspace, path)
    if error:
        return error
    assert target is not None
    root = workspace.resolve()
    rel = target.relative_to(root).as_posix()
    if not target.exists():
        return _error("DIRECTORY_NOT_FOUND", f"Directory not found: {rel}")
    if not target.is_dir():
        return _error("NOT_A_DIRECTORY", f"Target is a file, not a directory: {rel}")
    entries = []
    for child in sorted(target.iterdir(), key=lambda p: p.name):
        child_resolved = child.resolve()
        if not child_resolved.is_relative_to(root):
            continue
        entries.append(
            {
                "name": child.name,
                "path": child.relative_to(root).as_posix(),
                "type": "directory" if child.is_dir() else "file",
            }
        )
    return {"ok": True, "path": rel, "entries": entries}


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file in the workspace and return JSON.

    path: workspace-relative path (e.g. data/notes.md, skills/authoring-skills/references/template.md).
    Success: {"ok": true, "path": ..., "content": ...}.
    Error: {"ok": false, "error": {"code": ..., "message": ...}}.
    """
    return json.dumps(_read(paths.WORKSPACE_DIR, path), ensure_ascii=False)


@tool
def write_file(path: str, content: str) -> str:
    """Write UTF-8 text content to a file under output/ or skills/<slug>/ in workspace and return JSON.

    Creates subdirectories automatically. Overwrites existing files.
    Success: {"ok": true, "path": ..., "bytes": ..., "status": "created" | "updated"}.
    Error: {"ok": false, "error": {"code": ..., "message": ...}}.
    """
    return json.dumps(_write(paths.WORKSPACE_DIR, path, content), ensure_ascii=False)


@tool
def list_files(path: str) -> str:
    """List direct entries of a workspace directory sorted by name and return JSON.

    path: workspace-relative path (e.g. ".", "output", "skills").
    Success: {"ok": true, "path": ..., "entries": [...]}.
    Error: {"ok": false, "error": {"code": ..., "message": ...}}.
    """
    return json.dumps(_list(paths.WORKSPACE_DIR, path), ensure_ascii=False)

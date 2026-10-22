"""Memory tools: memory_list, memory_read, memory_write, and memory_delete.

Operates exclusively within personal-agent/memory/.
Normalized two-layer contract: memory items are addressed by (bucket, name).
- Memory directory is harness-injected (paths.MEMORY_DIR) and completely isolated from workspace file tools.
- Bucket '/' is strictly reserved for name 'profile' (stored at memory/profile.md).
- Other buckets (e.g. 'topics', 'areas') cannot use name 'profile'.
- Directory traversal ('..', slashes, absolute paths, symlinks) is strictly blocked.
- Enforces size limits, single-line descriptions, and flat bullet shape without headings.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from frontmatter import format_frontmatter, split_frontmatter
from memory_catalog import scan_memory
import paths

MAX_MEMORY_BYTES = 8_000
MAX_DESCRIPTION_LENGTH = 300
SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _validate_bucket_and_name(
    memory_dir: Path, bucket: str, name: str
) -> tuple[str | None, str | None, Path | None, dict[str, Any] | None]:
    """Validate bucket and name contract and enforce traversal boundaries.

    Returns (normalized_bucket, normalized_name, target_file_path, error_dict).
    """
    raw_bucket = (bucket or "").strip()
    raw_name = (name or "").strip()
    if raw_name.endswith(".md"):
        raw_name = raw_name[:-3]

    if not raw_bucket:
        return (
            None,
            None,
            None,
            _error(
                "INVALID_MEMORY_BUCKET",
                "Bucket cannot be empty. Use '/' for profile, or a domain bucket like 'topics' or 'areas'.",
            ),
        )

    if not raw_name:
        return None, None, None, _error("INVALID_MEMORY_NAME", "Memory name cannot be empty.")

    # Explicit traversal check for '..' or path separators
    if ".." in raw_bucket or "/" in raw_bucket.strip("/") or "\\" in raw_bucket:
        return (
            None,
            None,
            None,
            _error(
                "INVALID_MEMORY_BUCKET",
                f"Directory traversal and multi-level paths are strictly prohibited in bucket: '{bucket}'.",
            ),
        )

    if ".." in raw_name or "/" in raw_name or "\\" in raw_name:
        return (
            None,
            None,
            None,
            _error(
                "INVALID_MEMORY_NAME",
                f"Directory traversal and slashes are strictly prohibited in memory name: '{name}'.",
            ),
        )

    # Root bucket ("/")
    if raw_bucket in ("/", "root"):
        if raw_name != "profile":
            return (
                None,
                None,
                None,
                _error(
                    "INVALID_MEMORY_NAME",
                    f"Invalid name '{raw_name}' for bucket '/'. Only 'profile' is permitted in the root ('/') bucket.",
                ),
            )
        target = memory_dir / "profile.md"
        norm_bucket = "/"
        norm_name = "profile"
    else:
        # Non-root bucket
        if raw_name == "profile":
            return (
                None,
                None,
                None,
                _error(
                    "INVALID_MEMORY_NAME",
                    f"'profile' is reserved for the root ('/') bucket. Use bucket '/' for profile.",
                ),
            )

        # Validate bucket slug (single layer, lowercase alphanumeric with hyphens)
        if not SLUG_REGEX.match(raw_bucket) or len(raw_bucket) > 64:
            return (
                None,
                None,
                None,
                _error(
                    "INVALID_MEMORY_BUCKET",
                    f"Invalid bucket '{bucket}'. Bucket must be '/' or a single-layer lowercase kebab-case slug (e.g. 'topics', 'areas').",
                ),
            )

        # Validate name slug
        if not SLUG_REGEX.match(raw_name) or len(raw_name) > 64:
            return (
                None,
                None,
                None,
                _error(
                    "INVALID_MEMORY_NAME",
                    f"Invalid memory name '{name}'. Name must be a single-layer lowercase kebab-case slug (max 64 chars).",
                ),
            )

        target = memory_dir / raw_bucket / f"{raw_name}.md"
        norm_bucket = raw_bucket
        norm_name = raw_name

    # Check symlinks before resolving target path
    if os.path.islink(target):
        return (
            None,
            None,
            None,
            _error(
                "MEMORY_SYMLINK",
                f"Symlinks are not allowed in memory: bucket='{norm_bucket}', name='{norm_name}'",
            ),
        )

    # Containment check against memory_dir
    mem_root = memory_dir.resolve()
    target_resolved = target.resolve()
    if not target_resolved.is_relative_to(mem_root):
        return (
            None,
            None,
            None,
            _error(
                "PATH_OUTSIDE_MEMORY",
                f"Resolved target escapes memory directory boundaries: {target}",
            ),
        )

    return norm_bucket, norm_name, target, None


def _list_memory(memory_dir: Path, bucket: str | None = None) -> dict[str, Any]:
    entries = scan_memory(memory_dir, bucket_filter=bucket)
    return {
        "ok": True,
        "entries": [
            {
                "bucket": e.bucket,
                "name": e.name,
                "description": e.description,
                "bytes": e.bytes,
                "updated": e.updated,
            }
            for e in entries
        ],
    }


def _read_memory(memory_dir: Path, bucket: str, name: str) -> dict[str, Any]:
    norm_bucket, norm_name, target, err = _validate_bucket_and_name(memory_dir, bucket, name)
    if err:
        return err
    assert norm_bucket is not None and norm_name is not None and target is not None

    if not target.is_file():
        return _error(
            "MEMORY_NOT_FOUND",
            f"Memory item not found: bucket='{norm_bucket}', name='{norm_name}'",
        )

    try:
        stat = target.stat()
        text = target.read_text(encoding="utf-8")
        data, body = split_frontmatter(text)
        description = str(data.get("description", ""))
        updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        return {
            "ok": True,
            "bucket": norm_bucket,
            "name": norm_name,
            "description": description,
            "content": body,
            "bytes": stat.st_size,
            "updated": updated,
        }
    except Exception as exc:
        return _error("MEMORY_READ_ERROR", f"Failed to read memory item: {exc}")


def _write_memory(
    memory_dir: Path, bucket: str, name: str, description: str, content: str
) -> dict[str, Any]:
    norm_bucket, norm_name, target, err = _validate_bucket_and_name(memory_dir, bucket, name)
    if err:
        return err
    assert norm_bucket is not None and norm_name is not None and target is not None

    # Description validation
    desc = " ".join((description or "").split())
    if not desc or len(desc) > MAX_DESCRIPTION_LENGTH:
        return _error(
            "INVALID_MEMORY_DESCRIPTION",
            f"Description must be a single non-empty line up to {MAX_DESCRIPTION_LENGTH} characters.",
        )

    # Content size validation
    raw_bytes = (content or "").encode("utf-8")
    if len(raw_bytes) > MAX_MEMORY_BYTES:
        return _error(
            "MEMORY_TOO_LARGE",
            f"Content is {len(raw_bytes)} bytes, exceeding maximum {MAX_MEMORY_BYTES} bytes.",
        )

    # Content shape validation (no Markdown headings)
    for line in (content or "").splitlines():
        if line.strip().startswith("#"):
            return _error(
                "INVALID_MEMORY_CONTENT",
                "Memory body must be flat bullets and cannot contain Markdown heading lines ('#').",
            )

    fm_dict = {"name": norm_name, "description": desc}
    formatted_file = format_frontmatter(fm_dict, content)

    target.parent.mkdir(parents=True, exist_ok=True)
    status = "updated" if target.exists() else "created"

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            delete=False,
        ) as tmp:
            tmp.write(formatted_file)
            tmp_path = Path(tmp.name)

        os.replace(tmp_path, target)
        size = target.stat().st_size
        return {
            "ok": True,
            "bucket": norm_bucket,
            "name": norm_name,
            "status": status,
            "bytes": size,
        }
    except Exception as exc:
        if "tmp_path" in locals() and tmp_path.exists():
            tmp_path.unlink()
        return _error("MEMORY_WRITE_ERROR", f"Failed to write memory item: {exc}")


def _delete_memory(memory_dir: Path, bucket: str, name: str) -> dict[str, Any]:
    norm_bucket, norm_name, target, err = _validate_bucket_and_name(memory_dir, bucket, name)
    if err:
        return err
    assert norm_bucket is not None and norm_name is not None and target is not None

    if not target.is_file():
        return _error(
            "MEMORY_NOT_FOUND",
            f"Memory item not found: bucket='{norm_bucket}', name='{norm_name}'",
        )

    try:
        target.unlink()
        return {"ok": True, "bucket": norm_bucket, "name": norm_name, "status": "deleted"}
    except Exception as exc:
        return _error("MEMORY_DELETE_ERROR", f"Failed to delete memory item: {exc}")


@tool
def memory_list(bucket: str | None = None) -> str:
    """List memory items with metadata (bucket, name, description, bytes, updated).

    bucket: optional filter ('/' for profile, or domain bucket name like 'topics', 'areas').
    Success: {"ok": true, "entries": [...]}.
    Error: {"ok": false, "error": {"code": ..., "message": ...}}.
    """
    return json.dumps(_list_memory(paths.MEMORY_DIR, bucket), ensure_ascii=False)


@tool
def memory_read(bucket: str, name: str) -> str:
    """Read a memory item by bucket and name.

    bucket: '/' for profile, or a domain bucket like 'topics' or 'areas'.
    name: 'profile' (for bucket '/'), or slug name without '.md' extension.
    Success: {"ok": true, "bucket": ..., "name": ..., "description": ..., "content": ..., "bytes": ..., "updated": ...}.
    Error: {"ok": false, "error": {"code": ..., "message": ...}}.
    """
    return json.dumps(_read_memory(paths.MEMORY_DIR, bucket, name), ensure_ascii=False)


@tool
def memory_write(bucket: str, name: str, description: str, content: str) -> str:
    """Create or update a memory item by bucket and name atomically.

    bucket: '/' for profile, or a domain bucket like 'topics' or 'areas'.
    name: 'profile' (for bucket '/'), or slug name (lowercase kebab-case).
    description: concise keyword-dense single-line description (1-300 chars).
    content: body text (flat bullets, no Markdown headings '#', max 8000 bytes).
    Success: {"ok": true, "bucket": ..., "name": ..., "status": "created" | "updated", "bytes": ...}.
    Error: {"ok": false, "error": {"code": ..., "message": ...}}.
    """
    return json.dumps(
        _write_memory(paths.MEMORY_DIR, bucket, name, description, content), ensure_ascii=False
    )


@tool
def memory_delete(bucket: str, name: str) -> str:
    """Delete a memory item by bucket and name.

    bucket: '/' for profile, or a domain bucket like 'topics' or 'areas'.
    name: 'profile' (for bucket '/'), or slug name.
    Success: {"ok": true, "bucket": ..., "name": ..., "status": "deleted"}.
    Error: {"ok": false, "error": {"code": ..., "message": ...}}.
    """
    return json.dumps(_delete_memory(paths.MEMORY_DIR, bucket, name), ensure_ascii=False)

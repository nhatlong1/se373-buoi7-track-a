"""Memory catalog: scans and indexes markdown memory files under memory/ organized by bucket and name."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from frontmatter import split_frontmatter


@dataclass(frozen=True)
class MemoryEntry:
    bucket: str  # "/" for profile, or folder name like "topics", "areas"
    name: str  # slug or "profile"
    path: str  # relative path on disk: "profile.md" or "<bucket>/<name>.md"
    description: str
    bytes: int
    updated: str


def scan_memory(memory_dir: Path, bucket_filter: str | None = None) -> list[MemoryEntry]:
    """Scan memory directory and return entries sorted by bucket and name."""
    if not memory_dir.is_dir():
        return []

    entries: list[MemoryEntry] = []

    def process_file(file_path: Path, bucket: str, name: str, rel_path: str) -> None:
        if not file_path.is_file():
            return
        try:
            stat = file_path.stat()
            text = file_path.read_text(encoding="utf-8")
            data, _ = split_frontmatter(text)
            entry_name = str(data.get("name", name))
            description = str(data.get("description", ""))
            updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            entries.append(
                MemoryEntry(
                    bucket=bucket,
                    name=entry_name,
                    path=rel_path,
                    description=description,
                    bytes=stat.st_size,
                    updated=updated,
                )
            )
        except Exception:
            return

    # 1. Root bucket ("/") -> profile.md
    if bucket_filter is None or bucket_filter in ("/", "root", "profile"):
        profile_file = memory_dir / "profile.md"
        if profile_file.is_file():
            process_file(profile_file, "/", "profile", "profile.md")

    # 2. Subdirectory buckets
    for item in sorted(memory_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            b_name = item.name
            if bucket_filter is not None and bucket_filter not in (b_name,):
                continue
            for f in sorted(item.glob("*.md")):
                process_file(f, b_name, f.stem, f"{b_name}/{f.name}")

    return sorted(entries, key=lambda e: (e.bucket != "/", e.bucket, e.name))


def render_memory_context(memory_dir: Path) -> str:
    """Render the memory block for the system prompt.

    Contains full body of profile.md (if present) and index lines for other buckets.
    Returns empty string if memory directory has no content.
    """
    if not memory_dir.is_dir():
        return ""

    sections: list[str] = []

    # Profile section
    profile_path = memory_dir / "profile.md"
    if profile_path.is_file():
        try:
            text = profile_path.read_text(encoding="utf-8")
            _, body = split_frontmatter(text)
            body_clean = body.strip()
            if body_clean:
                sections.append(f'Profile (bucket: "/", name: "profile"):\n{body_clean}')
        except Exception:
            pass

    # Other buckets index
    index_lines: list[str] = []
    for item in sorted(memory_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            for f in sorted(item.glob("*.md")):
                try:
                    text = f.read_text(encoding="utf-8")
                    data, _ = split_frontmatter(text)
                    desc = data.get("description", "").strip()
                    desc_part = f" - {desc}" if desc else ""
                    index_lines.append(f'- bucket: "{item.name}", name: "{f.stem}"{desc_part}')
                except Exception:
                    continue

    if index_lines:
        sections.append("Indexed memory items:\n" + "\n".join(index_lines))

    if not sections:
        return ""

    content = "\n\n".join(sections)
    return f"<memory>\n{content}\n</memory>"

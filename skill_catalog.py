"""Skill catalog: scans workspace/skills/*/SKILL.md, extracting metadata for the system prompt."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from frontmatter import parse_frontmatter

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024


@dataclass(frozen=True)
class SkillMeta:
    name: str
    description: str
    location: str  # relative to workspace, e.g. skills/authoring-skills/SKILL.md


@dataclass
class Catalog:
    skills: list[SkillMeta] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)

    def metadata(self) -> list[dict]:
        return [asdict(skill) for skill in self.skills]


def scan_skills(workspace: Path) -> Catalog:
    """Scan workspace/skills/*/SKILL.md and return catalog."""
    catalog = Catalog()
    skills_dir = workspace / "skills"
    if not skills_dir.is_dir():
        return catalog

    seen: dict[str, str] = {}
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        location = skill_file.relative_to(workspace).as_posix()
        try:
            meta = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            catalog.diagnostics.append(f"Skipping {location}: {exc}")
            continue

        name = meta.get("name")
        description = meta.get("description")
        if not isinstance(name, str) or not name.strip():
            catalog.diagnostics.append(f"Skipping {location}: missing name")
            continue
        if not isinstance(description, str) or not description.strip():
            catalog.diagnostics.append(f"Skipping {location}: missing description")
            continue

        name, description = name.strip(), " ".join(description.split())
        if name in seen:
            catalog.diagnostics.append(
                f"Error: duplicate skill name '{name}' at {location}; keeping {seen[name]}, skipping later one."
            )
            continue

        if name != skill_file.parent.name:
            catalog.diagnostics.append(
                f"Warning {location}: name '{name}' differs from directory name '{skill_file.parent.name}'."
            )
        if len(name) > MAX_NAME_LENGTH:
            catalog.diagnostics.append(f"Warning {location}: name exceeds {MAX_NAME_LENGTH} chars.")
        if len(description) > MAX_DESCRIPTION_LENGTH:
            catalog.diagnostics.append(
                f"Warning {location}: description exceeds {MAX_DESCRIPTION_LENGTH} chars."
            )

        seen[name] = location
        catalog.skills.append(SkillMeta(name=name, description=description, location=location))

    return catalog


def render_catalog(catalog: Catalog) -> str:
    """Render <available_skills> XML block for system prompt."""
    if not catalog.skills:
        return ""
    items = "\n".join(
        "  <skill>\n"
        f"    <name>{escape(skill.name)}</name>\n"
        f"    <description>{escape(skill.description)}</description>\n"
        f"    <location>{escape(skill.location)}</location>\n"
        "  </skill>"
        for skill in catalog.skills
    )
    return f"<available_skills>\n{items}\n</available_skills>"

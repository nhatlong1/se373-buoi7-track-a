"""Tests for skill catalog scanning and prompt formatting."""

from __future__ import annotations

from pathlib import Path
from skill_catalog import render_catalog, scan_skills


def write_skill(workspace: Path, folder: str, text: str) -> None:
    path = workspace / "skills" / folder / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scan_skills_valid(tmp_path):
    write_skill(tmp_path, "good-skill", "---\nname: good-skill\ndescription: A good skill\n---\nBody")
    catalog = scan_skills(tmp_path)
    assert len(catalog.skills) == 1
    assert catalog.skills[0].name == "good-skill"
    assert catalog.skills[0].description == "A good skill"
    assert catalog.diagnostics == []

    block = render_catalog(catalog)
    assert "<available_skills>" in block
    assert "<name>good-skill</name>" in block


def test_scan_skills_invalid(tmp_path):
    write_skill(tmp_path, "bad-yaml", "---\nname: [bad\ndescription: x\n---\n")
    write_skill(tmp_path, "no-desc", "---\nname: no-desc\n---\nbody\n")
    catalog = scan_skills(tmp_path)
    assert len(catalog.skills) == 0
    assert len(catalog.diagnostics) == 2

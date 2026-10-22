"""Tests for the use_skill tool and skill catalog scanning."""

from __future__ import annotations

import json
from pathlib import Path

from tools.skills import _use_skill


def write_test_skill(workspace: Path, slug: str, content: str) -> None:
    skill_dir = workspace / "skills" / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_use_skill_success(agent_dirs):
    workspace = agent_dirs / "workspace"
    write_test_skill(
        workspace,
        "test-skill",
        "---\nname: test-skill\ndescription: A test skill\n---\n\n# Body of skill\nInstructions here.",
    )
    ref_dir = workspace / "skills" / "test-skill" / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)
    (ref_dir / "template.md").write_text("Reference content", encoding="utf-8")

    res = _use_skill(workspace, "test-skill")
    assert res["ok"] is True
    assert res["name"] == "test-skill"
    assert res["description"] == "A test skill"
    assert "Instructions here." in res["content"]
    assert "---" not in res["content"]
    assert res["references"] == ["references/template.md"]
    assert res["chars"] == len(res["content"])


def test_use_skill_not_found(agent_dirs):
    workspace = agent_dirs / "workspace"
    res = _use_skill(workspace, "non-existent")
    assert res["ok"] is False
    assert res["error"]["code"] == "SKILL_NOT_FOUND"


def test_use_skill_invalid_name(agent_dirs):
    workspace = agent_dirs / "workspace"
    for bad in ["../hack", "a/b", "a\\b", ""]:
        res = _use_skill(workspace, bad)
        assert res["ok"] is False
        assert res["error"]["code"] == "INVALID_SKILL_NAME"

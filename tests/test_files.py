"""Tests for workspace file operations: reading, writing, and listing."""

from __future__ import annotations

import json
from pathlib import Path

from tools.files import _list, _read, _write


def test_file_read_and_write(agent_dirs):
    workspace = agent_dirs / "workspace"

    # Write to output/
    w1 = _write(workspace, "output/result.txt", "hello output")
    assert w1["ok"] is True
    assert w1["status"] == "created"

    # Read back
    r1 = _read(workspace, "output/result.txt")
    assert r1["ok"] is True
    assert r1["content"] == "hello output"

    # List output
    l1 = _list(workspace, "output")
    assert l1["ok"] is True
    assert any(e["name"] == "result.txt" for e in l1["entries"])


def test_write_skills_allowed(agent_dirs):
    workspace = agent_dirs / "workspace"

    # Valid skill write
    valid_skill = "---\nname: my-skill\ndescription: A valid skill\n---\n\nBody"
    w1 = _write(workspace, "skills/my-skill/SKILL.md", valid_skill)
    assert w1["ok"] is True
    assert w1["status"] == "created"

    # Valid reference write
    w2 = _write(workspace, "skills/my-skill/references/doc.md", "Ref doc")
    assert w2["ok"] is True


def test_write_skills_invalid_frontmatter(agent_dirs):
    workspace = agent_dirs / "workspace"

    # Name mismatch
    bad_skill = "---\nname: other-name\ndescription: A valid skill\n---\n\nBody"
    w1 = _write(workspace, "skills/my-skill/SKILL.md", bad_skill)
    assert w1["ok"] is False
    assert w1["error"]["code"] == "INVALID_SKILL_FRONTMATTER"

    # Missing description
    bad_skill2 = "---\nname: my-skill\n---\n\nBody"
    w2 = _write(workspace, "skills/my-skill/SKILL.md", bad_skill2)
    assert w2["ok"] is False
    assert w2["error"]["code"] == "INVALID_SKILL_FRONTMATTER"


def test_write_outside_allowed_roots_rejected(agent_dirs):
    workspace = agent_dirs / "workspace"

    # Directly in workspace root
    assert _write(workspace, "root.txt", "x")["error"]["code"] == "PATH_NOT_WRITABLE"

    # Directly under skills/ without slug
    assert _write(workspace, "skills/test.md", "x")["error"]["code"] == "PATH_NOT_WRITABLE"

    # Traversal outside workspace
    assert _write(workspace, "../escape.txt", "x")["error"]["code"] == "PATH_OUTSIDE_WORKSPACE"

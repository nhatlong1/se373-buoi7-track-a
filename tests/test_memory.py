"""Tests for memory catalog and tools with the normalized (bucket, name) contract."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from memory_catalog import render_memory_context, scan_memory
from tools.memory import _delete_memory, _list_memory, _read_memory, _write_memory


def test_missing_memory_dir(tmp_path):
    missing_dir = tmp_path / "non_existent_memory"
    res = _list_memory(missing_dir)
    assert res["ok"] is True
    assert res["entries"] == []
    assert render_memory_context(missing_dir) == ""


def test_memory_lifecycle(agent_dirs):
    memory_dir = agent_dirs / "memory"

    # 1. Write profile to root bucket "/"
    w1 = _write_memory(
        memory_dir,
        "/",
        "profile",
        "Personal attributes",
        "- Location: Vietnam\n- Role: Researcher",
    )
    assert w1["ok"] is True
    assert w1["bucket"] == "/"
    assert w1["name"] == "profile"
    assert w1["status"] == "created"

    # 2. Read profile
    r1 = _read_memory(memory_dir, "/", "profile")
    assert r1["ok"] is True
    assert r1["bucket"] == "/"
    assert r1["name"] == "profile"
    assert r1["description"] == "Personal attributes"
    assert "- Location: Vietnam" in r1["content"]
    assert "---" not in r1["content"]

    # 3. Write topic
    w2 = _write_memory(
        memory_dir,
        "topics",
        "ai-preferences",
        "Preferred AI models",
        "- Primary model: qwen-3.8-flash",
    )
    assert w2["ok"] is True
    assert w2["bucket"] == "topics"
    assert w2["name"] == "ai-preferences"
    assert w2["status"] == "created"

    # 4. List memory
    l1 = _list_memory(memory_dir)
    assert l1["ok"] is True
    assert len(l1["entries"]) == 2
    items = [(e["bucket"], e["name"]) for e in l1["entries"]]
    assert ("/", "profile") in items
    assert ("topics", "ai-preferences") in items

    # 5. Render prompt context
    rendered = render_memory_context(memory_dir)
    assert "<memory>" in rendered
    assert 'Profile (bucket: "/", name: "profile"):\n- Location: Vietnam' in rendered
    assert 'bucket: "topics", name: "ai-preferences" - Preferred AI models' in rendered

    # 6. Delete memory
    d1 = _delete_memory(memory_dir, "topics", "ai-preferences")
    assert d1["ok"] is True
    assert d1["status"] == "deleted"

    # 7. Read deleted memory
    r2 = _read_memory(memory_dir, "topics", "ai-preferences")
    assert r2["ok"] is False
    assert r2["error"]["code"] == "MEMORY_NOT_FOUND"


def test_root_bucket_name_enforcement(agent_dirs):
    memory_dir = agent_dirs / "memory"

    # Reject non-profile name on "/"
    w1 = _write_memory(memory_dir, "/", "workflow", "desc", "- bullet")
    assert w1["ok"] is False
    assert w1["error"]["code"] == "INVALID_MEMORY_NAME"
    assert "Only 'profile' is permitted in the root ('/') bucket" in w1["error"]["message"]

    r1 = _read_memory(memory_dir, "/", "workflow")
    assert r1["ok"] is False
    assert r1["error"]["code"] == "INVALID_MEMORY_NAME"


def test_profile_name_prohibited_in_other_buckets(agent_dirs):
    memory_dir = agent_dirs / "memory"

    # Reject 'profile' in 'topics' or 'areas'
    for b in ["topics", "areas"]:
        w = _write_memory(memory_dir, b, "profile", "desc", "- bullet")
        assert w["ok"] is False
        assert w["error"]["code"] == "INVALID_MEMORY_NAME"
        assert "'profile' is reserved for the root ('/') bucket" in w["error"]["message"]

        r = _read_memory(memory_dir, b, "profile")
        assert r["ok"] is False
        assert r["error"]["code"] == "INVALID_MEMORY_NAME"


def test_memory_heading_rejected(agent_dirs):
    memory_dir = agent_dirs / "memory"
    res = _write_memory(
        memory_dir,
        "topics",
        "bad-note",
        "Invalid headings",
        "# Title heading\n- Bullet",
    )
    assert res["ok"] is False
    assert res["error"]["code"] == "INVALID_MEMORY_CONTENT"


def test_memory_oversize_rejected(agent_dirs):
    memory_dir = agent_dirs / "memory"
    oversize_content = "- bullet " + ("x" * 8100)
    res = _write_memory(
        memory_dir,
        "topics",
        "big-note",
        "Oversize",
        oversize_content,
    )
    assert res["ok"] is False
    assert res["error"]["code"] == "MEMORY_TOO_LARGE"


def test_memory_invalid_slugs_and_multi_layer(agent_dirs):
    memory_dir = agent_dirs / "memory"
    # Slashes and traversal in bucket or name
    assert _write_memory(memory_dir, "topics/sub", "slug", "desc", "- v")["error"]["code"] == "INVALID_MEMORY_BUCKET"
    assert _write_memory(memory_dir, "topics", "sub/slug", "desc", "- v")["error"]["code"] == "INVALID_MEMORY_NAME"
    assert _write_memory(memory_dir, "..", "slug", "desc", "- v")["error"]["code"] == "INVALID_MEMORY_BUCKET"
    assert _write_memory(memory_dir, "topics", "../escape", "desc", "- v")["error"]["code"] == "INVALID_MEMORY_NAME"
    assert _read_memory(memory_dir, "..", "slug")["error"]["code"] == "INVALID_MEMORY_BUCKET"
    assert _read_memory(memory_dir, "topics", "..")["error"]["code"] == "INVALID_MEMORY_NAME"

    # Bad characters
    assert _write_memory(memory_dir, "BAD_BUCKET", "slug", "desc", "- v")["error"]["code"] == "INVALID_MEMORY_BUCKET"
    assert _write_memory(memory_dir, "topics", "BAD_SLUG", "desc", "- v")["error"]["code"] == "INVALID_MEMORY_NAME"
    assert _write_memory(memory_dir, "topics", "has space", "desc", "- v")["error"]["code"] == "INVALID_MEMORY_NAME"


def test_memory_symlink_refused(agent_dirs):
    memory_dir = agent_dirs / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    secret = agent_dirs / "secret.txt"
    secret.write_text("secret")

    symlink_path = memory_dir / "profile.md"
    try:
        symlink_path.symlink_to(secret)
    except OSError:
        pytest.skip("Symlink creation not permitted in this test environment")

    res = _read_memory(memory_dir, "/", "profile")
    assert res["ok"] is False
    assert res["error"]["code"] == "MEMORY_SYMLINK"

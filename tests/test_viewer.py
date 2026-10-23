"""Unit tests for trace_replay and viewer modules."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure personal-agent is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import paths
from trace_replay import (
    generate_markdown_transcript,
    list_conversations,
    load_conversation,
)


def test_list_conversations():
    convs = list_conversations(paths.TRACES_DIR)
    assert len(convs) >= 3

    short_ids = [c.short_id for c in convs]
    assert "921cd3b8" in short_ids
    assert "bbee898c" in short_ids
    assert "64cf46a1" in short_ids

    c_921 = next(c for c in convs if c.short_id == "921cd3b8")
    assert c_921.turn_count == 3
    assert "vector database" in c_921.first_prompt.lower()
    assert c_921.total_events > 50

    c_bbee = next(c for c in convs if c.short_id == "bbee898c")
    assert c_bbee.turn_count == 2
    assert "what am i doing" in c_bbee.first_prompt.lower()


def test_load_conversation_921cd3b8():
    conv = load_conversation(paths.TRACES_DIR, "921cd3b8")
    assert conv.short_id == "921cd3b8"
    assert len(conv.turns) == 3

    # Turn 1 assertions
    t1 = conv.turns[0]
    assert t1.chat_turn == 1
    assert "vector database" in t1.user.lower()
    tool_names_t1 = [el["tool_name"] for el in t1.elements if el.get("type") == "tool"]
    assert "write_file" in tool_names_t1
    assert "memory_write" in tool_names_t1
    assert "qdrant" in t1.answer.lower()

    # Turn 2 assertions
    t2 = conv.turns[1]
    assert t2.chat_turn == 2
    assert "project description" in t2.user.lower()
    tool_names_t2 = [el["tool_name"] for el in t2.elements if el.get("type") == "tool"]
    assert "write_file" in tool_names_t2

    # Turn 3 assertions
    t3 = conv.turns[2]
    assert t3.chat_turn == 3
    assert "document writing" in t3.user.lower()

    # Snapshots check
    assert len(conv.snapshots) > 0
    assert any("authoring-skills" in s.get("system_prompt", "") for s in conv.snapshots)


def test_load_conversation_bbee898c():
    conv = load_conversation(paths.TRACES_DIR, "bbee898c")
    assert conv.short_id == "bbee898c"
    assert len(conv.turns) == 2

    # Turn 1
    t1 = conv.turns[0]
    assert "what am i doing" in t1.user.lower()
    assert "bizcare" in t1.answer.lower()

    # Turn 2
    t2 = conv.turns[1]
    assert "certain-acumen-k5cc4" in t2.user.lower()
    tool_names_t2 = [el["tool_name"] for el in t2.elements if el.get("type") == "tool"]
    assert "memory_write" in tool_names_t2
    assert "memory_delete" in tool_names_t2


def test_load_by_trace_file_path():
    files = list(paths.TRACES_DIR.glob("*921cd3b8*.jsonl"))
    assert files
    conv = load_conversation(paths.TRACES_DIR, files[0])
    assert conv.short_id == "921cd3b8"
    assert len(conv.turns) == 3


def test_generate_markdown_transcript():
    conv = load_conversation(paths.TRACES_DIR, "bbee898c")
    transcript = generate_markdown_transcript(conv)
    assert "# Conversation Transcript: `bbee898c`" in transcript
    assert "## Turn 1" in transcript
    assert "## Turn 2" in transcript
    assert "What am I doing?" in transcript
    assert "certain-acumen-k5cc4" in transcript

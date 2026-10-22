"""Tests for Observer: event recording, counters, and context inventory."""

from __future__ import annotations

import json
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from observer import Observer, serialize_message


def test_observer_inventory_with_use_skill():
    observer = Observer(conversation_id="conv-1")
    observer.start_turn("run-1")

    use_skill_output = {
        "ok": True,
        "name": "authoring-skills",
        "description": "Create skills",
        "content": "# Instructions",
        "references": ["references/skill-template.md"],
        "chars": 14,
    }
    tool_msg = ToolMessage(
        content=json.dumps(use_skill_output),
        name="use_skill",
        tool_call_id="call_skill_1",
    )

    observer.sync_messages([
        HumanMessage(content="Author a skill"),
        AIMessage(content="", tool_calls=[{"name": "use_skill", "args": {"name": "authoring-skills"}, "id": "call_skill_1"}]),
        tool_msg,
    ])

    inv = observer.inventory()
    assert len(inv["skills"]) == 1
    assert inv["skills"][0]["skill"] == "authoring-skills"
    assert inv["skills"][0]["chars"] == 14
    assert inv["skills"][0]["tool_call_id"] == "call_skill_1"


def test_observer_inventory_with_read_file():
    observer = Observer(conversation_id="conv-2")
    observer.start_turn("run-1")

    read_output = {"ok": True, "path": "output/notes.md", "content": "Note content"}
    tool_msg = ToolMessage(
        content=json.dumps(read_output),
        name="read_file",
        tool_call_id="call_read_1",
    )

    observer.sync_messages([
        HumanMessage(content="Read notes"),
        tool_msg,
    ])

    inv = observer.inventory()
    assert len(inv["resources"]) == 1
    assert inv["resources"][0]["path"] == "output/notes.md"

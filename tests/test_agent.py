"""Tests for agent construction, tool registration, and system prompt generation."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from agent import TOOLS, build_agent, system_prompt
from observer import Observer
from tests.conftest import ScriptedChatModel


def stream_events(agent, messages):
    events, new_messages = [], []
    for mode, chunk in agent.stream({"messages": messages}, stream_mode=["updates", "custom"]):
        if mode == "custom" and chunk.get("observer"):
            events.append(chunk)
        elif mode == "updates":
            for update in chunk.values():
                if isinstance(update, dict) and update.get("messages"):
                    new_messages.extend(update["messages"])
    return events, new_messages


def test_registered_tools():
    expected = [
        "list_files",
        "read_file",
        "write_file",
        "use_skill",
        "memory_list",
        "memory_read",
        "memory_write",
        "memory_delete",
    ]
    assert [t.name for t in TOOLS] == expected


def test_system_prompt_includes_memory_and_skills(agent_dirs):
    ws = agent_dirs / "workspace"
    mem = agent_dirs / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "profile.md").write_text(
        "---\nname: profile\ndescription: User profile\n---\n\n- Role: Engineer",
        encoding="utf-8",
    )

    prompt = system_prompt()
    assert "<memory>" in prompt
    assert "- Role: Engineer" in prompt
    assert "authoring-skills" in prompt


def test_agent_execution_with_scripted_model(agent_dirs):
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "list_files", "args": {"path": "."}, "id": "call_1"}],
            ),
            AIMessage(content="Here are the files."),
        ]
    )
    agent = build_agent(model)
    observer = Observer(conversation_id="conv-1")
    observer.start_turn("run-1")

    history = [HumanMessage(content="List the workspace")]
    events, new_messages = stream_events(agent, history)
    for ev in events:
        observer.record(ev["event"], ev["data"])

    assert any(e["event"] == "tool_started" and e["data"]["tool_name"] == "list_files" for e in events)
    assert any(e["event"] == "tool_finished" for e in events)
    assert len(model.received) == 2

"""Streamlit AppTest testing for personal-agent UI."""

from __future__ import annotations

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from streamlit.testing.v1 import AppTest

import agent
import paths
from tests.conftest import ScriptedChatModel

APP = str(paths.PROJECT_ROOT / "app.py")
TIMEOUT = 30


def make_app():
    return AppTest.from_file(APP, default_timeout=TIMEOUT)


def test_missing_config_disables_chat(agent_dirs, monkeypatch):
    monkeypatch.delenv("LLM_API_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_BASEURL", raising=False)
    at = make_app().run()
    assert not at.exception
    assert at.chat_input[0].disabled


def test_render_and_run_turn(configured_env, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(content="Hello! How can I assist you today?"),
        ]
    )
    monkeypatch.setattr(agent, "build_model", lambda settings: model)

    at = make_app().run()
    assert not at.exception
    at.chat_input[0].set_value("Hi there").run()
    assert not at.exception
    assert any("Hello! How can I assist you today?" in m.value for m in at.markdown)


def test_render_multi_step_turn_preserves_all_text(configured_env, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="I'll check your workspace.",
                tool_calls=[{"id": "call_1", "name": "list_files", "args": {"path": "."}}],
            ),
            AIMessage(
                content="Here is the table analysis.",
                tool_calls=[{"id": "call_2", "name": "list_files", "args": {"path": "output"}}],
            ),
            AIMessage(content="Both files are written and confirmed."),
        ]
    )
    monkeypatch.setattr(agent, "build_model", lambda settings: model)

    at = make_app().run()
    assert not at.exception
    at.chat_input[0].set_value("Analyze databases").run()
    assert not at.exception

    markdown_texts = " ".join(m.value for m in at.markdown)
    assert "I'll check your workspace." in markdown_texts
    assert "Here is the table analysis." in markdown_texts
    assert "Both files are written and confirmed." in markdown_texts


def test_multi_turn_persists_model_history_and_runs_tools(configured_env, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            # Turn 1
            AIMessage(content="First turn answer."),
            # Turn 2: uses tool write_file, then final answer
            AIMessage(
                content="Writing file now.",
                tool_calls=[
                    {
                        "id": "write_1",
                        "name": "write_file",
                        "args": {"path": "output/turn2.txt", "content": "Hello from Turn 2"},
                    }
                ],
            ),
            AIMessage(content="File created successfully."),
        ]
    )
    monkeypatch.setattr(agent, "build_model", lambda settings: model)

    at = make_app().run()
    assert not at.exception

    # Turn 1
    at.chat_input[0].set_value("Turn 1 prompt").run()
    assert not at.exception
    assert len(at.session_state.ui_history) == 1
    assert len(at.session_state.model_history) == 2
    assert at.session_state.model_history[0].content == "Turn 1 prompt"
    assert at.session_state.model_history[1].content == "First turn answer."

    # Turn 2
    at.chat_input[0].set_value("Turn 2 prompt").run()
    assert not at.exception
    assert len(at.session_state.ui_history) == 2

    # Check file was written to disk by tool during turn 2
    out_file = paths.WORKSPACE_DIR / "output" / "turn2.txt"
    assert out_file.is_file()
    assert out_file.read_text(encoding="utf-8") == "Hello from Turn 2"

    # Check model history has both turns
    history = at.session_state.model_history
    assert len(history) >= 5
    assert history[0].content == "Turn 1 prompt"
    assert history[2].content == "Turn 2 prompt"

    md_texts = [m.value for m in at.markdown]
    assert any("First turn answer." in t for t in md_texts)
    assert any("File created successfully." in t for t in md_texts)


def test_turn_failure_does_not_corrupt_history(configured_env, monkeypatch):
    class StepFailModel(BaseChatModel):
        call_count: int = 0

        @property
        def _llm_type(self) -> str:
            return "step-fail-mock"

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self.call_count += 1
            if self.call_count == 1:
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Turn 1 ok"))])
            raise RuntimeError("Turn 2 exploded")

    model = StepFailModel()
    monkeypatch.setattr(agent, "build_model", lambda settings: model)

    at = make_app().run()
    assert not at.exception

    # Turn 1
    at.chat_input[0].set_value("Turn 1 prompt").run()
    assert not at.exception
    assert len(at.session_state.model_history) == 2
    assert at.session_state.model_history[1].content == "Turn 1 ok"

    # Turn 2
    at.chat_input[0].set_value("Turn 2 prompt").run()
    assert not at.exception
    assert len(at.session_state.ui_history) == 2
    assert at.session_state.ui_history[1]["error"] is not None
    assert "Turn 2 exploded" in at.session_state.ui_history[1]["error"]

    # Model history is preserved as Turn 1 only
    assert len(at.session_state.model_history) == 2
    assert at.session_state.model_history[0].content == "Turn 1 prompt"
    assert at.session_state.model_history[1].content == "Turn 1 ok"

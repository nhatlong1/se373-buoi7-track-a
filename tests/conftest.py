"""Shared test fixtures for personal-agent."""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

import paths


class ScriptedChatModel(BaseChatModel):
    """Mock model: returns pre-scripted AIMessages in sequence and records inputs."""

    responses: list[AIMessage] = Field(default_factory=list)
    received: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted-mock"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedChatModel":
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.received.append(list(messages))
        if not self.responses:
            raise RuntimeError("ScriptedChatModel: ran out of pre-scripted responses")
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])


@pytest.fixture
def agent_dirs(tmp_path, monkeypatch):
    """Isolate workspace, memory, traces, and env to temporary path."""
    ws = tmp_path / "workspace"
    mem = tmp_path / "memory"
    traces = tmp_path / "traces"
    env_file = tmp_path / "test.env"

    monkeypatch.setattr(paths, "WORKSPACE_DIR", ws)
    monkeypatch.setattr(paths, "MEMORY_DIR", mem)
    monkeypatch.setattr(paths, "TRACES_DIR", traces)
    monkeypatch.setattr(paths, "ENV_PATH", env_file)

    paths.ensure_workspace(ws)
    return tmp_path


@pytest.fixture
def configured_env(agent_dirs, monkeypatch):
    monkeypatch.setenv("LLM_API_MODE", "OpenAI Chat Completions")
    monkeypatch.setenv("LLM_API_MODEL", "mock-model")
    monkeypatch.setenv("LLM_API_BASEURL", "http://mock-ai")
    monkeypatch.setenv("LLM_API_KEY", "none")
    monkeypatch.setenv("LLM_API_PATH", "/v1/chat/completions")
    return agent_dirs

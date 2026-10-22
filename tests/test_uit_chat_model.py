"""Tests for UITChatModel adaptation, message conversion, and tool binding."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from uit_chat_model import UITChatModel


def test_uit_chat_model_properties():
    model = UITChatModel(api_key="test-key")
    assert model._llm_type == "uit-vllm-chat-model"

    with pytest.raises(NotImplementedError, match="with_structured_output is not supported"):
        model.with_structured_output(None)


def test_bind_tools():
    @tool
    def sample_tool(param: str) -> str:
        """Sample tool description."""
        return param

    model = UITChatModel(api_key="test-key")
    bound = model.bind_tools([sample_tool])
    assert len(bound.bound_tools) == 1
    assert bound.bound_tools[0]["type"] == "function"
    assert bound.bound_tools[0]["function"]["name"] == "sample_tool"
    assert bound.bound_tools[0]["function"]["description"] == "Sample tool description."


def test_convert_messages_to_dicts_round_trip():
    model = UITChatModel(api_key="test-key")
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(
            content="Checking file",
            tool_calls=[{"name": "read_file", "args": {"path": "test.txt"}, "id": "call_123"}],
        ),
        ToolMessage(content="File content", tool_call_id="call_123", name="read_file"),
    ]

    dicts = model._convert_messages_to_dicts(messages)
    assert len(dicts) == 3

    # Human message
    assert dicts[0] == {"role": "user", "content": "Hello"}

    # AIMessage tool call inline reconstruction
    assert dicts[1]["role"] == "assistant"
    assert "<tool_call>" in dicts[1]["content"]
    assert "read_file" in dicts[1]["content"]

    # ToolMessage downgraded to user message
    assert dicts[2]["role"] == "user"
    assert "[Tool Result for call_123]: File content" in dicts[2]["content"]


def test_generate_against_mock_client(monkeypatch):
    model = UITChatModel(
        base_url="https://llm.uit.edu.vn/gemma/v1",
        api_key="test-key",
        model_name="gemma-4-26b",
    )

    fake_response = MagicMock()
    fake_choice = MagicMock()
    fake_choice.message.content = (
        'Let me check.\n<tool_call>{"name": "list_files", "arguments": {"path": "."}}</tool_call>'
    )
    fake_response.choices = [fake_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response
    monkeypatch.setattr(model, "_get_client", lambda: mock_client)

    result = model.invoke([HumanMessage(content="List files")])
    assert isinstance(result, AIMessage)
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "list_files"
    assert result.tool_calls[0]["args"] == {"path": "."}
    assert "<tool_call>" not in result.content
    assert "Let me check." in result.content

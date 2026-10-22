"""Tests for UITToolMiddleware request preparation and parser branches."""

from __future__ import annotations

import json
from uit_middleware import UITToolMiddleware


def test_is_uit_endpoint():
    assert UITToolMiddleware.is_uit_endpoint("https://llm.uit.edu.vn/gemma/v1") is True
    assert UITToolMiddleware.is_uit_endpoint("http://ai/v1") is False


def test_prepare_request_non_uit():
    payload = {
        "model": "qwen",
        "messages": [{"role": "user", "content": "hello"}],
        "tools": [{"type": "function", "function": {"name": "test"}}],
    }
    # Identity when endpoint is not UIT
    result = UITToolMiddleware.prepare_request(payload, "http://ai/v1")
    assert result == payload
    assert "tools" in result


def test_prepare_request_uit():
    payload = {
        "model": "gemma",
        "messages": [{"role": "user", "content": "hello"}],
        "tools": [{"type": "function", "function": {"name": "test_tool", "description": "A tool"}}],
        "tool_choice": "auto",
    }
    result = UITToolMiddleware.prepare_request(payload, "https://llm.uit.edu.vn/gemma/v1")
    assert "tools" not in result
    assert "tool_choice" not in result
    assert result["messages"][0]["role"] == "system"
    assert "test_tool" in result["messages"][0]["content"]


def test_parse_tool_calls_json_tag():
    text = (
        "Here is the call:\n"
        "<tool_call>\n"
        '{"name": "read_file", "arguments": {"path": "test.txt"}}\n'
        "</tool_call>\nDone!"
    )
    calls, cleaned = UITToolMiddleware.parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "read_file"
    args = json.loads(calls[0]["function"]["arguments"])
    assert args == {"path": "test.txt"}
    assert "Done!" in cleaned
    assert "<tool_call>" not in cleaned


def test_parse_tool_calls_qwen_xml():
    text = (
        "<tool_call>\n"
        "<function=write_file>\n"
        "<parameter=path>output/test.txt</parameter>\n"
        "<parameter=content>hello world</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )
    calls, cleaned = UITToolMiddleware.parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "write_file"
    args = json.loads(calls[0]["function"]["arguments"])
    assert args["path"] == "output/test.txt"
    assert args["content"] == "hello world"


def test_parse_tool_calls_gemma_marker():
    text = 'Thinking... call:memory_write{path: "profile.md", description: "User facts", content: "- Location: SG"}'
    calls, cleaned = UITToolMiddleware.parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "memory_write"
    args = json.loads(calls[0]["function"]["arguments"])
    assert args["path"] == "profile.md"
    assert "Thinking..." in cleaned
    assert "call:memory_write" not in cleaned


def test_parse_tool_calls_whole_message_json():
    text = '{"name": "list_files", "arguments": {"path": "."}}'
    calls, cleaned = UITToolMiddleware.parse_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "list_files"
    assert cleaned is None


def test_process_response():
    raw_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '<tool_call>{"name": "f", "arguments": {}}</tool_call>',
                },
                "finish_reason": "stop",
            }
        ]
    }
    processed = UITToolMiddleware.process_response(raw_response)
    msg = processed["choices"][0]["message"]
    assert "tool_calls" in msg
    assert msg["tool_calls"][0]["function"]["name"] == "f"
    assert processed["choices"][0]["finish_reason"] == "tool_calls"

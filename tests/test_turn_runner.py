"""Unit tests for TurnRun background worker."""

from __future__ import annotations

import json
import threading
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from agent import build_agent
from observer import Observer
from trace import TraceWriter
import paths
from turn_runner import TurnRun, compact_event


class StreamingToolChatModel(BaseChatModel):
    """Mock model that streams tokens, then requests a tool, then streams final answer."""

    call_count: int = 0

    @property
    def _llm_type(self) -> str:
        return "streaming-tool-mock"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "StreamingToolChatModel":
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise NotImplementedError

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            chunk1 = AIMessageChunk(content="Thinking about listing files...")
            if run_manager:
                run_manager.on_llm_new_token(chunk1.content)
            yield ChatGenerationChunk(message=chunk1)

            chunk2 = AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {
                        "name": "list_files",
                        "args": '{"path": "."}',
                        "id": "call_stream_1",
                        "index": 0,
                        "type": "tool_call_chunk",
                    }
                ],
            )
            yield ChatGenerationChunk(message=chunk2)
        else:
            chunk = AIMessageChunk(content="Listing finished successfully.")
            if run_manager:
                run_manager.on_llm_new_token(chunk.content)
            yield ChatGenerationChunk(message=chunk)


class FailingChatModel(BaseChatModel):
    """Mock model that raises an error during generation."""

    @property
    def _llm_type(self) -> str:
        return "failing-mock"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FailingChatModel":
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise RuntimeError("Simulated model outage")


def test_compact_event():
    event = {
        "type": "model_request",
        "snapshot": {"message_count": 5, "tools": ["t1", "t2"]},
        "other": 123,
    }
    compacted = compact_event(event)
    assert "snapshot" not in compacted
    assert compacted["message_count"] == 5
    assert compacted["tool_count"] == 2
    assert compacted["other"] == 123


def test_compact_event_missing_snapshot():
    event = {"type": "model_request"}
    compacted = compact_event(event)
    assert compacted["message_count"] == 0
    assert compacted["tool_count"] == 0


def test_turn_runner_streaming_no_text_duplication(agent_dirs):
    observer = Observer("test_conv_stream")
    model = StreamingToolChatModel()
    writer_factory = lambda r, t: TraceWriter(paths.TRACES_DIR, "test", observer.conversation_id, r, t)

    run = TurnRun(
        text="List files",
        history=[],
        observer=observer,
        writer_factory=writer_factory,
        capabilities={"tools": ["list_files"], "skills": []},
        recursion_limit=25,
    )

    run.start(lambda: build_agent(model))
    finished = run.join(timeout=10.0)

    assert finished is True
    assert run.succeeded is True
    assert run.turn["error"] is None

    # Check elements: must have exactly 1 thinking text, 1 tool, 1 final text (no duplicates)
    types = [el.get("type") for el in run.elements]
    assert types == ["text", "tool", "text"]

    assert run.elements[0]["content"] == "Thinking about listing files..."
    assert run.elements[0]["streaming"] is False

    assert run.elements[1]["type"] == "tool"
    assert run.elements[1]["tool_name"] == "list_files"
    assert run.elements[1]["status"] == "success"

    assert run.elements[2]["content"] == "Listing finished successfully."
    assert run.elements[2]["streaming"] is False

    assert "Thinking about listing files..." in run.turn["answer"]
    assert "Listing finished successfully." in run.turn["answer"]

    # Verify JSONL trace file persisted on disk
    trace_lines = [
        json.loads(line)
        for line in run.writer.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    completed_ev = next(e for e in trace_lines if e["type"] == "run_completed")
    assert completed_ev["answer"] == run.turn["answer"]
    assert completed_ev["aborted"] is False

    model_responses = [e for e in trace_lines if e["type"] == "model_response"]
    assert len(model_responses) >= 2
    assert model_responses[-1]["message"]["content"] == "Listing finished successfully."


def test_turn_runner_failure_rolls_back_observer(agent_dirs):
    observer = Observer("test_conv_fail")
    initial_msg = HumanMessage(content="Prior message")
    initial_history = [initial_msg]
    observer.sync_messages(initial_history)
    assert len(observer.messages) == 1

    model = FailingChatModel()
    writer_factory = lambda r, t: TraceWriter(paths.TRACES_DIR, "test", observer.conversation_id, r, t)

    run = TurnRun(
        text="Do something that fails",
        history=initial_history,
        observer=observer,
        writer_factory=writer_factory,
        capabilities={"tools": ["list_files"], "skills": []},
        recursion_limit=25,
    )

    run.start(lambda: build_agent(model))
    finished = run.join(timeout=10.0)

    assert finished is True
    assert run.succeeded is False
    assert run.turn["error"] is not None
    assert "Simulated model outage" in run.turn["error"]

    # Verify observer history was cleanly rolled back to initial_history
    assert observer.history_rolled_back is True
    assert len(observer.messages) == 1
    assert observer.messages[0]["content"] == "Prior message"


def test_turn_runner_handles_ai_message_with_none_tool_calls(agent_dirs):
    class NoneToolCallModel(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "none-tool-call-mock"

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            msg = AIMessage(content="Simple answer without tools")
            msg.tool_calls = None
            return ChatResult(generations=[ChatGeneration(message=msg)])

    observer = Observer("test_conv_none_tools")
    writer_factory = lambda r, t: TraceWriter(paths.TRACES_DIR, "test", observer.conversation_id, r, t)
    run = TurnRun(
        text="Hello",
        history=[],
        observer=observer,
        writer_factory=writer_factory,
        capabilities={"tools": ["list_files"], "skills": []},
        recursion_limit=25,
    )
    run.start(lambda: build_agent(NoneToolCallModel()))
    finished = run.join(timeout=10.0)
    assert finished is True
    assert run.succeeded is True
    assert len(run.elements) == 1
    assert run.elements[0]["content"] == "Simple answer without tools"


def test_turn_runner_abort(agent_dirs):
    stop_event = threading.Event()

    class InfiniteStreamModel(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "infinite-stream-mock"

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise NotImplementedError

        def _stream(self, messages, stop=None, run_manager=None, **kwargs):
            import time
            for _ in range(50):
                if stop_event.is_set():
                    break
                time.sleep(0.05)
                yield ChatGenerationChunk(message=AIMessageChunk(content="more text..."))

    observer = Observer("test_conv_abort")
    writer_factory = lambda r, t: TraceWriter(paths.TRACES_DIR, "test", observer.conversation_id, r, t)
    run = TurnRun(
        text="Run forever",
        history=[],
        observer=observer,
        writer_factory=writer_factory,
        capabilities={"tools": ["list_files"], "skills": []},
        recursion_limit=25,
    )
    run.start(lambda: build_agent(InfiniteStreamModel()))
    import time
    time.sleep(0.2)
    run.abort()
    stop_event.set()
    finished = run.join(timeout=5.0)
    assert finished is True
    assert run.succeeded is False


def test_observer_snapshot(agent_dirs):
    observer = Observer("test_conv_snap")
    observer.start_turn("r1")
    observer.record("user_submitted", {"text": "hi", "tools": [], "skills": []})
    snap = observer.snapshot()
    assert snap.conversation_id == "test_conv_snap"
    assert snap.chat_turn == 1
    assert len(snap.events) == 1
    assert snap.counters()["Turn"] == 1

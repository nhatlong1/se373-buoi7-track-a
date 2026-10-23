"""Background execution of one agent turn, decoupled from the Streamlit script thread.

Streamlit delivers every rerun/stop request (widget interaction, chat submission, frontend
reconnect) to the script thread as a ``BaseException`` at its next ``st.*`` call. With
``runner.fastReruns`` enabled (the default) the old script run is stopped and a new one
starts immediately. When the agent stream runs inside the script thread, that exception
abandons the LangGraph stream mid-turn: pending tool calls never execute, no terminal trace
event is written, and the turn is never committed to model history.

``TurnRun`` runs the stream in a worker thread and only mutates plain Python objects under
``lock``. The script thread polls and renders; interrupting the script thread no longer
affects the turn.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from observer import Observer
from trace import TraceWriter


def compact_event(event: dict) -> dict:
    item = {k: v for k, v in event.items() if k not in ("snapshot", "message")}
    if event.get("type") == "model_request":
        snap = event.get("snapshot") or {}
        item["message_count"] = snap.get("message_count", 0)
        item["tool_count"] = len(snap.get("tools", []))
    return item


class TurnRun:
    """One chat turn executed by a background thread.

    Readers must hold ``lock`` while reading ``elements``, ``turn``, ``working`` or the
    observer. ``version`` increments after every state mutation so pollers can skip
    redundant renders.
    """

    def __init__(
        self,
        text: str,
        history: list[BaseMessage],
        observer: Observer,
        writer_factory: Callable[[str, int], TraceWriter],
        capabilities: dict,
        recursion_limit: int,
        on_exception: Callable[[BaseException], None] | None = None,
    ) -> None:
        self.lock = threading.RLock()
        self.done = threading.Event()
        self.abort_requested = threading.Event()
        self.version = 0
        self.succeeded = False
        self.observer = observer
        self.recursion_limit = recursion_limit
        self.on_exception = on_exception
        self.run_id = uuid.uuid4().hex
        self.initial_history = list(history)
        self._current_text_el: dict[str, Any] | None = None
        observer.start_turn(self.run_id)
        self.writer = writer_factory(self.run_id, observer.chat_turn)
        self.elements: list[dict] = []
        self.turn: dict[str, Any] = {
            "run_id": self.run_id,
            "chat_turn": observer.chat_turn,
            "user": text,
            "elements": self.elements,
            "answer": "",
            "error": None,
            "events": [],
        }
        self.working: list[BaseMessage] = list(history) + [HumanMessage(content=text)]
        self._agent = None
        self._thread: threading.Thread | None = None
        with self.lock:
            self._emit(
                "user_submitted",
                {"text": text, "tools": capabilities["tools"], "skills": capabilities["skills"]},
            )
            observer.sync_messages(self.working)

    # ------------------------------------------------------------ lifecycle

    def start(self, agent_factory: Callable[[], Any]) -> None:
        """Build the agent in the caller's thread, then stream it in a worker thread."""
        try:
            self._agent = agent_factory()
        except Exception as exc:
            self._fail(exc)
            self.done.set()
            return
        self._thread = threading.Thread(
            target=self._run, name=f"agent-turn-{self.run_id[:8]}", daemon=True
        )
        self._thread.start()

    def abort(self) -> None:
        """Signal the worker to stop processing new stream chunks."""
        self.abort_requested.set()

    def join(self, timeout: float | None = None) -> bool:
        return self.done.wait(timeout)

    # ------------------------------------------------------------ worker

    def _emit(self, event_type: str, data: dict | None = None) -> None:
        event = self.observer.record(event_type, data)
        try:
            self.writer.write(event)
        except Exception:
            pass
        self.turn["events"].append(compact_event(event))
        self.version += 1

    def _append_text(self, piece: str) -> None:
        if self._current_text_el is None:
            el = {"type": "text", "content": piece, "streaming": True}
            self.elements.append(el)
            self._current_text_el = el
        else:
            self._current_text_el["content"] += piece
            self._current_text_el["streaming"] = True
        self.version += 1

    def _run(self) -> None:
        try:
            stream = self._agent.stream(
                {"messages": self.working},
                config={"recursion_limit": self.recursion_limit},
                stream_mode=["messages", "updates", "custom"],
            )
            for mode, chunk in stream:
                if self.abort_requested.is_set():
                    break
                with self.lock:
                    self._handle(mode, chunk)
            with self.lock:
                for el in self.elements:
                    el["streaming"] = False
                self._current_text_el = None
                text_parts = [
                    el["content"].strip()
                    for el in self.elements
                    if el.get("type") == "text" and el.get("content", "").strip()
                ]
                self.turn["answer"] = "\n\n".join(text_parts)
                self.observer.sync_messages(self.working)
                self._emit(
                    "run_completed",
                    {
                        "elements_count": len(self.elements),
                        "answer_chars": len(self.turn["answer"]),
                        "answer": self.turn["answer"],
                        "aborted": self.abort_requested.is_set(),
                    },
                )
                self.succeeded = not self.abort_requested.is_set()
        except BaseException as exc:  # record every termination cause, including SystemExit
            self._fail(exc)
            if not isinstance(exc, Exception):
                raise
        finally:
            self.done.set()

    def _fail(self, exc: BaseException) -> None:
        if self.on_exception is not None:
            try:
                self.on_exception(exc)
            except Exception:
                pass
        with self.lock:
            error = f"{type(exc).__name__}: {exc}"
            for el in self.elements:
                el["streaming"] = False
            self._current_text_el = None
            self.turn["error"] = error
            self.elements.append({"type": "error", "message": error})
            self._emit("run_failed", {"error": error})
            self.observer.history_rolled_back = True
            self.observer.sync_messages(self.initial_history)

    def _handle(self, mode: str, chunk: Any) -> None:
        if mode == "messages":
            msg_chunk, metadata = chunk
            if metadata.get("langgraph_node") not in ("agent", "model"):
                return
            content = getattr(msg_chunk, "content", None)
            if isinstance(content, str):
                piece = content
            elif isinstance(content, list):
                piece = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            else:
                piece = ""
            if piece:
                self._append_text(piece)

        elif mode == "custom" and isinstance(chunk, dict) and chunk.get("observer"):
            event_name = chunk.get("event")
            data = chunk.get("data", {})
            self._emit(event_name, data)
            if event_name == "tool_started":
                if self._current_text_el is not None:
                    self._current_text_el["streaming"] = False
                self.elements.append(
                    {
                        "type": "tool",
                        "tool_call_id": data.get("tool_call_id"),
                        "tool_name": data.get("tool_name"),
                        "args": data.get("arguments", {}),
                        "status": "running",
                        "result": None,
                        "elapsed_ms": None,
                    }
                )
            elif event_name == "tool_finished":
                call_id = data.get("tool_call_id")
                for el in reversed(self.elements):
                    if el.get("type") == "tool" and el.get("tool_call_id") == call_id:
                        el["status"] = data.get("status", "success")
                        el["result"] = data.get("result")
                        el["elapsed_ms"] = data.get("elapsed_ms")
                        break

        elif mode == "updates" and isinstance(chunk, dict):
            changed = False
            for update in chunk.values():
                if not (isinstance(update, dict) and update.get("messages")):
                    continue
                new_msgs = update["messages"]
                if not isinstance(new_msgs, list):
                    new_msgs = [new_msgs]
                self.working.extend(new_msgs)
                changed = True
                for m in new_msgs:
                    if not isinstance(m, AIMessage):
                        continue
                    txt = getattr(m, "text", None)
                    if txt is None:
                        txt = getattr(m, "content", "")
                    clean_txt = txt.strip() if isinstance(txt, str) else ""
                    if self._current_text_el is not None:
                        if clean_txt:
                            self._current_text_el["content"] = clean_txt
                            self._current_text_el["streaming"] = False
                        else:
                            if self._current_text_el in self.elements:
                                self.elements.remove(self._current_text_el)
                        self._current_text_el = None
                    elif clean_txt:
                        tool_call_ids = {c.get("id") for c in (m.tool_calls or [])}
                        insert_idx = next(
                            (
                                i
                                for i, el in enumerate(self.elements)
                                if el.get("type") == "tool" and el.get("tool_call_id") in tool_call_ids
                            ),
                            len(self.elements),
                        )
                        self.elements.insert(
                            insert_idx,
                            {"type": "text", "content": clean_txt, "streaming": False},
                        )
            if changed:
                self.observer.sync_messages(self.working)
                self.version += 1

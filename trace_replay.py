"""Trace replay and conversation reconstruction from on-disk JSONL trace logs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ConversationMetadata:
    conversation_id: str
    short_id: str
    started_at: str
    turn_count: int
    model_name: str | None
    first_prompt: str
    files: list[Path] = field(default_factory=list)
    total_events: int = 0


@dataclass
class ReplayedTurn:
    run_id: str
    chat_turn: int
    user: str
    elements: list[dict[str, Any]]
    answer: str
    error: str | None
    events: list[dict[str, Any]]
    snapshots: list[dict[str, Any]]


@dataclass
class ReplayedConversation:
    conversation_id: str
    short_id: str
    metadata: ConversationMetadata
    turns: list[ReplayedTurn]
    ui_history: list[dict[str, Any]]
    snapshots: list[dict[str, Any]]
    events: list[dict[str, Any]]


def parse_tool_content(content: Any) -> Any:
    """Parse JSON string tool outputs for clean inspection."""
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return content
    return content


def list_conversations(traces_dir: Path) -> list[ConversationMetadata]:
    """Scan traces directory and aggregate trace files by conversation_id."""
    if not traces_dir.is_dir():
        return []

    # Map short_id -> list of (turn_num, timestamp_str, Path)
    grouped: dict[str, list[tuple[int, str, Path]]] = {}
    for p in sorted(traces_dir.glob("*.jsonl")):
        m = re.search(r"^([0-9]{8}-[0-9]{6})_([a-zA-Z0-9]+)_turn(\d+)_", p.name)
        if not m:
            continue
        stamp = m.group(1)
        short_id = m.group(2)
        turn_num = int(m.group(3))
        grouped.setdefault(short_id, []).append((turn_num, stamp, p))

    conversations: list[ConversationMetadata] = []
    for short_id, file_tuples in grouped.items():
        file_tuples.sort(key=lambda x: (x[0], x[1]))
        files = [p for _, _, p in file_tuples]
        first_file = files[0]

        started_at = ""
        first_prompt = ""
        model_name = None
        full_conv_id = short_id
        total_events = 0

        # Scan files for metadata and event counts
        for f in files:
            try:
                with f.open("r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        total_events += 1
                        ev = json.loads(line)
                        if not started_at and ev.get("timestamp"):
                            started_at = ev["timestamp"]
                        if ev.get("conversation_id"):
                            full_conv_id = ev["conversation_id"]
                        if ev.get("type") == "user_submitted" and not first_prompt:
                            first_prompt = ev.get("text", "")
                        if ev.get("type") == "model_request" and not model_name:
                            model_name = ev.get("snapshot", {}).get("model_name")
            except Exception:
                pass

        conversations.append(
            ConversationMetadata(
                conversation_id=full_conv_id,
                short_id=short_id,
                started_at=started_at,
                turn_count=len(files),
                model_name=model_name,
                first_prompt=first_prompt,
                files=files,
                total_events=total_events,
            )
        )

    conversations.sort(key=lambda c: c.started_at or "", reverse=True)
    return conversations


def load_conversation(traces_dir: Path, identifier: str | Path) -> ReplayedConversation:
    """Reconstruct a conversation by conversation_id, short_id, or trace file path."""
    target_meta: ConversationMetadata | None = None
    all_convs = list_conversations(traces_dir)

    # Check if identifier is a Path or filename
    id_str = str(identifier).strip()
    if "/" in id_str or "\\" in id_str or id_str.endswith(".jsonl"):
        p = Path(id_str)
        m = re.search(r"_([a-zA-Z0-9]+)_turn\d+_", p.name)
        if m:
            short_id = m.group(1)
            target_meta = next((c for c in all_convs if c.short_id == short_id), None)

    if target_meta is None:
        target_meta = next(
            (c for c in all_convs if c.conversation_id == id_str or c.short_id == id_str),
            None,
        )

    if target_meta is None:
        raise FileNotFoundError(f"Conversation '{identifier}' not found in {traces_dir}")

    # Read events from all turn files
    parsed_turns_raw: list[dict[str, Any]] = []
    for turn_file in target_meta.files:
        events = []
        with turn_file.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
        parsed_turns_raw.append({"file": turn_file, "events": events})

    replayed_turns: list[ReplayedTurn] = []
    all_snapshots: list[dict[str, Any]] = []
    all_events: list[dict[str, Any]] = []
    ui_history: list[dict[str, Any]] = []

    for idx, turn_data in enumerate(parsed_turns_raw):
        events = turn_data["events"]
        user_text = ""
        turn_elements: list[dict[str, Any]] = []
        tool_dict: dict[str, dict[str, Any]] = {}
        turn_error = None
        turn_num = idx + 1
        run_id = ""
        turn_snapshots: list[dict[str, Any]] = []

        for ev in events:
            all_events.append(ev)
            ev_type = ev.get("type")
            if not run_id and ev.get("run_id"):
                run_id = ev["run_id"]
            if ev.get("chat_turn"):
                turn_num = ev["chat_turn"]

            if ev_type == "user_submitted":
                user_text = ev.get("text", "")
            elif ev_type == "model_request":
                snap = ev.get("snapshot")
                if snap:
                    turn_snapshots.append(snap)
                    all_snapshots.append(snap)
            elif ev_type == "tool_started":
                call_id = ev.get("tool_call_id")
                tool_item = {
                    "type": "tool",
                    "tool_call_id": call_id,
                    "tool_name": ev.get("tool_name"),
                    "args": ev.get("arguments", {}),
                    "status": "running",
                    "result": None,
                    "elapsed_ms": None,
                }
                tool_dict[call_id] = tool_item
                turn_elements.append(tool_item)
            elif ev_type == "tool_finished":
                call_id = ev.get("tool_call_id")
                if call_id in tool_dict:
                    tool_dict[call_id]["status"] = ev.get("status", "success")
                    res = ev.get("result")
                    tool_dict[call_id]["result"] = parse_tool_content(res)
                    tool_dict[call_id]["elapsed_ms"] = ev.get("elapsed_ms")
            elif ev_type == "run_failed":
                turn_error = ev.get("error", "Turn failed")

        # Recover assistant answer:
        # Tier 1: Look at the next turn's first model_request snapshot
        assistant_answer = ""
        if idx + 1 < len(parsed_turns_raw):
            next_events = parsed_turns_raw[idx + 1]["events"]
            for nev in next_events:
                if nev.get("type") == "model_request":
                    nmsgs = nev.get("snapshot", {}).get("messages", [])
                    # The message directly preceding the new turn's human message is the previous turn's final AI response
                    for nm in reversed(nmsgs):
                        if nm.get("role") == "assistant" and nm.get("content"):
                            assistant_answer = nm.get("content")
                            break
                    break

        # Tier 2: Check if run_completed or any event in this turn had answer text
        if not assistant_answer:
            for ev in reversed(events):
                if ev.get("answer"):
                    assistant_answer = ev.get("answer")
                    break

        # Tier 3: Check assistant messages in this turn's snapshots (strictly after this turn's user message)
        if not assistant_answer and turn_snapshots:
            last_snap_msgs = turn_snapshots[-1].get("messages", [])
            last_user_idx = -1
            for m_i, m in enumerate(last_snap_msgs):
                if m.get("role") == "user":
                    last_user_idx = m_i
            if last_user_idx != -1:
                for sm in reversed(last_snap_msgs[last_user_idx + 1 :]):
                    if sm.get("role") == "assistant" and sm.get("content"):
                        assistant_answer = sm.get("content")
                        break

        if assistant_answer and not any(el.get("type") == "text" for el in turn_elements):
            turn_elements.append({"type": "text", "content": assistant_answer, "streaming": False})

        replayed_turn = ReplayedTurn(
            run_id=run_id,
            chat_turn=turn_num,
            user=user_text,
            elements=turn_elements,
            answer=assistant_answer,
            error=turn_error,
            events=events,
            snapshots=turn_snapshots,
        )
        replayed_turns.append(replayed_turn)

        ui_turn = {
            "run_id": run_id,
            "chat_turn": turn_num,
            "user": user_text,
            "elements": turn_elements,
            "answer": assistant_answer,
            "error": turn_error,
            "events": events,
        }
        ui_history.append(ui_turn)

    return ReplayedConversation(
        conversation_id=target_meta.conversation_id,
        short_id=target_meta.short_id,
        metadata=target_meta,
        turns=replayed_turns,
        ui_history=ui_history,
        snapshots=all_snapshots,
        events=all_events,
    )


def generate_markdown_transcript(conv: ReplayedConversation) -> str:
    """Format conversation into a clean Markdown document."""
    meta = conv.metadata
    lines = [
        f"# Conversation Transcript: `{meta.short_id}`",
        "",
        f"- **Full Conversation ID**: `{meta.conversation_id}`",
        f"- **Started At**: {meta.started_at}",
        f"- **Model**: `{meta.model_name or 'unknown'}`",
        f"- **Turns**: {meta.turn_count}",
        f"- **Total Events**: {len(conv.events)}",
        f"- **Context Snapshots Captured**: {len(conv.snapshots)}",
        "",
        "---",
        "",
    ]

    for turn in conv.turns:
        lines.append(f"## Turn {turn.chat_turn}")
        lines.append("")
        lines.append(f"**Run ID**: `{turn.run_id}`")
        lines.append("")
        lines.append("### User")
        lines.append("")
        lines.append(turn.user or "*(empty)*")
        lines.append("")

        tool_calls = [el for el in turn.elements if el.get("type") == "tool"]
        if tool_calls:
            lines.append(f"### Tool Executions ({len(tool_calls)})")
            lines.append("")
            for tc in tool_calls:
                name = tc.get("tool_name", "unknown")
                status = tc.get("status", "unknown")
                elapsed = f" ({tc.get('elapsed_ms')} ms)" if tc.get("elapsed_ms") is not None else ""
                lines.append(f"#### `{name}` [{status}]{elapsed}")
                lines.append("")
                lines.append("**Arguments**:")
                lines.append("```json")
                lines.append(json.dumps(tc.get("args", {}), ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")
                lines.append("**Result**:")
                res = tc.get("result")
                if isinstance(res, (dict, list)):
                    lines.append("```json")
                    lines.append(json.dumps(res, ensure_ascii=False, indent=2))
                    lines.append("```")
                else:
                    lines.append("```text")
                    lines.append(str(res))
                    lines.append("```")
                lines.append("")

        lines.append("### Assistant")
        lines.append("")
        if turn.answer:
            lines.append(turn.answer)
        elif turn.error:
            lines.append(f"**Error**: {turn.error}")
        else:
            lines.append("*(Terminal turn: final answer was streamed to UI and omitted from raw trace)*")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)

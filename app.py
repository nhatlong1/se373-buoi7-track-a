"""Streamlit chat UI: Chat pane on the left, State & Context pane on the right."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import nullcontext

import streamlit as st

from agent import TOOLS, build_agent, build_model, capabilities, system_prompt
from config import APP_TITLE, CAPABILITY_TEXT, PROJECT_NAME, RECURSION_LIMIT, load_settings
from memory_catalog import scan_memory
from observer import (
    STATUS_DONE,
    STATUS_ERROR,
    STATUS_MODEL,
    STATUS_TOOL,
    Observer,
    message_text,
    serialize_message,
    tool_schema,
)
import paths
from providers import get_active_provider_info
from trace import TraceWriter, log_exception
from turn_runner import TurnRun

PANEL_HEIGHT = 600
POLL_SECONDS = 0.2
PANEL_REFRESH_SECONDS = 1.0

PAGE_CSS = """
<style>
[data-testid="stAppScrollToBottomContainer"] { overflow: hidden; }
[data-testid="stMainBlockContainer"] { padding-top: 3rem; padding-bottom: 0; }
[data-testid="stBottomBlockContainer"] { padding-top: 0.5rem; padding-bottom: 1rem; }
[data-testid="stLayoutWrapper"]:has(> .st-key-chat_panel),
[data-testid="stLayoutWrapper"]:has(> .st-key-state_panel) {
    height: calc(100dvh - 15.5rem) !important;
    flex-basis: auto !important;
}
.st-key-chat_panel, .st-key-state_panel { height: 100% !important; }
</style>
"""

STATUS_BADGE = {
    STATUS_MODEL: ("orange", ":material/smart_toy:"),
    STATUS_TOOL: ("violet", ":material/build:"),
    STATUS_DONE: ("green", ":material/check_circle:"),
    STATUS_ERROR: ("red", ":material/error:"),
}

COUNTER_HELP = {
    "Status": "Current observer lifecycle state.",
    "Turn": "Chat turn counter within current conversation (starts at 1).",
    "Model calls in turn": "Number of actual model invocations in current turn.",
    "Event steps in turn": "Observer event sequence count in current turn.",
    "Tool calls in turn": "Number of tool calls executed in current turn.",
}

CONTEXT_NOTE = (
    "Context captured at the LangChain layer (system prompt, messages, tool schemas), "
    "not the raw wire payload."
)


# ---------------------------------------------------------------- session state


def new_conversation() -> None:
    """Clear conversational state without deleting on-disk traces or memory."""
    ss = st.session_state
    if ss.get("active_run") is not None:
        try:
            ss.active_run.abort()
        except Exception:
            pass
    ss.conversation_id = uuid.uuid4().hex
    ss.model_history = []
    ss.ui_history = []
    ss.observer = Observer(conversation_id=ss.conversation_id)
    # An in-flight turn of the previous conversation is aborted and discarded.
    ss.active_run = None
    ss.pop("snapshot_choice", None)
    ss.pop("message_choice", None)
    ss.pop("memory_select_choice", None)


def init_state() -> None:
    if "observer" not in st.session_state:
        new_conversation()


def active_run() -> TurnRun | None:
    return st.session_state.get("active_run")


# ---------------------------------------------------------------- trace rendering


def usage_text(usage: dict | None) -> str:
    return (
        f" | {usage.get('input_tokens')} in / {usage.get('output_tokens')} out tokens"
        if usage
        else ""
    )


def render_events(events: list[dict]) -> None:
    """Render steps in exact sequence."""
    finished = {e["tool_call_id"]: e for e in events if e["type"] == "tool_finished"}
    shown = False
    for event in events:
        kind = event["type"]
        if kind == "model_request":
            shown = True
            st.markdown(
                f":material/smart_toy: **Model call #{event['model_call_index']}** | "
                f"{event['message_count']} messages | {event['tool_count']} tools"
            )
        elif kind == "model_response":
            requested = event.get("tool_calls_requested") or []
            if requested:
                names = ", ".join(f"`{c['name']}`" for c in requested)
                st.caption(
                    f"↳ requested {len(requested)} tool call(s): {names}{usage_text(event.get('usage'))}"
                )
            else:
                st.caption(
                    f"↳ returned final response, no tools requested{usage_text(event.get('usage'))}"
                )
        elif kind == "tool_started":
            shown = True
            render_tool_step(event, finished.get(event["tool_call_id"]))
        elif kind == "run_failed":
            st.error(f"Turn failed: {event.get('error')}", icon=":material/error:")
    if not shown:
        st.caption("No steps executed yet.")


def render_tool_step(started: dict, done: dict | None) -> None:
    with st.container(border=True):
        header = st.container(horizontal=True, vertical_alignment="center")
        header.markdown(f":material/build: **{started['tool_name']}**")
        if done is None:
            header.badge("running", color="orange")
        else:
            result = done.get("result")
            failed = done.get("status") in ("error", "exception") or (
                isinstance(result, dict) and result.get("ok") is False
            )
            header.badge("error" if failed else "ok", color="red" if failed else "green")
            if done.get("elapsed_ms") is not None:
                header.caption(f"{done['elapsed_ms']} ms")
        st.caption(f"tool_call_id `{started['tool_call_id']}`")
        st.json(started.get("arguments", {}), expanded=True)
        if done is None:
            return
        if done.get("status") == "exception":
            st.error(f"Exception during tool execution: {done.get('error')}")
        elif failed:
            st.caption("Tool returned error dictionary.")
        render_result(done.get("result"))


TEXT_RESULT_FIELDS = ("content", "stdout", "stderr")


def render_result(result) -> None:
    st.caption("Result")
    if isinstance(result, dict):
        st.json({k: v for k, v in result.items() if k not in TEXT_RESULT_FIELDS}, expanded=True)
        for key in TEXT_RESULT_FIELDS:
            value = result.get(key)
            if isinstance(value, str) and value:
                st.caption(key)
                st.code(value, language=None, wrap_lines=True)
    elif isinstance(result, list):
        st.json(result, expanded=True)
    elif result is not None:
        st.code(str(result), language=None, wrap_lines=True)


def steps_label(events: list[dict]) -> str:
    model_calls = sum(1 for e in events if e["type"] == "model_request")
    tool_calls = sum(1 for e in events if e["type"] == "tool_started")
    return f"Execution steps ({model_calls} model call(s), {tool_calls} tool call(s))"


def render_inline_tool(tool_item: dict) -> None:
    tool_name = tool_item.get("tool_name", "tool")
    status = tool_item.get("status", "running")
    elapsed = tool_item.get("elapsed_ms")
    elapsed_str = f" · {elapsed}ms" if elapsed is not None else ""
    label = f":material/build: **{tool_name}** ({status}{elapsed_str})"

    with st.expander(label, expanded=False, icon=":material/build:"):
        st.caption(f"tool_call_id `{tool_item.get('tool_call_id', '')}`")
        if tool_item.get("args"):
            st.caption("Arguments")
            raw_args = tool_item["args"]
            if isinstance(raw_args, dict):
                small_args = {}
                large_args = {}
                for k, v in raw_args.items():
                    if isinstance(v, str) and len(v) > 2000:
                        small_args[k] = f"<{len(v)} chars string>"
                        large_args[k] = v
                    else:
                        small_args[k] = v
                st.json(small_args, expanded=True)
                for k, v in large_args.items():
                    st.caption(f"Argument `{k}` ({len(v)} chars):")
                    preview = v[:2000] + ("\n... [truncated for UI performance]" if len(v) > 2000 else "")
                    st.code(preview, language=None, wrap_lines=True)
            else:
                st.json(raw_args, expanded=True)
        if status == "running":
            st.caption("Running tool…")
        elif tool_item.get("status") in ("error", "exception"):
            st.error(f"Tool error: {tool_item.get('error') or tool_item.get('result')}")
        else:
            render_result(tool_item.get("result"))


def render_turn_elements(elements: list[dict], live: bool = False) -> None:
    for el in elements:
        kind = el.get("type")
        if kind == "text":
            content = el.get("content", "")
            if live and el.get("streaming"):
                st.markdown(content + " ▌")
            elif content:
                st.markdown(content)
        elif kind == "tool":
            render_inline_tool(el)
        elif kind == "error":
            st.error(el.get("message", "Error"), icon=":material/error:")


def render_history() -> None:
    run = active_run()
    for turn in st.session_state.ui_history:
        if run is not None and turn is run.turn:
            continue  # rendered live by follow_active_run
        with st.chat_message("user"):
            st.markdown(turn["user"])
        with st.chat_message("assistant"):
            if turn.get("elements"):
                render_turn_elements(turn["elements"])
            elif turn.get("answer"):
                st.markdown(turn["answer"])
            elif turn.get("error"):
                st.error(turn["error"], icon=":material/error:")


# ---------------------------------------------------------------- state & context panel


def message_rows(messages: list[dict]) -> list[dict]:
    rows = []
    for index, message in enumerate(messages):
        text = message_text(message.get("content", ""))
        calls = message.get("tool_calls") or []
        if calls:
            kind = "tool_calls"
            tool = ", ".join(f"{c['name']} ({c['id']})" for c in calls)
        elif message.get("role") == "tool":
            kind = "tool_result"
            tool = f"{message.get('name')} ({message.get('tool_call_id')})"
        else:
            kind = "text"
            tool = ""
        rows.append(
            {
                "index": index,
                "role": message.get("role"),
                "type": kind,
                "preview": text[:120] + ("…" if len(text) > 120 else ""),
                "tool / ID": tool,
            }
        )
    return rows


def render_counters(observer: Observer) -> None:
    counters = observer.counters()
    status = counters["Status"]
    color, icon = STATUS_BADGE.get(status, ("gray", ":material/radio_button_unchecked:"))
    row = st.container(horizontal=True, vertical_alignment="center")
    row.badge(status, icon=icon, color=color)
    if observer.running_tools:
        row.caption("running: " + ", ".join(observer.running_tools.values()))
    row.caption(
        f"conversation `{observer.conversation_id[:8]}` | run `{(observer.run_id or '-')[:8]}`",
        help=f"conversation_id: {observer.conversation_id}\n\nrun_id: {observer.run_id or '-'}",
    )
    keys = list(COUNTER_HELP)
    for pair in (keys[:2], keys[2:4]):
        for col, key in zip(st.columns(2, gap="small"), pair):
            col.metric(key, counters[key], help=COUNTER_HELP[key], border=True)
    if observer.turn_failed:
        st.error(f"Turn {observer.chat_turn} failed: {observer.error}", icon=":material/error:")
    if observer.history_rolled_back:
        st.warning("Model history was rolled back before the failed turn.")


def render_capabilities(observer: Observer, caps: dict, tool_schemas: list[dict]) -> None:
    with st.expander(f"Registered Tools ({len(tool_schemas)})", icon=":material/build:"):
        for schema in tool_schemas:
            st.markdown(f"**{schema['name']}**")
            st.json(schema, expanded=False)

    with st.expander(f"Skills Catalog ({len(caps['skills'])})", icon=":material/menu_book:"):
        if not caps["skills"]:
            st.caption("No skills discovered.")
        for skill in caps["skills"]:
            st.markdown(f"**{skill['name']}** | `{skill['location']}`  \n{skill['description']}")
        for diag in caps["skill_diagnostics"]:
            st.warning(diag)

    inventory = observer.inventory()
    with st.expander(f"Loaded Skills in Context ({len(inventory['skills'])})", icon=":material/task_alt:"):
        if not inventory["skills"]:
            st.caption("No skills invoked via use_skill yet in this conversation.")
        for item in inventory["skills"]:
            st.markdown(
                f"**{item['skill']}** | message #{item['message_index']} | "
                f"tool_call_id `{item['tool_call_id']}` | {item['chars']} chars | "
                f"first request: {item['first_request'] or 'pending'}"
            )

    with st.expander(f"Read Resources ({len(inventory['resources'])})", icon=":material/description:"):
        if not inventory["resources"]:
            st.caption("No external resources read via read_file yet.")
        for item in inventory["resources"]:
            st.markdown(f"`{item['path']}` | message #{item['message_index']} | tool_call_id `{item['tool_call_id']}`")


def render_memory_pane(interactive: bool = True) -> None:
    """Display file-system memory contents for inspection without adding to prompt context."""
    memories = scan_memory(paths.MEMORY_DIR)
    with st.expander(f"Durable Memory Files ({len(memories)})", icon=":material/psychology:"):
        if not memories:
            st.caption("No memory files exist yet. Files appear on first memory write.")
            return

        if interactive:
            options = [m.path for m in memories]
            choice = st.selectbox("Inspect memory file", options, key="memory_select_choice")
            selected = next((m for m in memories if m.path == choice), None)
            if selected:
                st.caption(
                    f"Bucket: **{selected.bucket}** | {selected.bytes} bytes | "
                    f"Description: {selected.description} | Updated: {selected.updated[:19]}"
                )
                file_path = paths.MEMORY_DIR / selected.path
                if file_path.is_file():
                    st.code(file_path.read_text(encoding="utf-8"), language="markdown", wrap_lines=True)
        else:
            st.caption(f"{len(memories)} memory file(s) on disk:")
            for m in memories:
                st.markdown(f"- **{m.bucket}** / `{m.name}`: {m.description}")


def render_messages(observer: Observer, interactive: bool) -> None:
    with st.expander(f"Current Message History ({len(observer.messages)})", icon=":material/forum:"):
        if not observer.messages:
            st.caption("No messages in history.")
            return
        st.dataframe(message_rows(observer.messages), hide_index=True, width="stretch", height="content")
        if interactive:
            index = st.selectbox(
                "View full message",
                options=list(range(len(observer.messages))),
                index=len(observer.messages) - 1,
                key="message_choice",
            )
            st.json(observer.messages[index], expanded=True)
        else:
            st.caption("Latest message:")
            st.json(observer.messages[-1], expanded=False)


def snapshot_label(snapshot: dict) -> str:
    time_part = (snapshot.get("captured_at") or "")[11:19]
    return f"Turn {snapshot['chat_turn']}, model call #{snapshot['model_call_index']} ({time_part})"


def snapshot_summary(snapshot: dict) -> str:
    usage = snapshot.get("usage")
    tokens = (
        f" | {usage.get('input_tokens')} in / {usage.get('output_tokens')} out tokens"
        if usage
        else " | no usage data"
    )
    return (
        f"model `{snapshot.get('model_name') or '-'}` | {snapshot['message_count']} messages | "
        f"{len(snapshot['tools'])} tools | "
        f"{snapshot['system_prompt_chars'] + snapshot['message_chars']} chars{tokens}"
    )


def render_context(observer: Observer, interactive: bool) -> None:
    st.markdown("##### Context Sent to Model (LangChain Layer)", help=CONTEXT_NOTE)
    snapshots = observer.snapshots
    if not snapshots:
        st.info("No requests sent yet. Showing configuration preview.", icon=":material/info:")
        tools = [tool_schema(t) for t in TOOLS]
        with st.expander("Configuration: system prompt", icon=":material/article:"):
            st.code(system_prompt(), language="markdown", wrap_lines=True)
        with st.expander(f"Configuration: tool schemas ({len(tools)})", icon=":material/data_object:"):
            st.json(tools, expanded=False)
        return

    if interactive:
        row = st.container(horizontal=True, vertical_alignment="bottom")
        with row:
            choice = st.selectbox(
                "Request snapshot",
                options=list(range(len(snapshots))),
                index=len(snapshots) - 1,
                format_func=lambda i: snapshot_label(snapshots[i]),
                key="snapshot_choice",
            )
        snapshot = snapshots[choice]
        row.download_button(
            "Snapshot JSON",
            icon=":material/download:",
            data=json.dumps(snapshot, ensure_ascii=False, indent=2),
            file_name=f"snapshot_turn{snapshot['chat_turn']:02d}_call{snapshot['model_call_index']:02d}.json",
            mime="application/json",
            on_click="ignore",
        )
        row.download_button(
            "Conversation JSON",
            icon=":material/download:",
            data=json.dumps(observer.export(), ensure_ascii=False, indent=2),
            file_name=f"conversation_{observer.conversation_id[:8]}.json",
            mime="application/json",
            on_click="ignore",
        )
    else:
        snapshot = snapshots[-1]
        st.caption(f"Following latest snapshot: {snapshot_label(snapshot)}")
    st.caption(snapshot_summary(snapshot))

    meta = {k: v for k, v in snapshot.items() if k not in ("system_prompt", "messages", "tools")}
    with st.expander(f"Snapshot: system prompt ({snapshot['system_prompt_chars']} chars)", icon=":material/article:"):
        st.code(snapshot["system_prompt"], language="markdown", wrap_lines=True)
    with st.expander(f"Snapshot: messages ({snapshot['message_count']})", icon=":material/forum:"):
        st.dataframe(message_rows(snapshot["messages"]), hide_index=True, width="stretch", height="content")
        st.json(snapshot["messages"], expanded=False)
    with st.expander(f"Snapshot: tool schemas ({len(snapshot['tools'])})", icon=":material/data_object:"):
        st.json(snapshot["tools"], expanded=False)
    with st.expander("Snapshot: metadata", icon=":material/info:"):
        st.json(meta, expanded=True)


def render_event_log(observer: Observer) -> None:
    with st.expander(f"Event Log ({len(observer.events)})", icon=":material/list:"):
        rows = [
            {
                "turn": e["chat_turn"],
                "seq": e["sequence"],
                "event": e["type"],
                "tool": e.get("tool_name", ""),
                "tool_call_id": e.get("tool_call_id", ""),
                "time": e["timestamp"][11:23],
            }
            for e in observer.events
        ]
        if rows:
            st.dataframe(rows, hide_index=True, width="stretch", height="content")
        else:
            st.caption("No events recorded.")


def render_state_panel(interactive: bool, obs: Any | None = None) -> None:
    observer = obs if obs is not None else st.session_state.observer
    st.subheader("State & Context")
    render_counters(observer)
    render_context(observer, interactive)
    render_memory_pane(interactive)
    render_capabilities(observer, capabilities(), [tool_schema(t) for t in TOOLS])
    render_messages(observer, interactive)
    render_event_log(observer)


# ---------------------------------------------------------------- run turn


def start_turn(text: str, settings) -> None:
    """Create the turn and hand the agent stream to a worker thread.

    The worker survives Streamlit reruns/stops of the script thread; see turn_runner.
    """
    ss = st.session_state
    observer: Observer = ss.observer
    run = TurnRun(
        text=text,
        history=ss.model_history,
        observer=observer,
        writer_factory=lambda run_id, chat_turn: TraceWriter(
            paths.TRACES_DIR, PROJECT_NAME, observer.conversation_id, run_id, chat_turn
        ),
        capabilities=capabilities(),
        recursion_limit=RECURSION_LIMIT,
        on_exception=lambda exc: log_exception(paths.TRACES_DIR, exc),
    )
    ss.ui_history.append(run.turn)
    ss.active_run = run
    run.start(lambda: build_agent(build_model(settings)))


def finalize_run() -> None:
    """Commit a finished turn to model history. Idempotent; safe on every script run."""
    ss = st.session_state
    run = active_run()
    if run is None or not run.done.is_set():
        return
    with run.lock:
        if run.succeeded:
            ss.model_history = run.working
        ss.active_run = None
    ss.pop("snapshot_choice", None)
    ss.pop("message_choice", None)
    ss.pop("memory_select_choice", None)


def follow_active_run(run: TurnRun, live_slot, state_box) -> None:
    """Poll the worker and re-render until the turn finishes, then rerun the page.

    A rerun request interrupts only this polling loop; the next script run resumes it.
    """
    seen = -1
    last_panel = time.monotonic()
    while True:
        finished = run.done.is_set()
        if finished or run.version != seen:
            with run.lock:
                seen = run.version
                elements_snapshot = [dict(el) for el in run.elements]
            if live_slot is not None:
                try:
                    with live_slot.container():
                        render_turn_elements(elements_snapshot, live=not finished)
                except Exception:
                    pass
            now = time.monotonic()
            if finished or now - last_panel >= PANEL_REFRESH_SECONDS:
                if state_box is not None:
                    with run.lock:
                        obs_snap = run.observer.snapshot()
                    try:
                        with state_box.container():
                            render_state_panel(interactive=False, obs=obs_snap)
                    except Exception:
                        pass
                last_panel = now
        if finished:
            break
        time.sleep(POLL_SECONDS)
    finalize_run()
    st.rerun()


# ---------------------------------------------------------------- output files


def output_files() -> list[str]:
    output_dir = paths.WORKSPACE_DIR / paths.OUTPUT_SUBDIR
    if not output_dir.is_dir():
        return []
    return sorted(p.relative_to(paths.WORKSPACE_DIR).as_posix() for p in output_dir.rglob("*") if p.is_file())


def render_output_files() -> None:
    st.subheader("Output Files")
    files = output_files()
    if not files:
        st.caption("No files under workspace/output/.")
        return
    choice = st.selectbox("Select file in workspace/output/", files, key="output_choice")
    path = paths.WORKSPACE_DIR / choice
    if not path.is_file():
        st.warning("File no longer exists.")
        return
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    st.caption(f"{choice} | {len(data)} bytes | Preview only (not in model context)")
    with st.container(border=True):
        if path.suffix.lower() in (".md", ".markdown"):
            st.markdown(text)
        else:
            st.code(text, language=None, wrap_lines=True)
    st.download_button("Download file", data=data, file_name=path.name, on_click="ignore")


# ---------------------------------------------------------------- page


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon=":material/smart_toy:", layout="wide")
    st.html(PAGE_CSS)
    init_state()
    paths.ensure_workspace()
    finalize_run()
    run = active_run()

    header = st.container(horizontal=True, vertical_alignment="center")
    header.title(APP_TITLE)
    header.button("New conversation", icon=":material/add_comment:", on_click=new_conversation)

    # Provider badge in header
    try:
        p_info = get_active_provider_info()
        base_str = f" | {p_info['base_url']}" if p_info.get("base_url") else ""
        header.caption(f"Provider: **{p_info['mode']}** | Model: **{p_info['model']}**{base_str}")
    except Exception:
        pass

    st.caption(CAPABILITY_TEXT)

    settings, missing = load_settings()
    chat_col, state_col = st.columns([5, 4], gap="medium")
    with chat_col:
        chat_box = st.container(height=PANEL_HEIGHT, border=True, autoscroll=True, key="chat_panel")
        with chat_box:
            if missing:
                st.warning(
                    "Missing configuration: " + ", ".join(missing) + ". Create a .env file from .env.example."
                )
            if not st.session_state.ui_history:
                st.caption("Enter a request below to get started.")
            render_history()
            live_slot = None
            if run is not None:
                with st.chat_message("user"):
                    st.markdown(run.turn["user"])
                with st.chat_message("assistant"):
                    live_slot = st.empty()
    with state_col:
        with st.container(height=PANEL_HEIGHT, border=True, key="state_panel"):
            state_box = st.empty()
            if run is not None:
                with run.lock:
                    obs_snap = run.observer.snapshot()
                with state_box.container():
                    render_state_panel(interactive=False, obs=obs_snap)
            else:
                with state_box.container():
                    render_state_panel(interactive=True)
            render_output_files()

    prompt = st.chat_input("Enter your request…", disabled=bool(missing) or run is not None)
    if run is not None:
        if prompt:
            st.toast("A turn is still running; the new request was ignored.", icon=":material/hourglass:")
        follow_active_run(run, live_slot, state_box)
    elif prompt and settings is not None:
        start_turn(prompt, settings)
        st.rerun()


main()

"""Past Conversation & Trace Viewer for personal-agent.

Operates in two modes:
1. Streamlit GUI: uv run streamlit run viewer.py
2. CLI Utility:   uv run python viewer.py [conv_id] [--transcript | --summary | --list | --export <file>]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import paths
from trace_replay import (
    ConversationMetadata,
    ReplayedConversation,
    generate_markdown_transcript,
    list_conversations,
    load_conversation,
)


# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------


def run_cli() -> None:
    args = sys.argv[1:]
    traces_dir = paths.TRACES_DIR

    if not args or args[0] in ("-h", "--help"):
        print("Personal Agent - Past Conversation & Trace Viewer (CLI)")
        print("\nUsage:")
        print("  python viewer.py --list")
        print("  python viewer.py <conv_id> --summary")
        print("  python viewer.py <conv_id> --transcript")
        print("  python viewer.py <conv_id> --export <output.md>")
        print("\nTo launch interactive GUI:")
        print("  streamlit run viewer.py")
        sys.exit(0)

    if args[0] in ("-l", "--list"):
        convs = list_conversations(traces_dir)
        if not convs:
            print(f"No conversation traces found in {traces_dir}")
            return
        print(f"Found {len(convs)} conversation(s) in {traces_dir}:\n")
        print(f"{'Short ID':<10} {'Started At':<22} {'Turns':<6} {'Events':<8} {'Model':<30} {'First Prompt'}")
        print("-" * 105)
        for c in convs:
            prompt_preview = (c.first_prompt.replace("\n", " ")[:35] + "…") if len(c.first_prompt) > 35 else c.first_prompt
            print(f"{c.short_id:<10} {c.started_at[:19]:<22} {c.turn_count:<6} {c.total_events:<8} {(c.model_name or '-'):<30} {prompt_preview}")
        return

    conv_id = args[0]
    action = args[1] if len(args) > 1 else "--summary"

    try:
        conv = load_conversation(traces_dir, conv_id)
    except FileNotFoundError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    if action in ("-s", "--summary"):
        meta = conv.metadata
        print("=" * 60)
        print(f"Conversation: {meta.short_id} ({meta.conversation_id})")
        print("=" * 60)
        print(f"Started at:       {meta.started_at}")
        print(f"Model:            {meta.model_name or 'unknown'}")
        print(f"Total turns:      {meta.turn_count}")
        print(f"Total events:     {len(conv.events)}")
        print(f"Snapshots:        {len(conv.snapshots)}")
        print(f"Trace files ({len(meta.files)}):")
        for f in meta.files:
            print(f"  * {f.name}")
        print("\nTurns:")
        for t in conv.turns:
            tools_used = [el.get("tool_name") for el in t.elements if el.get("type") == "tool"]
            print(f"  Turn {t.chat_turn} (run {t.run_id[:8]}):")
            print(f"    User:    {repr(t.user[:60])}...")
            print(f"    Tools ({len(tools_used)}): {', '.join(tools_used) or 'none'}")
            ans_prev = (t.answer[:60] + "...") if t.answer else "(no text saved in trace)"
            print(f"    Answer:  {repr(ans_prev)}")
    elif action in ("-t", "--transcript"):
        print(generate_markdown_transcript(conv))
    elif action in ("-e", "--export"):
        if len(args) < 3:
            print("Error: --export requires an output filename", file=sys.stderr)
            sys.exit(1)
        out_path = Path(args[2])
        transcript = generate_markdown_transcript(conv)
        out_path.write_text(transcript, encoding="utf-8")
        print(f"Transcript exported to {out_path.resolve()} ({len(transcript)} chars)")
    else:
        print(f"Unknown action: {action}. Use --summary, --transcript, or --export <file>.", file=sys.stderr)
        sys.exit(1)


# -----------------------------------------------------------------------------
# Streamlit GUI
# -----------------------------------------------------------------------------


def run_gui() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="Past Conversation Viewer",
        page_icon=":material/history_edu:",
        layout="wide",
    )

    st.html(
        """
        <style>
        [data-testid="stAppScrollToBottomContainer"] {
            overflow: hidden !important;
        }
        [data-testid="stMainBlockContainer"] {
            padding-top: 3.5rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        /* Stretch both chat and context containers to flush with viewport bottom */
        [data-testid="stLayoutWrapper"]:has(> .st-key-chat_col),
        [data-testid="stLayoutWrapper"]:has(> .st-key-context_col) {
            height: calc(100dvh - 8rem) !important;
            max-height: calc(100dvh - 8rem) !important;
            flex-basis: auto !important;
        }
        .st-key-chat_col, .st-key-context_col {
            height: 100% !important;
            max-height: 100% !important;
        }
        .st-key-chat_col > div, .st-key-context_col > div {
            height: 100% !important;
            max-height: 100% !important;
        }
        /* Clean up header spacing */
        h1, h2, h3 {
            margin-top: 0 !important;
        }
        </style>
        """
    )

    traces_dir = paths.TRACES_DIR
    convs = list_conversations(traces_dir)

    head_col1, head_col2 = st.columns([7, 3], vertical_alignment="center")
    with head_col1:
        st.markdown(
            "### :material/history_edu: Trace & Conversation Viewer",
            help=f"Inspecting trace logs from {traces_dir.resolve()}",
        )
    with head_col2:
        st.caption(f":material/folder: `{traces_dir.name}/` ({len(convs)} recorded sessions)")

    if not convs:
        st.warning(f"No conversation traces found in `{traces_dir}`.")
        return

    # Sidebar / Header Session Selector
    with st.sidebar:
        st.header("Conversations")
        options = [c.short_id for c in convs]

        def format_conv(short_id: str) -> str:
            c = next(x for x in convs if x.short_id == short_id)
            time_str = c.started_at[11:19] if c.started_at else "--:--"
            date_str = c.started_at[:10] if c.started_at else ""
            return f"{c.short_id} ({c.turn_count} turns, {date_str} {time_str})"

        selected_id = st.selectbox(
            "Select conversation",
            options=options,
            format_func=format_conv,
            key="selected_conv_id",
        )

        conv = load_conversation(traces_dir, selected_id)
        meta = conv.metadata

        st.divider()
        st.markdown(f"**Conversation ID**: `{meta.conversation_id}`")
        st.markdown(f"**Started**: `{meta.started_at}`")
        st.markdown(f"**Model**: `{meta.model_name or 'unknown'}`")
        st.markdown(f"**Turns**: `{meta.turn_count}` | **Events**: `{len(conv.events)}`")

        st.divider()
        st.subheader("Trace Files")
        for f in meta.files:
            st.caption(f"`{f.name}`")

        st.divider()
        transcript = generate_markdown_transcript(conv)
        st.download_button(
            "Download Transcript (.md)",
            data=transcript,
            file_name=f"transcript_{meta.short_id}.md",
            mime="text/markdown",
            icon=":material/download:",
            use_container_width=True,
        )
        st.download_button(
            "Download Raw Events (.json)",
            data=json.dumps(conv.events, ensure_ascii=False, indent=2),
            file_name=f"events_{meta.short_id}.json",
            mime="application/json",
            icon=":material/data_object:",
            use_container_width=True,
        )

    # Main Two-Column View
    chat_col, state_col = st.columns([5, 4], gap="medium")

    # Left Column: Conversation Turns & Inline Tools
    with chat_col:
        st.markdown(f"**Conversation Flow ({meta.turn_count} turns)**")
        with st.container(height=900, border=True, key="chat_col"):
            for turn in conv.turns:
                with st.chat_message("user"):
                    st.markdown(f"**[Turn {turn.chat_turn}]**")
                    st.markdown(turn.user or "*(empty prompt)*")

                with st.chat_message("assistant"):
                    # Render tool executions
                    tool_items = [el for el in turn.elements if el.get("type") == "tool"]
                    for t in tool_items:
                        tool_name = t.get("tool_name", "tool")
                        status = t.get("status", "success")
                        elapsed = t.get("elapsed_ms")
                        elapsed_str = f" · {elapsed}ms" if elapsed is not None else ""
                        badge_color = "red" if status in ("error", "exception") else "violet"
                        
                        label = f":material/build: **{tool_name}** ({status}{elapsed_str})"
                        with st.expander(label, expanded=False):
                            st.caption(f"Call ID: `{t.get('tool_call_id')}`")
                            st.caption("Arguments:")
                            st.json(t.get("args", {}), expanded=True)
                            st.caption("Result:")
                            res = t.get("result")
                            if isinstance(res, (dict, list)):
                                st.json(res, expanded=True)
                            else:
                                st.code(str(res), language=None, wrap_lines=True)

                    if turn.answer:
                        st.markdown(turn.answer)
                    elif turn.error:
                        st.error(f"Turn error: {turn.error}", icon=":material/error:")
                    else:
                        st.caption("*(Terminal turn: final answer was streamed to UI and omitted from raw trace)*")

    # Right Column: State & Context Inspector
    with state_col:
        st.markdown("**Trace & Context Inspector**")
        with st.container(height=900, border=True, key="context_col"):
            tabs = st.tabs(["Context Snapshots", "Events Log", "Tool Summary"])

            # Tab 1: Context Snapshots
            with tabs[0]:
                snapshots = conv.snapshots
                if not snapshots:
                    st.caption("No context snapshots recorded in this conversation.")
                else:
                    snap_options = list(range(len(snapshots)))

                    def snap_label(i: int) -> str:
                        s = snapshots[i]
                        time_p = (s.get("captured_at") or "")[11:19]
                        return f"Turn {s.get('chat_turn')}, Call #{s.get('model_call_index')} ({time_p})"

                    selected_snap_idx = st.selectbox(
                        "Select model request snapshot",
                        options=snap_options,
                        format_func=snap_label,
                        key="snap_choice",
                    )
                    snap = snapshots[selected_snap_idx]

                    st.caption(
                        f"Model: `{snap.get('model_name')}` | Messages: {snap.get('message_count')} | "
                        f"Tools: {len(snap.get('tools', []))} | System Prompt Chars: {snap.get('system_prompt_chars')}"
                    )

                    with st.expander("System Prompt", icon=":material/article:"):
                        st.code(snap.get("system_prompt", ""), language="markdown", wrap_lines=True)

                    with st.expander(f"Messages in Context ({len(snap.get('messages', []))})", icon=":material/forum:"):
                        for i, m in enumerate(snap.get("messages", [])):
                            role = m.get("role")
                            st.markdown(f"**#{i} [{role}]**")
                            content = m.get("content")
                            if isinstance(content, (dict, list)):
                                st.json(content, expanded=False)
                            elif content:
                                st.code(str(content)[:1000] + ("..." if len(str(content)) > 1000 else ""), language=None, wrap_lines=True)
                            for call in m.get("tool_calls", []) or []:
                                st.caption(f"↳ tool call: `{call.get('name')}` ({call.get('id')})")
                            st.divider()

                    with st.expander(f"Tool Schemas ({len(snap.get('tools', []))})", icon=":material/data_object:"):
                        st.json(snap.get("tools", []), expanded=False)

            # Tab 2: Chronological Events Log
            with tabs[1]:
                event_rows = []
                for ev in conv.events:
                    event_rows.append(
                        {
                            "turn": ev.get("chat_turn"),
                            "seq": ev.get("sequence"),
                            "type": ev.get("type"),
                            "tool": ev.get("tool_name", ""),
                            "time": (ev.get("timestamp") or "")[11:23],
                        }
                    )
                if event_rows:
                    st.dataframe(event_rows, hide_index=True, use_container_width=True)
                else:
                    st.caption("No events recorded.")

            # Tab 3: Tool Summary
            with tabs[2]:
                all_tools = []
                for t in conv.turns:
                    for el in t.elements:
                        if el.get("type") == "tool":
                            all_tools.append(
                                {
                                    "turn": t.chat_turn,
                                    "tool": el.get("tool_name"),
                                    "status": el.get("status"),
                                    "elapsed_ms": el.get("elapsed_ms"),
                                }
                            )
                if all_tools:
                    st.dataframe(all_tools, hide_index=True, use_container_width=True)
                else:
                    st.caption("No tools were called in this conversation.")


# -----------------------------------------------------------------------------
# Main Routing
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # If running with arguments or in a terminal without streamlit runner:
    is_cli = len(sys.argv) > 1 and not sys.argv[0].endswith("streamlit")
    # Streamlit execution sets __package__ or imports streamlit
    if "streamlit" in sys.modules and not is_cli:
        run_gui()
    elif is_cli:
        run_cli()
    else:
        # Default when run via `python viewer.py` without args -> run CLI help
        run_cli()
else:
    # When imported or launched via `streamlit run viewer.py`:
    run_gui()

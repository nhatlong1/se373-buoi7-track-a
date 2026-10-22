# Personal Agent

A modular personal agent built on LangChain `create_agent`, Streamlit, multi-provider model routing, modular skills, and durable file-system memory.

## Architecture

1. **Multi-Provider Layer**:
   - `OpenAI Chat Completions`: Standard OpenAI-compatible format with native tool calling (e.g. via Aperture at `http://ai/v1`).
   - `UIT`: Custom `UITChatModel` with `UITToolMiddleware` designed for campus vLLM deployments lacking native tool choice, injecting tool schemas into the system prompt and parsing tags (`<tool_call>`, Qwen XML, Gemma markers) from assistant text.
2. **File-System Memory**:
   - Durable markdown-backed memory under `memory/` outside `workspace/`.
   - Normalized two-layer contract: `(bucket, name)`.
   - Root bucket `"/"` is strictly reserved for `name="profile"` (`memory/profile.md`).
   - Domain buckets (e.g. `"topics"`, `"areas"`) store workstream and domain facts (`memory/<bucket>/<name>.md`).
   - Only the profile body and an index of active memory items enter the prompt; full bodies are loaded on-demand via `memory_read`.
3. **Skills**:
   - Discovered dynamically under `workspace/skills/*/SKILL.md`.
   - Metadata is exposed in the prompt; full body and reference assets are loaded via `use_skill`.
   - Includes seed skill `authoring-skills`.
4. **Safety & Bounds**:
   - Strict workspace containment.
   - Symlink traversal protection.
   - No shell execution tool.

## Available Tools

1. `list_files(path)`: List entries of a workspace directory.
2. `read_file(path)`: Read UTF-8 files across the workspace.
3. `write_file(path, content)`: Write files under `output/` or `skills/<slug>/`.
4. `use_skill(name)`: Load skill body and reference list.
5. `memory_list(bucket=None)`: List memory items with metadata (`bucket`, `name`, `description`, `bytes`, `updated`).
6. `memory_read(bucket, name)`: Read a memory item by bucket and name.
7. `memory_write(bucket, name, description, content)`: Atomically create or update a memory item.
8. `memory_delete(bucket, name)`: Delete a memory item by bucket and name.

## Setup & Running

From `personal-agent/`:
```bash
uv sync
uv run pytest
uv run streamlit run app.py
```

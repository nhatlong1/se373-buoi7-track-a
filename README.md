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
5. **Observability & Tracing**:
   - `ObserverMiddleware` intercepts model requests, responses, and tool dispatches in real time.
   - Persists structured JSONL traces per turn to `traces/` with timestamps, usage metrics, and snapshots.
   - Logs runtime exception tracebacks to `traces/debug.log`.

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
cp .env.example .env
# edit .env with proper values
uv sync
uv run streamlit run app.py

# run tests
uv run pytest

# inspect past conversation traces (GUI)
uv run streamlit run viewer.py

# inspect traces via CLI
uv run python viewer.py --list
uv run python viewer.py <conv_id> --summary
uv run python viewer.py <conv_id> --transcript
```

## Featured trace run:

- Trace ID: 921cd3b8
- Trace files:
  - [20261023-143742_921cd3b8_turn01_0474552f.jsonl](traces/20261023-143742_921cd3b8_turn01_0474552f.jsonl)
  - [20261023-144044_921cd3b8_turn02_e4c55bab.jsonl](traces/20261023-144044_921cd3b8_turn02_e4c55bab.jsonl)
  - [20261023-145519_921cd3b8_turn03_932022f2.jsonl](traces/20261023-145519_921cd3b8_turn03_932022f2.jsonl)
- Trace ID: bbee898c
- Trace files:
  - [20261023-151414_bbee898c_turn01_a2fefc3b.jsonl](traces/20261023-151414_bbee898c_turn01_a2fefc3b.jsonl)
  - [20261023-152500_bbee898c_turn02_dba32188.jsonl](traces/20261023-152500_bbee898c_turn02_dba32188.jsonl)
- Trace ID: 64cf46a1
- Trace files:
  - [20261023-153022_64cf46a1_turn01_1b24269e.jsonl](traces/20261023-153022_64cf46a1_turn01_1b24269e.jsonl)
  - [20261023-154151_64cf46a1_turn02_f54b7b45.jsonl](traces/20261023-154151_64cf46a1_turn02_f54b7b45.jsonl)

### Summary

#### 921cd3b8

The user asked the agent for vector database recommendation for SE373 capstone project under 4 vCPU and 12GB RAM footprint. Qdrant is recommended as the primary vector database, fitting the constraints of a single host with 4 vCPU and 12 GB RAM while satisfying requirements for client-server architecture, strong per-user data isolation, independent BM25 full-text search and vector similarity, and low memory footprint.

The user asked the agent to extract information from the description of BizCare, SE373 Agentic Engineering final project. BizCare is a multi-tenant AI customer support platform for small Vietnamese businesses, deployed on a single host with 4 vCPU and 12 GB RAM using Qdrant as the primary vector database.

The user asked the agent to author a skill for writing document, including a preset library of templates for reference. The agent authored a document-writing skill to improve language quality, triggered whenever an agent must author or edit persistent prose with general.md (fallback), research-report.md, code-review-report.md, code-analysis-report.md, spec-analysis-report.md, technical-specification.md, documentation.md, graphical-design-document.md, architectural-design-document.md, system-design-document.md, academic-paper.md

#### bbee898c

The user asked the agent what they're working on. The agent responded with information about BizCare retrieved from memory and surface known gaps and good next work.

The user resolved known gap about ingestion pipeline design and requested memory update about:
- Preferred name: certain-acumen-k5cc4
- Preference for a greeting before every session
- Change course ID from SE373 to SE374

The new pipeline design decisions and memory change request is processed, even though the agent decided ex parte that TXT files are chunked by paragraph, not "ingested whole" as described.

#### 64cf46a1

The user asked the agent about the ingestion pipeline disclosed "last session" and what is the course name. The agent correctly greeted the user from preference: Hello, certain-acumen-k5cc4, correctly answered the course name is SE374 and correctly retrieved the overall pipeline design. The agent suggested updating output/ documents to match memory's settled decisions.

The user agreed to the agent's suggestion and request to change course name back to SE373. The agent proceed. Work is not verified.

### Observation

The model used, minimax/minimax-m3.1-flash is a highly capable model with generally good sense and taste, even though it still occassionally suffer from context bias and does not generalise well enough (document-writing skill). It has successfully navigated the agent environment to support the user's needs. Above all, it successfully utilised the memory system to the user's advantage with good memory discipline and organisation.
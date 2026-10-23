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
   - `/profile.md` body and an index of active memory items are eagerly injected into the model's system prompt
   - Full body of topic memory is loaded on-demand via `memory_read`.
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

- Model used: `minimax/minimax-m3.1-flash` (428B MoE model with 23B activated per token)
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

> Note: Some bbservations are made with gateway-logged reasoning traces, not client snapshot or trace transcript.
>
> Gateway logs will not be available.

Evaluations across the featured traces (`921cd3b8`, `bbee898c`, `64cf46a1`) driven by `vercel/minimax/minimax-m3.1-flash` reveal strong architectural reasoning despite still being affected by context bias. Most importantly, the model exhibited good memory management discipline.

#### Overall performance

The model consistently reasoned from hard host constraints rather than generic defaults:

- In trace `921cd3b8` turn 1, when tasked with deploying an embedding model, relational database, vector database, object storage, and backend application on a 4 vCPU / 12 GB RAM footprint, the model systematically eliminated heavy alternatives in [workspace/output/vector-db-decision.md](workspace/output/vector-db-decision.md). It rejected Weaviate due to high baseline memory, Milvus Standalone due to daemon overhead (etcd, MinIO, and Milvus daemons competing for 4 vCPUs), Elasticsearch/OpenSearch due to Java Virtual Machine (JVM) heap pressure (3-5 GB), and pgvector because PostgreSQL `ts_rank` lacks true BM25 scoring. It selected Qdrant for its 0.5-1.5 GB memory range, native BM25 payload index, and scalar quantization levers (`memmap_threshold_kb`, `on_disk_payload`).
- In trace `921cd3b8` turn 2, upon receiving the BizCare Vietnamese specification, the model noted in reasoning step 7 that its earlier Turn 1 tenant-filtered shared collection violated the specification. It autonomously refactored [workspace/output/retrieval.py](workspace/output/retrieval.py) and [workspace/output/vector-db-decision.md](workspace/output/vector-db-decision.md) to dynamic per-workspace collections (`ws_<workspace_id>`) while retaining payload filtering as defense in depth.
- In trace `64cf46a1` turn 2, after drafting ingestion and re-indexing documentation, the model audited its generated files prior to completion, identified an unused parameter in `supersede_document`, a stale configuration comment, and an invalid cross-reference in [workspace/output/ingestion-pipeline.md](workspace/output/ingestion-pipeline.md), and executed full-file rewrites to resolve them.
- Operating without live Internet access, the model delivered a sensible multi-container [workspace/output/docker-compose.yml](workspace/output/docker-compose.yml), 590 lines of functional retrieval logic in [workspace/output/retrieval.py](workspace/output/retrieval.py), and 11 markdown specification documents using only workspace file and memory tools.

The model exhibited anchoring on earlier prompt context when writing general skills and processing contradictory directives:

- In trace `921cd3b8` turn 3, when generating a reusable, domain-agnostic [workspace/skills/document-writing/SKILL.md](workspace/skills/document-writing/SKILL.md), BizCare prompt context leaked directly into the style rules:
  - Rule 7 ([workspace/skills/document-writing/SKILL.md](workspace/skills/document-writing/SKILL.md) line 60): cites `"Recall@5 fell below the 0.85 threshold after the filter change"` (directly copied from BizCare spec Section 3.4.b).
  - Rule 10 ([workspace/skills/document-writing/SKILL.md](workspace/skills/document-writing/SKILL.md) line 66): cites `"The reviewer blocks the message"` (copied from BizCare spec Section 3.8 reviewer agent).
  - Rule 19 ([workspace/skills/document-writing/SKILL.md](workspace/skills/document-writing/SKILL.md) line 78): cites `"This holds for the 2 workspaces tested..."` (copied from BizCare sample workspaces `moc-mien-florist` and `iron-viet-fitness`).
- In trace `bbee898c` turn 2, the user instructed: `"txt files are ingested whole because no heuristic is decided to be the best way to fit an unstructured txt file."` Anchored to the earlier Vietnamese specification (Section 2.2.a: "TXT không chuẩn hóa hoặc chunk theo đoạn văn"), the model persisted its prior assumption in [memory/areas/se373-vector-db-selection.md](memory/areas/se373-vector-db-selection.md) (`"txt by paragraph (proposal, unvalidated)"`) and in [workspace/output/ingestion-pipeline.md](workspace/output/ingestion-pipeline.md).
- In trace `bbee898c` turn 1, the model recognized in reasoning that passing `score_threshold` to a Reciprocal Rank Fusion (RRF) query was invalid because RRF yields rank-based scores (~0.016-0.03) incomparable to cosine thresholds. However, when refactoring [workspace/output/retrieval.py](workspace/output/retrieval.py) in trace `64cf46a1` turn 2 line 391, it retained `score_threshold=score_threshold` inside `query_points(query=models.FusionQuery(fusion=fusion))`.

#### Tool resilience

- In trace `921cd3b8` turn 3 (step 19) and trace `64cf46a1` turn 2 (step 20), the model attempted to invoke a non-existent `edit_file` tool. After receiving `Error: edit_file is not a valid tool`, the model did not fail or loop; it recorded that no line-edit tool existed, pivoted immediately to `write_file`, and completed the necessary file updates.

#### Memory lifecycle management

The model demonstrated strong memory hygiene across multi-turn and cross-session interactions:

- Across 27 memory operations in the three featured traces, the model maintained the two-layer memory model:
  - restricting the root bucket `/` to `profile.md`
  - organizing topics and areas into distinct buckets
  - omitting markdown headings from memory bodies, and
  - adhering to the 300-character description limit.
- In every new session (`921cd3b8` turn 1, `bbee898c` turn 1, and `64cf46a1` turn 1), the model's initial tool call was `memory_read` on `profile` or `memory_list` before formulating user-facing output.
- When the course ID was changed from SE373 to SE374 in `bbee898c`, the model created `se374-*` keys and invoked `memory_delete` on obsolete `se373-*` files to prevent stale states. When reverted to SE373 in `64cf46a1`, it removed `se374-*` keys and logged an explicit observation entry in [memory/profile.md](memory/profile.md) line 10.

#### Execution efficiency

Gateway session telemetry across the three featured traces:

- The model completed 69 requests with 414,014 input tokens, 2,409,525 cached tokens (85.3% prompt cache hit rate across multi-turn dialogues), 45,298 reasoning tokens, and 90,020 completion tokens with 92 tool calls, totaling $0.1796 across three sessions.
- The model committed 21,503 reasoning tokens (29.3% of generated tokens) in `921cd3b8` to synthesize complex architectural tradeoffs, and 20,732 reasoning tokens (38.0% of generated tokens) in `64cf46a1` to audit cross-references and verify state reconciliation across workspace documents.

### Conclusion

While success may have been depended on MiniMax-M3.1-Flash as a capable model, the demonstration and tests proved that the memory system is implemented correct, functional, and effective.
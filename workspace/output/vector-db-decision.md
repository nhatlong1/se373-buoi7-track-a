# Vector Database Decision Record — SE373 Final Project (BizCare)

**Context:** Single host, 4 vCPU / 12 GB RAM. Must co-host: Python backend, relational DB, vector DB, object storage, and a small text embedding model.
**Requirements:** strong per-workspace data isolation, BM25-equivalent full-text search *alongside* vector similarity, vector search and full-text search independently callable, hybrid search preferred but optional, client-server (not embedded), low memory footprint.
**Spec source:** `output/project-spec-en.md` (BizCare, SE373 Group 02, 18/10/2026).

---

## 1. Recommendation

**Primary: Qdrant (self-hosted, client-server).**

**Lightweight alternative: Redis Stack (RediSearch + vector sets)** if you want the absolute smallest footprint and can accept a less mature vector API.

**Fallback: pgvector** if you are willing to drop the "separate vector DB server" preference — it is by far the cheapest option, but it does not give you BM25.

---

## 2. Why Qdrant fits this host

| Requirement | How Qdrant satisfies it |
|---|---|
| Client-server | Native REST (`:6333`) + gRPC (`:6334`) server; official Python client over gRPC. |
| Vector similarity | HNSW index, cosine / dot / Euclid. |
| BM25 full-text | Payload **text index** (BM25 scoring) on any text field, independent of the vector index. |
| Independent vector vs. FTS | Two separate query paths: `VectorQuery` and `MatchText`. Neither requires the other. |
| Hybrid search | `FusionQuery` with RRF (or DBSF) over two `Prefetch` branches. |
| Per-workspace isolation | One collection per workspace (spec 2.2.b) + a `workspace_id` payload filter on every query. |
| Low memory | int8 scalar / binary / product quantization, `on_disk` vectors, `on_disk_payload`, mmap'd segments, `memmap_threshold_kb`. |
| License | Apache 2.0 — no open-core feature gating for the features above. |

### Why not the others

- **Weaviate** — best-in-class built-in multi-tenancy and BM25+vector hybrid, but it is the heaviest of the realistic options (plan for 2–4 GB RSS). On a 12 GB shared host with Postgres, MinIO, and an embedding model loaded, it leaves too little headroom. Its Go runtime + segment cache does not release memory back to the OS as aggressively.
- **Milvus (standalone)** — requires etcd **and** MinIO **and** the Milvus process. Three extra services on 4 vCPU is not viable here. (Milvus Lite is embedded and Python-only, so it fails the client-server requirement.)
- **Elasticsearch / OpenSearch** — superb BM25 and RRF hybrid, but JVM heap + off-heap Lucene structures typically cost 3–5 GB. It is a search engine being used as a vector DB; the memory cost is not justified at this scale.
- **Chroma** — client-server mode exists but is not production-grade, has no BM25, and holds the index in the client process.
- **pgvector** — cheapest by far (no extra process), but Postgres FTS uses `ts_rank`, which is *not* BM25, and hybrid ranking must be hand-rolled in SQL. It also conflicts with your stated client-server preference.
- **LanceDB / txtai** — embedded only. Disqualified.
- **Typesense** — good BM25, but the index is fully in-memory and vector support is comparatively recent.

---

## 3. Memory budget (12 GB host)

Assumed: ~1M chunks × 384 dims, single-node, Docker.

| Component | Typical RSS | Tuning lever |
|---|---|---|
| OS + Docker daemon | 0.5 – 1.0 GB | — |
| FastAPI backend + int8 embedding model | 0.5 – 0.9 GB | ONNX Runtime, int8 weights |
| PostgreSQL 16 | 1.5 – 2.5 GB | `shared_buffers = 1GB` |
| MinIO (single node) | 0.3 – 0.6 GB | small disk, no erasure coding |
| **Qdrant** (on-disk payload, int8 quant) | **0.5 – 1.5 GB** | quantization + `on_disk` |
| **Total** | **3.3 – 6.5 GB** | ~5 GB headroom |

Swap the Qdrant row to compare:

| Vector DB | Vector DB RSS | Total stack | Verdict |
|---|---|---|---|
| Qdrant | 0.5 – 1.5 GB | 3.3 – 6.5 GB | Comfortable |
| Redis Stack | 0.3 – 1.0 GB | 3.1 – 6.0 GB | Comfortable, least mature vector API |
| Weaviate | 2.0 – 4.0 GB | 4.8 – 8.5 GB | Tight but workable |
| Elasticsearch / OpenSearch | 3.0 – 5.0 GB | 5.8 – 9.5 GB | Risky |
| Milvus standalone | 4.0 – 6.0 GB (+ etcd + MinIO) | 8.0 – 12.0 GB+ | Does not fit |

### 3.1 Per-workspace collections: the memory caveat

The spec (2.2.b) requires **one collection per workspace**. Qdrant allocates a minimum segment size per collection, so N collections cost more than one shared collection with N filters. With only 2 sample workspaces this is negligible. If the number of workspaces grows, options in order of preference:

1. Keep per-workspace collections but raise `memmap_threshold_kb` so small collections stay mmap'd on disk.
2. Use `shard_key_selector` with `workspace_id` as the shard key inside one collection — this gives the same logical isolation with one set of segments.
3. Fall back to a shared collection with a mandatory `workspace_id` filter (the design used in the earlier draft of `retrieval.py`).

Option 2 is the best of both worlds and is worth benchmarking before the demo.

---

## 4. Embedding model (keep it small)

| Model | Params | Dims | fp32 / int8 | Use when |
|---|---|---|---|---|
| `all-MiniLM-L6-v2` | 22.7 M | 384 | 90 MB / 23 MB | English-only corpus |
| `multilingual-e5-small` | 118 M | 384 | 470 MB / 120 MB | **Vietnamese / mixed-language corpus** |
| `paraphrase-multilingual-MiniLM-L12-v2` | 118 M | 384 | 470 MB / 120 MB | Multilingual, slightly stronger |

Recommendation for a VNUHCM project: **`multilingual-e5-small`**, int8-quantized, served via ONNX Runtime inside the backend process. E5 models need the `query:` / `passage:` prefix — bake that into your ingest and query helpers so it is never forgotten.

The corpus is Vietnamese (spec 1.4.1), so `multilingual-e5-small` is the right default. Note the spec also requires handling unaccented and abbreviated text (EV-INTENT-02); test whether the embedding model degrades on unaccented Vietnamese, and consider a text normalization step (add diacritics back) before embedding if recall suffers.

---

## 5. Isolation design (revised to match the spec)

The spec mandates **one collection per workspace** (2.2.b), so the earlier "one shared collection + tenant filter" design was replaced. The revised design has two layers of defence:

1. **Collection boundary** — `ws_<workspace_id>`. A query against the wrong collection returns nothing.
2. **Payload filter** — every query additionally pins `workspace_id` and excludes `status != active`.

Rules to enforce:

1. `workspace_id` is a `KEYWORD` payload field with an index.
2. The collection name is derived from the authenticated session, never from a request body. The agent has no ability to choose a different workspace (spec 2.2.b).
3. Every read path goes through a single wrapper that injects the filter. No raw client calls in route handlers.
4. Expired (`superseded`) documents are excluded at the **metadata filter step**, not deferred to ranking (spec 2.2.b).
5. The relevance score threshold is set by the business owner in the agent config; chunks below it must not be used to answer (spec 2.2.b, 3.4.a).
6. Regression test: insert a doc in workspace A, assert workspace B's vector, FTS, and hybrid queries all return zero hits.

---

## 6. Query patterns

See `output/retrieval.py` for the full implementation. Summary:

- **Vector only** → `query_points(query=VectorQuery(vector=v), query_filter=workspace_filter)`
- **Full-text only** → `query_points(query=MatchText(text=q, field="body"), query_filter=workspace_filter)`
- **Hybrid** → `query_points(prefetch=[VectorQuery(...), MatchText(...)], query=FusionQuery(fusion=Fusion.RRF))`

All three are independently callable; hybrid is a composition of the other two, not a separate subsystem. The spec (2.2.b) requires the combined form for production retrieval; the other two remain available for the evaluation harness and for debugging.

---

## 7. Deployment checklist

1. `docker compose up -d` with the provided `output/docker-compose.yml` (mem limits are set per service to enforce the budget).
2. Create the collection with the text index and int8 quantization (see `retrieval.py::ensure_collection`).
3. Ingest with `workspace_id` stamped server-side and the full spec metadata set.
4. Smoke-test: vector-only, FTS-only, hybrid, the cross-workspace isolation test, and the superseded-exclusion test.
5. Monitor `docker stats` — if Qdrant exceeds ~2 GB, enable `on_disk_payload` and re-index with product quantization.

---

## 8. Decision log

- **Chose Qdrant over Weaviate** — memory headroom on a 12 GB shared host outweighs Weaviate's superior first-class multi-tenancy, since Qdrant covers isolation via per-workspace collections.
- **Chose Qdrant over Elasticsearch** — BM25 quality is not the bottleneck at this data scale; RAM is.
- **Kept a separate vector server** (per stated preference) rather than pgvector, but documented pgvector as the fallback if the host turns out to be smaller than specified.
- **Revised isolation design from shared-collection to per-workspace collections** after reading the spec (2.2.b), which explicitly requires a collection per workspace and forbids cross-collection queries.
- **Kept `multilingual-e5-small`** rather than an English-only model, because the corpus and all test scenarios are Vietnamese.

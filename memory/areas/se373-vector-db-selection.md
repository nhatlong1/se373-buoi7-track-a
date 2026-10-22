---
name: "se373-vector-db-selection"
description: "SE373 BizCare: vector DB decision = Qdrant; per-workspace collections, memory budget, isolation design, embedding model choice"
---

- Decision: Qdrant (self-hosted, client-server) as the vector DB for the SE373 BizCare final project.
- Chosen over Weaviate (too heavy, 2-4 GB RSS), Milvus standalone (needs etcd + MinIO, does not fit 4 vCPU), Elasticsearch/OpenSearch (JVM + Lucene, 3-5 GB), Chroma (no BM25, not production-grade), pgvector (no BM25, ts_rank is not BM25, conflicts with client-server preference), LanceDB/txtai (embedded only).
- Fallback if the host is smaller than specified: pgvector. Lightweight alternative: Redis Stack (RediSearch + vector sets).
- Qdrant satisfies requirements via: payload text index (BM25) independent of the HNSW vector index; VectorQuery and MatchText as separate query paths; FusionQuery with RRF for the combined retrieval the spec requires.
- Isolation design (REVISED to match spec 2.2.b): one collection per workspace, named ws_<workspace_id>, PLUS a mandatory workspace_id payload filter on every query. Two layers of defence. workspace_id derived from the authenticated session, never from a request body; agent cannot choose a different workspace.
- Expired/superseded documents excluded at the metadata filter step (not deferred to ranking), per spec 2.2.b.
- Business-owner-set relevance score threshold applied at query time; chunks below it must not be used to answer.
- Memory budget on the 12 GB host: OS+Docker 0.5-1.0, FastAPI+int8 embedding model 0.5-0.9, Postgres 16 1.5-2.5, MinIO 0.3-0.6, Qdrant 0.5-1.5. Total 3.3-6.5 GB.
- Qdrant memory levers: int8 scalar quantization, on_disk_payload, memmap_threshold_kb, max_search_threads=2.
- Per-workspace collection caveat: N collections cost more than one shared collection with N filters (min segment size per collection). Negligible at 2 workspaces. If workspace count grows, prefer shard_key_selector with workspace_id as shard key inside one collection.
- Embedding model: multilingual-e5-small (384 dims, int8 ~120 MB) - corpus and all test scenarios are Vietnamese. all-MiniLM-L6-v2 only if English-only. E5 needs query:/passage: prefixes.
- Open risk to test: EV-INTENT-02 requires handling unaccented/abbreviated Vietnamese; check embedding recall on unaccented text, consider diacritic restoration before embedding.
- Artifacts: output/project-spec-en.md (full English translation), output/vector-db-decision.md, output/docker-compose.yml, output/qdrant-config.yaml, output/retrieval.py.

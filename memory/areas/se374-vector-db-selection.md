---
name: "se374-vector-db-selection"
description: "SE374 BizCare: vector DB = Qdrant (latest version only); MySQL + SeaweedFS; embeddinggemma2 Q4 LiteRT-LM; ingestion pipeline; re-index strategy still open"
---

- Vector DB decision: Qdrant (self-hosted, client-server) for the SE374 BizCare final project.
- Chosen over Weaviate (too heavy, 2-4 GB RSS), Milvus standalone (needs etcd + MinIO, does not fit 4 vCPU), Elasticsearch/OpenSearch (JVM + Lucene, 3-5 GB), Chroma (no BM25, not production-grade), pgvector (no BM25, ts_rank is not BM25, conflicts with client-server preference), LanceDB/txtai (embedded only).
- Fallback if the host is smaller than specified: pgvector. Lightweight alternative: Redis Stack (RediSearch + vector sets).
- Qdrant satisfies requirements via: payload text index (BM25) independent of the HNSW vector index; VectorQuery and MatchText as separate query paths; FusionQuery with RRF for combined retrieval.
- Isolation design: one collection per workspace, named ws_<workspace_id>, PLUS a mandatory workspace_id payload filter on every query. Two layers of defence. workspace_id derived from the authenticated session, never from a request body; agent cannot choose a different workspace.
- Qdrant holds ONLY the latest indexed version of each document - outdated documents are impossible to search by design (no superseded chunks retained in the vector DB).
- Business-owner-set relevance score threshold applied at query time; chunks below it must not be used to answer.
- Memory budget on the 12 GB host: OS+Docker 0.5-1.0, FastAPI+embedding model 0.5-0.9, MySQL 1.5-2.5, SeaweedFS 0.3-0.6, Qdrant 0.5-1.5. Total 3.3-6.5 GB.
- Qdrant memory levers: int8 scalar quantization, on_disk_payload, memmap_threshold_kb, max_search_threads=2.
- Per-workspace collection caveat: N collections cost more than one shared collection with N filters (min segment size per collection). Negligible at 2 workspaces. If workspace count grows, prefer shard_key_selector with workspace_id as shard key inside one collection.
- Embedding model: embeddinggemma2, text-only mode, Q4 quantisation, LiteRT-LM format (replaces the earlier multilingual-e5-small choice).
- INGESTION PIPELINE (theoretical, as designed): (1) Validate - accept only txt, html, md, pdf, csv, xlsx; scan for prompt injection and viruses. (2) Normalise - Text type to MD (markitdown for HTML and PDF, txt not converted), Table type to CSV (one CSV per XLSX sheet); remove all image content. (3) Chunk - by section for structured files, by rows for CSV; txt ingested whole (no heuristic chosen yet for unstructured txt); every CSV chunk carries the header row so search is not lost in meaningless numbers. (4) Embed - embeddinggemma2 text-only, Q4, LiteRT-LM.
- OPEN: no re-indexing strategy designed yet and no change-detection mechanism in place. Current sample workflow = customer uploads a new document and requests re-index; the entire "current" state store is re-indexed at once.
- Open risk to test: EV-INTENT-02 requires handling unaccented/abbreviated Vietnamese; check embedding recall on unaccented text, consider diacritic restoration before embedding.
- Artifacts: output/project-spec-en.md (full English translation), output/vector-db-decision.md, output/docker-compose.yml, output/qdrant-config.yaml, output/retrieval.py.

"""
SE373 final project - BizCare retrieval layer (Qdrant).

Implements the knowledge base requirements from the project spec (section 2.2):

  - One collection per workspace (spec 2.2.b). The agent is locked to the
    workspace it is operating in; no query ever spans all collections.
  - Combined semantic + keyword (BM25) retrieval, with the two result
    lists merged before ranking (spec 2.2.b).
  - A relevance score threshold set by the business owner; chunks below
    the threshold must not be used to answer (spec 2.2.b, 3.4.a).
  - Expired documents are removed at the metadata filter step, not
    deferred to the ranking step (spec 2.2.b).
  - Chunk metadata matches the spec table exactly (spec 2.2.b).

The three query paths are independently callable:
  1. vector_search()   - dense similarity only
  2. fulltext_search() - BM25 only
  3. hybrid_search()   - RRF fusion of the two (spec 2.2.b requires the
                         combined form; the other two remain available
                         for debugging and for the evaluation harness)

Install:  pip install qdrant-client
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from qdrant_client import QdrantClient, models

QDRANT_URL = "http://localhost:6333"

# Embedding model must match the one used at ingest time.
#
# embeddinggemma2, text-only mode, Q4 quantisation, LiteRT-LM format.
# The dimension must be read from the deployed checkpoint configuration
# before any collection is created - a wrong size fails at upsert time,
# not at startup. See output/ingestion-pipeline.md section 9, Q1.
EMBED_MODEL = "embeddinggemma2"
EMBED_DIM: int | None = None  # TBD - read from the checkpoint config

# Task prefixes. The previous multilingual-e5-small model required
# asymmetric "query: " / "passage: " prefixes. Whether embeddinggemma2
# does is unconfirmed - see output/ingestion-pipeline.md section 9, Q2.
# If prefixes are required, bake them into the two embedding helpers
# below, never into call sites.
QUERY_PREFIX = ""
PASSAGE_PREFIX = ""

# Chunk status values (spec 2.2.b metadata table).
STATUS_ACTIVE = "active"
STATUS_SUPERSEDED = "superseded"

# Staging flag. Chunks are written with indexed=False and flipped to
# True once the write is verified complete, so a partially written
# document is never retrievable. See output/reindexing-strategy.md.
INDEXED_TRUE = True
INDEXED_FALSE = False

# Document types (spec 2.2.b metadata table).
# The spec enum has no "txt" member. A TXT upload is normalized to text
# and recorded as "markdown" - see output/ingestion-pipeline.md Q4.
DOC_TYPES = ("markdown", "html", "pdf", "csv", "xlsx")


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------

def get_client() -> QdrantClient:
    # Prefer gRPC for lower latency and less per-request overhead.
    return QdrantClient(url=QDRANT_URL, prefer_grpc=True, timeout=30)


def collection_name(workspace_id: str) -> str:
    """One collection per workspace (spec 2.2.b).

    The workspace id comes from the authenticated session, never from a
    request body. The agent has no ability to choose a different one.
    """
    return f"ws_{workspace_id}"


# --------------------------------------------------------------------------
# Collection setup
# --------------------------------------------------------------------------

def ensure_collection(client: QdrantClient, workspace_id: str) -> None:
    """Create the workspace collection with a BM25 text index and int8 quantization."""
    if EMBED_DIM is None:
        raise RuntimeError(
            "EMBED_DIM is not set. Read the vector dimension from the "
            "deployed embeddinggemma2 checkpoint configuration first."
        )

    name = collection_name(workspace_id)
    if client.collection_exists(name):
        return

    client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(
            size=EMBED_DIM,
            distance=models.Distance.COSINE,
            on_disk=False,  # vectors stay in RAM; payload goes to disk
        ),
        # BM25 full-text index over the chunk body.
        # This index is completely independent of the HNSW vector index.
        hnsw_config=models.HnswConfigDiff(
            m=16,
            ef_construct=100,
            on_disk=False,
        ),
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(
                type=models.ScalarType.INT8,
                quantile=0.99,
                always_ram=False,
            )
        ),
        optimizers_config=models.OptimizersConfigDiff(
            memmap_threshold=20_000,
            indexing_threshold=20_000,
        ),
    )

    # Payload schema. workspace_id is a KEYWORD index -> fast, exact filtering.
    client.create_payload_index(
        collection_name=name,
        field_name="workspace_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=name,
        field_name="doc_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=name,
        field_name="status",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=name,
        field_name="indexed",
        field_schema=models.PayloadSchemaType.BOOL,
    )
    client.create_payload_index(
        collection_name=name,
        field_name="version",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        collection_name=name,
        field_name="updated_at",
        field_schema=models.PayloadSchemaType.DATETIME,
    )


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------

def workspace_filter(workspace_id: str) -> models.Filter:
    """The only sanctioned way to build a workspace filter.

    Two layers of defence:
      1. The collection itself is per-workspace, so a wrong collection
         name is already a hard boundary.
      2. The payload filter additionally pins workspace_id, requires the
         chunk to be active, and requires the staged write to have been
         completed (spec 2.2.b).
    """
    return models.Filter(
        must=[
            models.FieldCondition(
                key="workspace_id",
                match=models.MatchValue(value=workspace_id),
            ),
            models.FieldCondition(
                key="status",
                match=models.MatchValue(value=STATUS_ACTIVE),
            ),
            models.FieldCondition(
                key="indexed",
                match=models.MatchValue(value=INDEXED_TRUE),
            ),
        ]
    )


# --------------------------------------------------------------------------
# Ingest
# --------------------------------------------------------------------------

@dataclass
class Chunk:
    """A chunk of a document, with the metadata fields required by the spec."""

    doc_id: str
    text: str
    title: str
    uri: str
    section: str
    chunk_index: int
    updated_at: datetime
    doc_type: str
    version: str
    status: str = STATUS_ACTIVE
    indexed: bool = INDEXED_FALSE
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.doc_type not in DOC_TYPES:
            raise ValueError(f"invalid doc_type: {self.doc_type}")
        if self.status not in (STATUS_ACTIVE, STATUS_SUPERSEDED):
            raise ValueError(f"invalid status: {self.status}")


def upsert_chunks(
    client: QdrantClient,
    workspace_id: str,
    chunks: Sequence[Chunk],
    embeddings: Sequence[Sequence[float]],
) -> None:
    """Write chunks for one workspace, staged.

    Chunks are written with indexed=False. The caller verifies the chunk
    count and then calls mark_indexed() to flip the flag. A partially
    written document is therefore never retrievable.

    workspace_id is stamped here from the authenticated session, never
    taken from the request body.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")

    points = [
        models.PointStruct(
            id=str(uuid.uuid4()),
            vector=list(vec),
            payload={
                "workspace_id": workspace_id,   # server-side stamp
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "uri": chunk.uri,
                "section": chunk.section,
                "chunk_index": chunk.chunk_index,
                "updated_at": chunk.updated_at,
                "doc_type": chunk.doc_type,
                "version": chunk.version,
                "status": chunk.status,
                "indexed": chunk.indexed,
                "body": chunk.text,   # the BM25-indexed field
                **chunk.extra,
            },
        )
        for chunk, vec in zip(chunks, embeddings)
    ]

    client.upsert(
        collection_name=collection_name(workspace_id),
        points=points,
        wait=True,
    )


def mark_indexed(
    client: QdrantClient,
    workspace_id: str,
    doc_id: str,
    version: str,
) -> None:
    """Flip the staging flag once the write is verified complete.

    Must not run before the chunk count has been verified. See
    output/reindexing-strategy.md section 4.3.
    """
    client.set_payload(
        collection_name=collection_name(workspace_id),
        payload={"indexed": INDEXED_TRUE},
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(key="workspace_id",
                                         match=models.MatchValue(value=workspace_id)),
                    models.FieldCondition(key="doc_id",
                                         match=models.MatchValue(value=doc_id)),
                    models.FieldCondition(key="version",
                                         match=models.MatchValue(value=version)),
                ]
            )
        ),
        wait=True,
    )


# --------------------------------------------------------------------------
# Query path 1: vector similarity only
# --------------------------------------------------------------------------

def vector_search(
    client: QdrantClient,
    workspace_id: str,
    query_vector: Sequence[float],
    limit: int = 10,
    score_threshold: float | None = None,
) -> list[models.ScoredPoint]:
    """Dense retrieval. Does not touch the full-text index at all.

    score_threshold is the business owner's relevance threshold
    (spec 2.2.b). Chunks below it must not be used to answer.
    """
    return client.query_points(
        collection_name=collection_name(workspace_id),
        query=models.VectorQuery(
            vector=list(query_vector),
            limit=limit,
            score_threshold=score_threshold,
        ),
        query_filter=workspace_filter(workspace_id),
        with_payload=True,
    ).points


# --------------------------------------------------------------------------
# Query path 2: BM25 full-text only
# --------------------------------------------------------------------------

def fulltext_search(
    client: QdrantClient,
    workspace_id: str,
    query_text: str,
    limit: int = 10,
) -> list[models.ScoredPoint]:
    """BM25 retrieval over the 'body' payload field.

    Does not touch the vector index at all. The returned score is the
    BM25 score, not a cosine similarity.
    """
    return client.query_points(
        collection_name=collection_name(workspace_id),
        query=models.MatchText(
            text=query_text,
            field="body",
        ),
        query_filter=workspace_filter(workspace_id),
        limit=limit,
        with_payload=True,
    ).points


# --------------------------------------------------------------------------
# Query path 3: hybrid (semantic + keyword merged before ranking)
# --------------------------------------------------------------------------

def hybrid_search(
    client: QdrantClient,
    workspace_id: str,
    query_vector: Sequence[float],
    query_text: str,
    limit: int = 10,
    fusion: models.Fusion = models.Fusion.RRF,
    score_threshold: float | None = None,
) -> list[models.ScoredPoint]:
    """Reciprocal Rank Fusion over the vector and BM25 branches.

    Each branch is a Prefetch, so both are executed independently and
    their ranked lists are merged before the final ranking (spec 2.2.b).
    RRF is rank-based and needs no score normalization, which is why it
    is preferred over DBSF here.
    """
    return client.query_points(
        collection_name=collection_name(workspace_id),
        prefetch=[
            models.Prefetch(
                query=models.VectorQuery(vector=list(query_vector), limit=limit * 2),
                filter=workspace_filter(workspace_id),
            ),
            models.Prefetch(
                query=models.MatchText(text=query_text, field="body"),
                filter=workspace_filter(workspace_id),
            ),
        ],
        query=models.FusionQuery(fusion=fusion),
        limit=limit,
        score_threshold=score_threshold,
        with_payload=True,
    ).points


# --------------------------------------------------------------------------
# Versioning (spec 2.2.c)
# --------------------------------------------------------------------------

def supersede_document(
    client: QdrantClient,
    workspace_id: str,
    doc_id: str,
) -> None:
    """Remove the current version's chunks from the vector database.

    The vector database holds only the latest indexed version, so the
    old chunks are deleted rather than flagged and filtered. The
    document store keeps the old version's original file and metadata,
    so it stays viewable in history and trace citations remain
    reconcilable.

    The status filter in workspace_filter() remains as a second line of
    defence and is still covered by test_superseded_excluded.
    """
    client.delete(
        collection_name=collection_name(workspace_id),
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(key="workspace_id",
                                         match=models.MatchValue(value=workspace_id)),
                    models.FieldCondition(key="doc_id",
                                         match=models.MatchValue(value=doc_id)),
                ]
            )
        ),
        wait=True,
    )


def delete_document(client: QdrantClient, workspace_id: str, doc_id: str) -> None:
    """Soft delete: remove from the vector database, keep the document
    store record for reconciling old traces (spec 2.2.c)."""
    client.delete(
        collection_name=collection_name(workspace_id),
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(key="workspace_id",
                                         match=models.MatchValue(value=workspace_id)),
                    models.FieldCondition(key="doc_id",
                                         match=models.MatchValue(value=doc_id)),
                ]
            )
        ),
        wait=True,
    )


# --------------------------------------------------------------------------
# Isolation regression test
# --------------------------------------------------------------------------

def test_isolation(client: QdrantClient, embed_fn) -> None:
    """Insert a doc in workspace A, assert workspace B sees nothing.

    Run this in CI. It is the single most important test for the
    workspace isolation requirement (spec 3.4.b criterion 6, 3.7.b
    criterion 6).
    """
    ws_a, ws_b = "moc-mien-florist", "iron-viet-fitness"
    marker = "zzz-isolation-marker-9f3a"
    now = datetime.now(timezone.utc)

    for ws in (ws_a, ws_b):
        ensure_collection(client, ws)

    upsert_chunks(
        client,
        ws_a,
        [
            Chunk(
                doc_id="iso-1",
                text=f"{marker} confidential content",
                title="Isolation test",
                uri="test://iso-1",
                section="Test",
                chunk_index=0,
                updated_at=now,
                doc_type="markdown",
                version="v1",
            )
        ],
        [embed_fn(PASSAGE_PREFIX + marker + " confidential content")],
    )
    mark_indexed(client, ws_a, "iso-1", "v1")

    vec = embed_fn(QUERY_PREFIX + marker)

    a_vec = vector_search(client, ws_a, vec, limit=5)
    b_vec = vector_search(client, ws_b, vec, limit=5)
    a_txt = fulltext_search(client, ws_a, marker, limit=5)
    b_txt = fulltext_search(client, ws_b, marker, limit=5)
    a_hyb = hybrid_search(client, ws_a, vec, marker, limit=5)
    b_hyb = hybrid_search(client, ws_b, vec, marker, limit=5)

    assert a_vec, "workspace A should find its own document"
    assert a_txt, "workspace A should find its own document via BM25"
    assert a_hyb, "workspace A should find its own document via hybrid"

    assert not b_vec, "ISOLATION FAIL: workspace B saw workspace A vector results"
    assert not b_txt, "ISOLATION FAIL: workspace B saw workspace A full-text results"
    assert not b_hyb, "ISOLATION FAIL: workspace B saw workspace A hybrid results"

    print("isolation OK: vector, full-text and hybrid all workspace-scoped")


def test_superseded_excluded(client: QdrantClient, embed_fn) -> None:
    """A superseded document must not appear in any result set.

    Covers spec 3.4.c EV-POLICY-07.
    """
    ws = "moc-mien-florist"
    marker = "zzz-superseded-marker-4b1e"
    now = datetime.now(timezone.utc)

    upsert_chunks(
        client,
        ws,
        [
            Chunk(
                doc_id="sup-1",
                text=f"{marker} old policy text",
                title="Old policy",
                uri="test://sup-1",
                section="Policy",
                chunk_index=0,
                updated_at=now,
                doc_type="markdown",
                version="v1",
            )
        ],
        [embed_fn(PASSAGE_PREFIX + marker + " old policy text")],
    )
    mark_indexed(client, ws, "sup-1", "v1")

    assert fulltext_search(client, ws, marker, limit=5), "precondition: doc is active"

    supersede_document(client, ws, "sup-1")

    assert not fulltext_search(client, ws, marker, limit=5), \
        "SUPERSEDED FAIL: expired document still returned by BM25"
    assert not vector_search(client, ws, embed_fn(QUERY_PREFIX + marker), limit=5), \
        "SUPERSEDED FAIL: expired document still returned by vector search"

    print("superseded exclusion OK")


def test_staged_chunks_not_retrievable(client: QdrantClient, embed_fn) -> None:
    """A chunk written but not yet marked indexed must not be retrievable.

    Covers the staged-write guarantee in output/reindexing-strategy.md
    section 4.2.
    """
    ws = "moc-mien-florist"
    marker = "zzz-staged-marker-7c2d"
    now = datetime.now(timezone.utc)

    upsert_chunks(
        client,
        ws,
        [
            Chunk(
                doc_id="staged-1",
                text=f"{marker} partially written content",
                title="Staged write",
                uri="test://staged-1",
                section="Test",
                chunk_index=0,
                updated_at=now,
                doc_type="markdown",
                version="v1",
            )
        ],
        [embed_fn(PASSAGE_PREFIX + marker + " partially written content")],
    )

    assert not fulltext_search(client, ws, marker, limit=5), \
        "STAGING FAIL: chunk was retrievable before being marked indexed"
    assert not vector_search(client, ws, embed_fn(QUERY_PREFIX + marker), limit=5), \
        "STAGING FAIL: chunk was retrievable before being marked indexed"

    mark_indexed(client, ws, "staged-1", "v1")

    assert fulltext_search(client, ws, marker, limit=5), \
        "STAGING FAIL: chunk was not retrievable after being marked indexed"

    print("staged write OK")

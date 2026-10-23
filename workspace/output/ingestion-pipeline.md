# BizCare Ingestion and Indexing Pipeline

| Field | Value |
|---|---|
| Author | SE373 Group 02 |
| Date | 2026-10-23 |
| Version | v1.0 |
| Status | Draft |
| Owner | SE373 Group 02 |
| Reviewers | TBD |
| Applies to | BizCare final project, knowledge base subsystem |
| Related documents | `output/project-spec-en.md` (spec), `output/vector-db-decision.md` (Qdrant decision), `output/reindexing-strategy.md` (re-index design), `output/retrieval.py` (retrieval layer) |

## 1. Introduction

### 1.1 Purpose

This document defines how an uploaded document becomes searchable content in a BizCare workspace, so that an implementer can build the pipeline and a reviewer can check it against the project specification.

### 1.2 Scope

Covered: the seven pipeline stages, format-specific normalization and chunking rules, chunk metadata, the embedding model, the index status model exposed to the Portal, and the boundary with the re-indexing design.

Not covered here: retrieval query construction (see `output/retrieval.py`), the re-index run algorithm and its failure handling (see `output/reindexing-strategy.md`), and the agent workflow that consumes retrieved passages (spec §4.1).

### 1.3 Design drivers

| Driver | Type | Priority | Implication |
|---|---|---|---|
| Spec §2.2.a fixes the pipeline stages and the status model | Normative | Must | Stage order and the `pending → indexing → indexed` / `failed` status vocabulary follow the spec exactly |
| Spec §3.4.b requires new policy content to be live after at most one re-index run | Normative | Must | Re-index is scoped to the changed document, not the whole workspace |
| Corpus is Vietnamese, including unaccented and abbreviated text (spec §1.4.1) | Quality | Must | Normalization must not corrupt Vietnamese text; embedding recall on unaccented input must be measured, not assumed |
| Single host, 4 vCPU / 12 GB RAM | Resource | Must | Parsing, chunking and embedding run in-process; no heavyweight document service |
| Per-workspace isolation (spec §2.2.b) | Security | Must | `workspace_id` is stamped server-side; one collection per workspace |
| A wrong answer is worse than a missing answer | Quality | Should | During re-index a document is absent rather than stale; staged writes keep partial content invisible |
| Documents may contain instructions aimed at the agent (spec §3.4.c EV-POLICY-08) | Security | Must | Retrieved passages are treated as untrusted data; pre-ingest scanning is defence in depth, not the primary control |

### 1.4 Constraints

- Supported formats are fixed by spec §2.2.a: TXT, Markdown, HTML, PDF, CSV, XLSX.
- The document store is the source of truth for originals, versions and effective status (spec §2.2.c). The vector database is the source of truth for search only.
- The vector database holds only the latest indexed version of each document. Superseded content is not retained there.
- All sample data is synthetic and small scale (spec §9). The two sample workspaces hold 29 and 20 documents.

### 1.5 Glossary

| Term | Meaning |
|---|---|
| Document | A logical knowledge item owned by one workspace, identified by `doc_id` |
| Version | One revision of a document's content, identified by `doc_id` + `version` |
| Effective version | The version currently returned by search for a document |
| Chunk | A retrievable unit of text with metadata, produced by the chunking stage |
| Normalized text | The canonical text form produced from an uploaded file, used for hashing and chunking |
| Source hash | SHA-256 of the uploaded file bytes; detects duplicate uploads |
| Content hash | SHA-256 of the normalized text; detects a changed document |
| Re-index run | One pass that makes a changed document's new content live |
| Collection | The Qdrant collection for one workspace, named `ws_<workspace_id>` |

## 2. Pipeline overview

### 2.1 Stage flow

```
   upload / edit
         │
         ▼
   ┌───────────────┐   reject: unsupported format, empty, duplicate
   │  1. Validate  │──────────────────────────────────────────▶ failed
   └───────┬───────┘
           ▼
   ┌───────────────┐   text → markdown, tables → csv, images dropped
   │  2. Normalize │
   └───────┬───────┘
           ▼
   ┌───────────────┐   section-aware for text, row-wise for tables
   │    3. Chunk   │
   └───────┬───────┘
           ▼
   ┌───────────────┐   embeddinggemma2, text-only, Q4, LiteRT-LM
   │    4. Embed   │
   └───────┬───────┘
           ▼
   ┌───────────────┐   staged write into ws_<workspace_id>
   │    5. Index   │
   └───────┬───────┘
           ▼
   ┌───────────────┐   old version superseded, new version effective
   │ 6. Mark as    │
   │   effective   │
   └───────┬───────┘
           ▼
   ┌───────────────┐   pending → indexing → indexed | failed
   │ 7. Report     │
   │    status     │
   └───────────────┘
```

### 2.2 Stage summary

| # | Stage | Input | Output | Failure recorded as |
|---|---|---|---|---|
| 1 | Validate | Uploaded file bytes | Accepted file + source hash | `failed` with reason |
| 2 | Normalize | Accepted file | Normalized text + content hash | `failed` with reason |
| 3 | Chunk | Normalized text | Ordered chunk list with section paths | `failed` with reason |
| 4 | Embed | Chunk list | One vector per chunk | `failed` with reason |
| 5 | Index | Chunks + vectors | Chunks written to the workspace collection | `failed` with reason |
| 6 | Mark as effective | New version indexed | Old version superseded, new version effective | `failed` with reason |
| 7 | Report status | Stage outcomes | `pending` / `indexing` / `indexed` / `failed` | — |

### 2.3 Status model

Spec §2.2.a step 6 and §2.2.c require the Portal to display indexing progress and an error reason on failure.

| Status | Meaning | Owner-visible | Retryable |
|---|---|---|---|
| `pending` | Accepted, not yet started | Yes | No — it will start |
| `indexing` | A stage is running | Yes | No — it is running |
| `indexed` | The version is effective and searchable | Yes | No |
| `failed` | A stage failed; the reason is recorded | Yes, with reason | Yes — the owner can retry |

A failed run never leaves a partially indexed document visible. See `output/reindexing-strategy.md` §4.2.

## 3. Stage specifications

### 3.1 Stage 1 — Validate

| Check | Rule | On failure |
|---|---|---|
| Format | Extension and content type must be one of `txt`, `md`, `html`, `pdf`, `csv`, `xlsx` | Reject with the list of supported formats |
| Non-empty | File size > 0 and extracted text length > 0 | Reject as empty |
| Duplicate | `source_sha256` must not match an existing document in the same workspace | Reject as duplicate |
| Injection scan | Scan extracted text for instruction-like patterns aimed at the assistant | Flag for review; do not auto-reject on a heuristic match alone |
| Malware scan | Scan the file bytes | Reject the upload |

The duplicate check is scoped to the workspace. The same file may legitimately exist in two workspaces, and each workspace owns its own copy.

The injection scan is defence in depth. The primary control is that retrieved passages are data, never instructions, and that the reviewer (spec §3.8) blocks answers that follow instructions found inside a document. A heuristic scan cannot classify every instruction, so it must not be the only control, and a match must not silently drop a legitimate document.

### 3.2 Stage 2 — Normalize

Normalization converts the file into canonical text while preserving the structure the chunker needs.

| Format group | Formats | Normalized to | Notes |
|---|---|---|---|
| Plaintext | TXT | Text, unchanged | Not converted to Markdown. Chunked by paragraph |
| Plaintext | Markdown | Markdown | Structure preserved as-is |
| Plaintext | HTML | Markdown | Via `markitdown` |
| PDF | PDF | Markdown | Via `markitdown`. Image data is not processed; scanned PDFs are not handled; tables with composite cells are not guaranteed to convert well |
| Tables | CSV | CSV | Header row retained |
| Tables | XLSX | CSV | One CSV per sheet; a four-sheet workbook yields four CSV documents |

All image content is removed during normalization. A document that is only images normalizes to empty text and is rejected at stage 1.

Normalization must not alter Vietnamese characters. Accent stripping, transliteration and whitespace collapsing are all prohibited here, because the corpus is Vietnamese and the chunk text is what the BM25 index sees.

### 3.3 Stage 3 — Chunk

Chunks are split along the structure of the normalized text, and each chunk carries the section path it came from (spec §2.2.a step 3, §3.4.a).

| Source | Chunking rule | Section path |
|---|---|---|
| Markdown / HTML / PDF | Split on heading boundaries; a section that exceeds the target size is split further on paragraph boundaries | Full heading path, e.g. `Chính sách đổi trả > Thời hạn` |
| CSV | Split on row groups; every chunk repeats the header row | Table name or sheet name |
| XLSX | Same as CSV, applied per sheet | Sheet name |
| TXT | Split on paragraph boundaries | Paragraph index |

Every CSV chunk repeats the header row. Without it, a chunk of bare numbers is unsearchable by keyword and unreadable as a citation.

Chunk size is **TBD**. The proposal is a token-based target of roughly 512 tokens with roughly 64 tokens of overlap for structured text, and a row count target for tables. This must be validated against the Recall@5 ≥ 0.85 threshold (spec §3.4.b) before it is fixed; the value is a design parameter, not a measured result.

The TXT heuristic was previously left undecided. The rule above — paragraph boundaries — is the proposal, and it carries the same validation requirement.

### 3.4 Stage 4 — Embed

| Property | Value |
|---|---|
| Model | `embeddinggemma2` |
| Mode | Text only |
| Quantisation | Q4 |
| Runtime format | LiteRT-LM |
| Dimensions | **TBD** — must be read from the deployed checkpoint before any collection is created |
| Task prefixes | **TBD** — confirm whether the checkpoint requires asymmetric prefixes such as `query: ` / `passage: ` |

The model runs in-process in the backend. It replaces the earlier `multilingual-e5-small` choice, which was dropped in favour of the smaller LiteRT-LM build.

Two details are unresolved and both affect retrieval quality:

1. **Dimensions.** A collection created with the wrong vector size fails at upsert time, not at startup. The dimension must be read from the checkpoint configuration and set in one place.
2. **Prefixes.** The earlier E5 model required `query: ` and `passage: ` prefixes. Whether `embeddinggemma2` does is unconfirmed. If it does, the prefixes belong in the two embedding helpers, never at call sites.

Both are tracked as open questions in §9.

### 3.5 Stage 5 — Index

Chunks are written to the workspace collection `ws_<workspace_id>` with the metadata set in §4.

The write is staged: chunks are written with an `indexed` flag of `false`, the chunk count is verified, and only then is the flag flipped to `true`. A partially written document is therefore never retrievable. The full sequence, including the failure paths, is in `output/reindexing-strategy.md` §4.

### 3.6 Stage 6 — Mark as effective

When a new version replaces an old one, the old version moves to `superseded` and the new version becomes effective (spec §2.2.a step 5, §2.2.c).

The old version's content is removed from the vector database rather than retained and filtered. The document store keeps the old version's original file and metadata, so it stays viewable in history and trace citations remain reconcilable.

### 3.7 Stage 7 — Report status

Every stage transition writes the document version's index status to the document store, so the Portal can show progress and an error reason. The status vocabulary is in §2.3.

## 4. Chunk metadata

The metadata set is fixed by spec §2.2.b and is stored on every chunk.

| Field | Type | Source | Notes |
|---|---|---|---|
| `doc_id` | string | Document store | Matches the document store key |
| `workspace_id` | string | Authenticated session | Stamped server-side, never from a request body |
| `title` | string | Document store | Shown to the customer in citations |
| `uri` | string | Document store | Original source of the document |
| `section` | string | Chunking stage | Section path in the original text |
| `chunk_index` | int | Chunking stage | Order within the document |
| `updated_at` | datetime | Document store | Last update time of the document |
| `doc_type` | enum | Normalization stage | `markdown`, `html`, `pdf`, `csv`, `xlsx` |
| `version` | string | Document store | Version the chunk belongs to |
| `status` | enum | Indexing stage | `active` or `superseded` |
| `body` | string | Chunking stage | The chunk text; this is the field the BM25 index covers |
| `indexed` | bool | Indexing stage | `false` while staging, `true` once the version is complete |

`indexed` is an addition to the spec's field list, not a change to it. The spec's `status` enum keeps exactly two values, and `indexed` carries the staging state that a third enum value would otherwise have to carry. The retrieval filter requires `status == active` **and** `indexed == true`.

`doc_type` has no `txt` member in the spec's enum, so a TXT upload is recorded as `markdown` after normalization. This is a spec ambiguity, listed in §9.

## 5. Data stores and ownership

| Store | Owns | Does not own |
|---|---|---|
| MySQL | Workspace registry, document records, version records, index status, audit log, re-index job records | Original file bytes, chunk text, vectors |
| SeaweedFS (S3 API) | Original uploaded files, one object per version | Version metadata, index status |
| Qdrant | Embedded chunks and their metadata for the latest indexed version | Version history, originals, effective status |

MySQL is the source of truth for workspace IDs and for which version is effective. Qdrant is the source of truth for search only. A disagreement between MySQL and Qdrant is resolved in favour of MySQL, and the affected document is re-indexed.

## 6. Design decisions

### 6.1 One collection per workspace

| Field | Value |
|---|---|
| Status | Accepted |
| Context | Spec §2.2.b requires one collection per workspace and forbids cross-collection queries |
| Decision | Collection `ws_<workspace_id>`, plus a mandatory `workspace_id` payload filter on every query |
| Alternatives considered | A single shared collection with a tenant filter — rejected because the spec forbids it |
| Consequences | Two layers of isolation; N collections cost more than one collection with N filters, which is negligible at two workspaces |
| Revisit when | The workspace count grows enough that per-collection segment overhead matters — then use `shard_key_selector` with `workspace_id` as the shard key |

### 6.2 Superseded content is deleted, not flagged

| Field | Value |
|---|---|
| Status | Accepted |
| Context | The spec requires expired documents to be excluded at the metadata filter step; it does not require them to be retained in the vector database |
| Decision | The re-index path removes the old version's chunks from the collection. The `status == active` filter remains as the second layer of isolation and is still tested |
| Alternatives considered | Retaining superseded chunks and relying on the filter — rejected because it lets the collection grow without bound and makes "outdated content is not searchable" a property of the filter rather than of the data |
| Consequences | The vector database holds only the latest indexed version; the document store keeps history |

### 6.3 Staged writes

| Field | Value |
|---|---|
| Status | Accepted |
| Context | A partially written document that is visible to search produces answers assembled from half of one version and half of another |
| Decision | Write with `indexed = false`, verify the chunk count, then flip the flag to `true` in one payload update |
| Alternatives considered | Write directly as active — rejected because a partial upsert would be visible; keep both versions until the new one is complete — rejected because it creates a window where old and new policy content are both retrievable |
| Consequences | A document is briefly absent during re-index rather than briefly wrong |

### 6.4 Per-document re-index

| Field | Value |
|---|---|
| Status | Accepted |
| Context | The previous workflow re-indexed the entire current state store on every request, which does not satisfy spec §3.4.b criterion 5 |
| Decision | A re-index run touches only the changed document. The run completes in one pass, so the new content is live after at most one run |
| Alternatives considered | Whole-workspace re-index — rejected on the spec criterion and on cost; incremental per-chunk diffing — rejected as unnecessary complexity at a corpus of 49 documents |
| Consequences | Re-index cost scales with the size of the changed document, not the workspace |

## 7. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Embedding recall degrades on unaccented or abbreviated Vietnamese (spec §3.3.c EV-INTENT-02) | Medium | High — intent and policy questions fail | Measure recall on an unaccented test set before the demo; if recall drops, add a diacritic-restoration step before embedding and re-measure |
| R2 | Chunk size is wrong in either direction | Medium | Medium — too large hurts precision, too small loses context | Validate against Recall@5 ≥ 0.85 and faithfulness ≥ 0.9 before fixing the value |
| R3 | A document is invisible for longer than expected after a failed re-index | Low | Medium — questions about it get "no information available" | The Portal shows `failed` with a reason and a retry action; the document store still holds the original file, so a retry restores it |
| R4 | The embedding dimension is misconfigured | Low | High — upserts fail | Read the dimension from the checkpoint configuration; fail fast at collection creation |
| R5 | A document contains instructions aimed at the agent (spec §3.4.c EV-POLICY-08) | Medium | High — wrong price quoted | Treat passages as data; reviewer blocks non-grounded answers; injection scan is defence in depth only |
| R6 | PDF conversion loses table structure | Medium | Low — affects a minority of documents | Composite-cell tables are explicitly out of guarantee per spec §2.2.a; verify the three sample PDFs convert acceptably |

## 8. Verification

| Requirement | Source | How it is checked |
|---|---|---|
| Every chunk carries the full metadata set | Spec §2.2.b | Assert the payload keys on a sample chunk from each format group |
| Expired documents are excluded at the filter step | Spec §2.2.b | `test_superseded_excluded` in `output/retrieval.py` |
| No cross-workspace retrieval | Spec §2.2.b, §3.4.b criterion 6 | `test_isolation` in `output/retrieval.py` |
| A partially written document is not retrievable | Staged-write guarantee | `test_staged_chunks_not_retrievable` in `output/retrieval.py` |
| New policy content is live after at most one re-index run | Spec §3.4.b criterion 5 | `test_reindex_single_run` in `output/reindexing-strategy.md` §10.1 |
| Out-of-KB questions get the "no information available" template | Spec §3.4.b criterion 4 | Evaluation suite, use case 3.4 |
| Recall@5 ≥ 0.85 | Spec §3.4.b criterion 1 | Evaluation suite, use case 3.4 |
| Index status is visible with a failure reason | Spec §2.2.c | Portal test |

## 9. Open questions

| ID | Question | Impact | Owner | Target date |
|---|---|---|---|---|
| Q1 | What is the vector dimension of the deployed `embeddinggemma2` checkpoint? | Blocks collection creation | Group 02 | Before the first ingest run |
| Q2 | Does `embeddinggemma2` require task prefixes for retrieval? | Affects recall if wrong | Group 02 | Before the first ingest run |
| Q3 | What chunk size and overlap meet Recall@5 ≥ 0.85? | Affects retrieval quality | Group 02 | Before the evaluation run |
| Q4 | Should a TXT upload be recorded as `doc_type = markdown` or should the spec enum be extended with `txt`? | Affects metadata conformance | Group 02 | Before the report is written |
| Q5 | Does the injection scan reject, flag, or pass with a warning? | Affects upload UX and the Portal | Group 02 | Before the Portal is built |
| Q6 | Is the TXT paragraph-boundary heuristic acceptable, or is a different rule needed? | Affects retrieval quality | Group 02 | Before the evaluation run |

## Appendix A: Change log

| Version | Date | Author | Change |
|---|---|---|---|
| v1.0 | 2026-10-23 | SE373 Group 02 | Initial document. Consolidates the ingestion design, replaces `multilingual-e5-small` with `embeddinggemma2`, and closes the re-indexing gap with `output/reindexing-strategy.md` |

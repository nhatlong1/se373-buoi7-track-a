# BizCare Re-indexing Strategy

| Field | Value |
|---|---|
| Author | SE373 Group 02 |
| Date | 2026-10-23 |
| Version | v1.0 |
| Status | Draft |
| Owner | SE373 Group 02 |
| Reviewers | TBD |
| Applies to | BizCare final project, knowledge base subsystem |
| Related documents | `output/project-spec-en.md` (spec), `output/ingestion-pipeline.md` (pipeline), `output/vector-db-decision.md` (Qdrant decision), `output/retrieval.py` (retrieval layer) |

## 1. Introduction

### 1.1 Purpose

This document defines how a changed document becomes live in search, so that an implementer can build the re-index path and a reviewer can check it against the specification's re-indexing criterion.

### 1.2 Scope

Covered: change detection, the re-index run, the write ordering that keeps a document from being half-old and half-new, failure handling and retry, the job record, and the verification tests.

Not covered: the initial ingestion of a new document (see `output/ingestion-pipeline.md` §3), retrieval query construction (see `output/retrieval.py`), and the agent workflow (spec §4.1).

### 1.3 Design drivers

| Driver | Type | Priority | Implication |
|---|---|---|---|
| Spec §3.4.b criterion 5: after editing a policy document, related questions reflect the new content after at most one re-indexing run | Normative | Must | One run must be sufficient; the run must be scoped to the changed document |
| Spec §3.4.c EV-POLICY-05 tests exactly this behaviour | Normative | Must | The behaviour is a graded scenario, not an internal detail |
| Spec §3.4.c EV-POLICY-07: an expired document containing the exact answer must not be used | Normative | Must | The old version must be unreachable the moment the new one becomes effective |
| A stale policy answer is a business harm (spec §1.1) | Quality | Must | Prefer a brief absence over a brief wrong answer |
| Corpus is 49 documents across 2 workspaces (spec §2.1) | Resource | Informational | Per-document re-index is cheap; no incremental chunk diffing is needed |
| Single host, 4 vCPU / 12 GB RAM | Resource | Must | Re-index runs in the backend process, not as a separate worker fleet |

### 1.4 Constraints

- The document store is the source of truth for which version is effective (spec §2.2.c).
- The vector database holds only the latest indexed version of each document.
- Every write to the document store writes an audit log recording who, which workspace, when, `doc_id` and `version` (spec §2.2.c).
- Citations in traces record the `doc_id` and `version` used, so a policy change stays reconcilable (spec §2.2.c).

### 1.5 Glossary

| Term | Meaning |
|---|---|
| Re-index run | One pass that makes a changed document's new content live |
| Effective version | The version currently returned by search for a document |
| Source hash | SHA-256 of the uploaded file bytes |
| Content hash | SHA-256 of the normalized text |
| Staged write | Writing chunks with `indexed = false`, then flipping the flag once the write is verified complete |
| Job record | The MySQL row tracking one re-index run |

## 2. The problem this closes

The previous design had no re-indexing strategy and no change-detection mechanism. The sample workflow was: a customer uploads a new document and requests a re-index, and the entire current state store is re-indexed at once.

That fails spec §3.4.b criterion 5 in two ways. It re-indexes far more than the changed document, and it has no defined behaviour for the window during which the run is in progress. The spec requires that a policy edit be reflected after at most one run, and EV-POLICY-05 tests it directly.

## 3. Change detection

### 3.1 What triggers a re-index

| Trigger | Detection | Action |
|---|---|---|
| A new document is uploaded | New `doc_id` in the document store | Full ingest of the new document |
| A document is replaced with a new file | `source_sha256` differs from the effective version's | Re-index run for that document |
| A document is edited in the Portal | The edit produces new normalized text | Re-index run for that document |
| A document is deleted | Delete operation | Remove its chunks from the collection; keep the document store record (spec §2.2.c soft delete) |
| The embedding model or chunking parameters change | Configuration version differs from the one recorded on the document | Re-index run for the affected documents |

The last row matters. A change to the embedding model or to the chunk size invalidates every existing vector, because the stored vectors no longer match the current model or the current chunk boundaries. The document store records a `index_config_version` per document; a mismatch marks the document as needing re-index.

### 3.2 Hash-based detection

Two hashes are stored per document version in the document store.

| Hash | Computed over | Detects |
|---|---|---|
| `source_sha256` | The uploaded file bytes | A different file was uploaded |
| `content_sha256` | The normalized text | The same file was uploaded but the normalization output changed, for example after a chunking or model change |

`content_sha256` is the one that matters for the common case. A Portal edit that changes a policy value changes the normalized text, so the content hash changes even though the file bytes may be regenerated identically.

### 3.3 Detection point

Detection runs at the point of write, not on a timer. The Portal edit handler and the upload handler both compute the new content hash and compare it against the effective version's. A difference schedules a re-index run.

A periodic sweep is not needed at this corpus size, but a manual "re-index workspace" action is exposed in the Portal for recovery after a failed run.

## 4. The re-index run

### 4.1 Sequence

| Step | Action | State written | Failure handling |
|---|---|---|---|
| 1 | Load the document and the effective version from the document store | — | Abort; nothing to do |
| 2 | Compute the new content hash; compare with the effective version's | — | If equal, the run ends as a no-op |
| 3 | Normalize the new content | — | `failed` with the reason |
| 4 | Chunk the normalized text | — | `failed` with the reason |
| 5 | Embed the chunks | — | `failed` with the reason |
| 6 | Delete the effective version's chunks from the collection | — | `failed` with the reason |
| 7 | Write the new chunks with `indexed = false` | — | `failed` with the reason; the document is absent, not stale |
| 8 | Verify the written chunk count matches the expected count | — | `failed` with the reason; delete the partial write |
| 9 | Flip `indexed` to `true` on the new chunks | — | `failed` with the reason |
| 10 | Mark the old version `superseded` in the document store; mark the new version effective | Document store | `failed` with the reason |
| 11 | Write the audit log entry | Document store | `failed` with the reason |
| 12 | Set the document's index status to `indexed` | Document store | — |

Steps 3 to 5 do the expensive work before anything is deleted. If normalization, chunking or embedding fails, the effective version is untouched and the document stays searchable with its old content. That is the correct outcome for a transient failure, and it is why the delete is step 6 rather than step 1.

### 4.2 Write ordering and the visibility window

The ordering in §4.1 produces a window in which the document is absent from search:

```
  t0   effective version v1 is live
  t1   step 6: v1 chunks deleted          → document absent
  t2   step 7: v2 chunks written, indexed=false
  t3   step 8: count verified
  t4   step 9: v2 chunks indexed=true     → v2 live
```

The window is t1 to t4. During it, a question about the document gets the "no information available" answer plus a ticket request (spec §3.4.b criterion 4).

This is deliberate. The alternative — keeping v1 live until v2 is complete — creates a window where both versions are retrievable, and a policy question could be answered from the old version. A wrong policy answer is a business harm; a missing one is a recoverable inconvenience. The window is short because steps 6 to 9 are collection writes with no embedding work in them.

### 4.3 Ordering constraint

Step 9 must not run before step 8. If the flag is flipped before the count is verified, a truncated write becomes visible and the document is permanently missing chunks.

Step 10 must not run before step 9. If the document store records v2 as effective while the collection still holds only staged chunks, the two stores disagree and the document is invisible despite being marked effective.

### 4.4 Idempotency

A re-index run is idempotent with respect to its target version. Re-running it on the same content produces the same chunks and the same effective state, because the content hash comparison in step 2 short-circuits a no-op run.

A run that fails at step 6 or later leaves the document absent. Re-running it is safe: step 6 deletes whatever chunks exist for the document, including a partial write from the failed run, and steps 7 to 9 rebuild them.

## 5. Failure handling

### 5.1 Failure classes

| Class | Where it fails | Effect on the document | Recovery |
|---|---|---|---|
| Pre-processing | Steps 3 to 5 | Old version stays live | Fix the input, retry |
| Write | Steps 6 to 9 | Document absent | Retry; the run is idempotent |
| Commit | Steps 10 to 11 | Document absent, or effective version recorded but chunks staged | Retry; step 2 sees a matching content hash and must be forced to continue rather than short-circuit |

The commit-class failure needs care. If step 10 succeeded and step 11 failed, the document store says v2 is effective and the collection holds v2 as active. A naive retry would stop at step 2 because the content hash matches, leaving the audit log unwritten. The retry path therefore compares the *collection* state, not only the document store state, and continues to step 11 when the audit entry is missing.

### 5.2 Retry

| Property | Value |
|---|---|
| Trigger | The Portal's retry action, or an automatic retry for transient errors |
| Maximum attempts | 3 |
| Backoff | Exponential, starting at 5 s |
| Retryable errors | Storage timeout, embedding model timeout, collection write timeout |
| Non-retryable errors | Unsupported format, empty document, duplicate document, normalization failure on malformed input |

A non-retryable error leaves the document in `failed` with the reason recorded, and the Portal shows the reason and the retry action. The owner can replace the file and retry.

### 5.3 Degradation behaviour

If the vector database is unavailable during a re-index, the document store still holds the original file and the effective version's metadata. The document's index status becomes `failed` with the reason. The document is not searchable, and the agent answers questions about it with the "no information available" template rather than with stale content.

If the embedding model fails to load, no re-index run can start. The Portal shows the failure at the workspace level, and existing indexed content stays searchable because it does not depend on the model at query time.

## 6. Job record

Each run writes a row to MySQL.

| Field | Type | Purpose |
|---|---|---|
| `job_id` | string | Primary key |
| `workspace_id` | string | Owning workspace |
| `doc_id` | string | Target document |
| `from_version` | string | Version that was effective before the run |
| `to_version` | string | Version the run made effective |
| `trigger` | enum | `upload`, `edit`, `delete`, `config_change`, `manual` |
| `status` | enum | `running`, `succeeded`, `failed` |
| `error_reason` | string | Populated on `failed` |
| `chunks_written` | int | Chunk count, for verification against the expected count |
| `started_at` | datetime | |
| `finished_at` | datetime | |

The job record is what makes the Portal's index status display possible (spec §2.2.c) and what a reviewer inspects to confirm that a policy edit was reflected in one run.

## 7. Audit log

Every write to the document store writes an audit log entry (spec §2.2.c): who performed it, which workspace, when, `doc_id`, `version`.

A re-index run writes at least two entries: one for the version change and one for the effective-status change. The audit log is append-only and is not written to by the vector database.

## 8. Interaction with the rest of the system

| Concern | Behaviour |
|---|---|
| Retrieval | The filter requires `status == active` and `indexed == true`. A staged or superseded chunk is never a candidate |
| Citations | A trace records the `doc_id` and `version` of the passage used, so an answer given before a policy change stays reconcilable against the version it came from |
| Reviewer | The reviewer reads the draft and the retrieved passages. It does not read the document store, so it cannot be confused by a version that is no longer effective |
| Agent workflow | The agent is not blocked while a re-index runs. It sees the document as absent and answers with the "no information available" template |

## 9. Design decisions

### 9.1 Per-document re-index, not whole-workspace

| Field | Value |
|---|---|
| Status | Accepted |
| Context | The previous workflow re-indexed the entire current state store on every request |
| Decision | A run touches only the changed document |
| Alternatives considered | Whole-workspace re-index — rejected on spec §3.4.b criterion 5 and on cost; per-chunk diffing — rejected as unnecessary complexity at 49 documents |
| Consequences | Cost scales with the changed document, not the workspace. A model or chunking change still requires a workspace-wide run, which is why `index_config_version` is tracked per document |
| Revisit when | The corpus grows past a few thousand documents, where per-chunk diffing becomes worth its complexity |

### 9.2 Delete-then-write, not write-then-swap

| Field | Value |
|---|---|
| Status | Accepted |
| Context | The vector database holds only the latest indexed version, so both versions cannot coexist in the collection |
| Decision | Delete the effective version's chunks, then write the new version's chunks staged, then flip the flag |
| Alternatives considered | Write the new version first and delete the old one after — rejected because both versions would be retrievable during the overlap, and a policy question could be answered from the old version |
| Consequences | A brief absence window, in exchange for never exposing two versions of a policy at once |

### 9.3 Pre-processing before deletion

| Field | Value |
|---|---|
| Status | Accepted |
| Context | Normalization, chunking and embedding are the steps most likely to fail, and they are also the slowest |
| Decision | Steps 3 to 5 complete before step 6 deletes anything |
| Alternatives considered | Delete first, then process — rejected because a processing failure would leave a valid document unsearchable |
| Consequences | A failed run leaves the old content live, which is the correct outcome for a transient failure |

### 9.4 Hash-based detection, not a polling sweep

| Field | Value |
|---|---|
| Status | Accepted |
| Context | The corpus is small and changes are user-initiated |
| Decision | Detection happens at the point of write, using a content hash comparison |
| Alternatives considered | Periodic sweep comparing timestamps — rejected because it re-indexes documents that did not change and adds a scheduler to a single-host deployment |
| Consequences | A manual workspace-wide re-index action is still exposed for recovery |

## 10. Verification

| Requirement | Source | How it is checked |
|---|---|---|
| A policy edit is reflected after at most one re-index run | Spec §3.4.b criterion 5 | `test_reindex_single_run` in §10.1 |
| The expired document containing the exact answer is not used | Spec §3.4.c EV-POLICY-07 | `test_superseded_excluded` in `output/retrieval.py` |
| The new version is live and the old one is not | Spec §2.2.a step 5 | `test_reindex_replaces_content` in §10.1 |
| A failed run does not leave a partially indexed document visible | Spec §2.2.a step 6 | `test_failed_run_leaves_no_partial` in §10.1 |
| The document store and the collection agree on the effective version | Spec §2.2.c | `test_stores_agree_after_run` in §10.1 |
| Index status and failure reason are visible | Spec §2.2.c | Portal test |

### 10.1 Test scenarios

| Test | Setup | Assertion |
|---|---|---|
| `test_reindex_single_run` | Index a policy document, edit one value, run one re-index | A question about the edited value returns the new content; a question about the old value does not return the old content |
| `test_reindex_replaces_content` | Index a document, replace it with a new version | The collection holds chunks for the new version only; the old version's chunks are gone |
| `test_failed_run_leaves_no_partial` | Force a failure during the write step | No chunk for the document is retrievable; the document store records `failed` with a reason; the old version is not marked superseded |
| `test_stores_agree_after_run` | Run a successful re-index | The document store's effective version matches the version present in the collection |
| `test_noop_run_is_cheap` | Run a re-index with unchanged content | The run ends without a collection write |

## 11. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | The absence window is long enough for a customer to hit it | Low | Medium — a "no information available" answer during a policy change | The window contains only collection writes; measure it and report it in the technical report |
| R2 | A commit-class failure leaves the stores disagreeing | Low | High — the document is invisible despite being marked effective | §5.1 commit-class handling; `test_stores_agree_after_run` |
| R3 | A model or chunking change is not detected, leaving stale vectors | Medium | High — retrieval quality silently degrades | `index_config_version` per document; a mismatch marks the document for re-index |
| R4 | Re-index runs overlap for the same document | Low | Medium — two runs race on the same chunks | One active job per `doc_id`; a second request for the same document is rejected while a run is in progress |
| R5 | The embedding model is unavailable at run time | Low | Medium — the document stays unsearchable | The document store keeps the original file; the run is retried when the model returns |

## 12. Open questions

| ID | Question | Impact | Owner | Target date |
|---|---|---|---|---|
| Q1 | What is the measured duration of the absence window (t1 to t4) on the target host? | Needed for the technical report | Group 02 | Before the report is written |
| Q2 | Should the Portal expose a per-document re-index action, or only a workspace-wide one? | Affects the Portal build | Group 02 | Before the Portal is built |
| Q3 | Is a background job runner needed, or is an in-process run sufficient at this corpus size? | Affects the backend design | Group 02 | Before the backend is built |
| Q4 | Should a re-index run be triggered automatically on save, or only on an explicit owner action? | Affects the Portal UX and the EV-POLICY-05 test setup | Group 02 | Before the Portal is built |

## Appendix A: Change log

| Version | Date | Author | Change |
|---|---|---|---|
| v1.0 | 2026-10-23 | SE373 Group 02 | Initial document. Defines change detection, the re-index run, write ordering, failure handling and the verification tests. Closes the open re-indexing item from the previous design |

# Spec Analysis Report Template

**Use when:** a specification document must be assessed before implementation — for gaps, ambiguity, contradictions, feasibility, and testability. The reader is the author and the implementers, who need to know what to clarify and what to build.

**Do not use for:** writing the specification itself (use `technical-specification.md`).

---

## Template

```markdown
# Specification Analysis: <spec title>

| Field | Value |
|---|---|
| Author | <name or agent> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / In Review / Final |
| Specification analyzed | <document, version, date> |
| Specification author | |
| Intended implementers | |
| Analysis method | <read / cross-referenced against code / workshop> |
| Scope | <what was analyzed> |
| Out of scope | <what was not analyzed> |

## Executive summary

<3–6 sentences. The overall assessment: is this spec ready to implement?
How many blocking issues, how many ambiguities, how much of it is
testable. Name the single most important thing to fix first.>

## 1. Assessment summary

| Dimension | Rating | Basis |
|---|---|---|
| Completeness | <complete / gaps found / major gaps> | |
| Clarity | <clear / ambiguous / frequently ambiguous> | |
| Internal consistency | <consistent / contradictions found> | |
| Testability | <testable / partly testable / untestable> | |
| Feasibility | <feasible / feasible with changes / infeasible as written> | |
| Scope control | <well bounded / scope creep risk> | |
| Traceability | <traceable / partial> | |

**Overall verdict:** <Ready to implement | Implement after resolving
the blocking issues below | Not ready — needs a rewrite of section X>

## 2. Specification overview

<What the spec is for, its scope, its audience, and its structure. This
orients a reader who has not read the spec.>

### 2.1 Scope and non-scope
<As stated in the spec.>

### 2.2 Structure map

| Section | Purpose | Requirements | Status |
|---|---|---|---|

## 3. Requirement inventory

<Every normative requirement, extracted and numbered. This is the
backbone of the analysis — everything else references these IDs.>

| ID | Requirement (condensed) | Source section | Type | Priority | Testable? | Status |
|---|---|---|---|---|---|---|
| R-001 | | | Functional / Non-functional / Constraint | Must / Should / May | Yes / No / Partly | OK / Ambiguous / Contradictory / Missing |

### 3.1 Requirement type breakdown

| Type | Count | Notes |
|---|---|---|

### 3.2 Requirement strength audit

<Check that MUST / SHOULD / MAY are used deliberately. Flag "must" on
things nothing can fail, and "may" on things that are actually
mandatory.>

## 4. Findings

### 4.1 Blocking issues

#### B1. <Short title>

| Field | Value |
|---|---|
| Type | Gap / Ambiguity / Contradiction / Untestable / Infeasible |
| Location | Spec section X.Y |
| Affected requirements | R-00X, R-00Y |
| Severity | Blocking |

**Problem**
<What is wrong, quoted or cited.>

**Why it blocks**
<The concrete consequence: two implementers would build different things,
or the requirement cannot be verified.>

**Proposed resolution**
<Specific, actionable. Offer a default if the author does not choose.>

### 4.2 Ambiguities

| ID | Location | Ambiguity | Readings | Recommended reading |
|---|---|---|---|---|

### 4.3 Contradictions

| ID | Between | Contradiction | Suggested resolution |
|---|---|---|---|

### 4.4 Gaps

| ID | Area | What is missing | Why it matters |
|---|---|---|---|

### 4.5 Untestable requirements

| ID | Requirement | Why it cannot be verified | Suggested rewrite |
|---|---|---|---|

### 4.6 Out-of-scope items that leak in

<Requirements that belong to a different system, or that contradict the
stated non-scope.>

## 5. Traceability matrix

<Does every requirement trace to a design element, a test, or a
business goal? Where the chain breaks, the requirement is unverified.>

| Requirement | Business goal | Design element | Test | Verified? |
|---|---|---|---|---|

## 6. Feasibility assessment

| Aspect | Assessment | Risk | Mitigation |
|---|---|---|---|
| Technical feasibility | | | |
| Data availability | | | |
| Integration dependencies | | | |
| Performance / scale | | | |
| Security / compliance | | | |
| Operational readiness | | | |
| Schedule realism | | | |

## 7. Acceptance criteria review

| Requirement | Acceptance criterion present? | Measurable? | Deterministic? | Notes |
|---|---|---|---|---|

## 8. Consistency checks performed

| Check | Result | Notes |
|---|---|---|
| Terminology used consistently | | |
| No duplicate requirement IDs | | |
| No requirement contradicts another | | |
| All referenced sections exist | | |
| All referenced artifacts exist | | |
| Error handling specified for every external call | | |
| Non-functional requirements quantified | | |

## 9. Recommendations

| # | Recommendation | Type | Owner | Priority | Effort |
|---|---|---|---|---|---|

## 10. Open questions for the spec author

| # | Question | Blocks | Who can answer |
|---|---|---|---|

## 11. Limitations and open questions

<What was not analyzed, which parts of the spec were ambiguous enough to
prevent analysis, and what would change the assessment.>

## Appendix A: Requirement-to-section index

## Appendix B: Glossary of terms used in the spec
```

---

## Rules for writing spec analysis

1. **Extract before you judge.** Build the requirement inventory first. Judgments made before extraction are impressions.
2. **Quote the spec.** Every finding cites the section and quotes the problematic text. A finding the author cannot locate is useless.
3. **Distinguish a gap from a choice.** "The spec does not say which database" is a gap. "The spec says PostgreSQL" is a decision, not a finding.
4. **Offer a resolution, not just a complaint.** "Ambiguous" alone makes work for the author. Propose the default you would implement and let them override.
5. **Do not rewrite the spec.** This document analyzes. If the author wants the rewrite, that is a separate task.
6. **Testability is a first-class check.** A requirement that cannot fail cannot be verified. Flag every one.
7. **Do not inflate severity.** If everything is blocking, nothing is. Reserve blocking for issues that genuinely stop implementation.
8. **Note what is good.** A spec that states its non-scope clearly, or defines its error behavior, has done something worth saying out loud.

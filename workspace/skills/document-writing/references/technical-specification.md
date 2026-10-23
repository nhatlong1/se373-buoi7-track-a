# Technical Specification Template

**Use when:** the document defines what a system must do — requirements with IDs, interfaces, data model, error handling, acceptance criteria. The reader is an implementer who needs an unambiguous contract.

**Do not use for:** describing how the system will be built (use `architectural-design-document.md` or `system-design-document.md`), or documenting an existing system for users (use `documentation.md`).

---

## Template

```markdown
# <System or Feature> Specification

| Field | Value |
|---|---|
| Author | <name or agent> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / In Review / Final / Implemented |
| Owner | |
| Reviewers | |
| Applies to | <version / release> |
| Related documents | <design doc, ADR, issue links> |

## 1. Introduction

### 1.1 Purpose
<One paragraph: what this specification defines and why it exists.>

### 1.2 Scope
<What is specified.>

### 1.3 Non-scope
<What is explicitly not specified, and where it is specified instead.>

### 1.4 Definitions and terminology

| Term | Definition |
|---|---|
| | |

### 1.5 Requirement conventions

**Normative keywords.** MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD,
SHOULD NOT, MAY, OPTIONAL are to be interpreted as described in RFC 2119.
For readability, this document uses MUST, SHOULD, and MAY.

**Requirement IDs.** Every requirement has a stable ID of the form
`REQ-<AREA>-<NNN>`. IDs are never reused or renumbered.

**Priority.** MUST (a test can fail if violated), SHOULD (expected but
deferrable), MAY (optional).

## 2. System context

<What the system does in its environment. Users, upstream and
downstream systems, the boundary of this specification.>

### 2.1 Actors and roles

| Actor | Description | Permissions |
|---|---|---|

### 2.2 External interfaces

| Interface | Direction | Protocol | Description |
|---|---|---|---|

## 3. Functional requirements

<Grouped by feature. Each requirement is one testable statement.>

### 3.1 <Feature area>

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-XXX-001 | The system MUST <observable behavior>. | MUST | <test name / method> |
| REQ-XXX-002 | | | |

### 3.2 <Feature area>

## 4. Non-functional requirements

### 4.1 Performance

| ID | Requirement | Target | Measurement method | Conditions |
|---|---|---|---|---|
| REQ-PERF-001 | | | | |

### 4.2 Reliability and availability

| ID | Requirement | Target | Measurement method |
|---|---|---|---|

### 4.3 Security

| ID | Requirement | Verification |
|---|---|---|

### 4.4 Privacy and data handling

| ID | Requirement | Verification |
|---|---|---|

### 4.5 Scalability and capacity

| ID | Requirement | Target | Conditions |
|---|---|---|---|

### 4.6 Usability and accessibility

| ID | Requirement | Verification |
|---|---|---|

### 4.7 Observability

| ID | Requirement | Verification |
|---|---|---|

### 4.8 Maintainability and portability

| ID | Requirement | Verification |
|---|---|---|

## 5. Data model

### 5.1 Entities

| Entity | Description | Owner | Retention |
|---|---|---|---|

### 5.2 <Entity> detail

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|

### 5.3 Relationships
<Diagram or description.>

### 5.4 Data lifecycle
<Creation, update, versioning, expiry, deletion.>

## 6. Interfaces

### 6.1 <Interface name>

**Purpose.** <What it does.>

**Request**

| Field | Type | Required | Validation | Description |
|---|---|---|---|---|

**Response**

| Field | Type | Description |
|---|---|---|

**Errors**

| Condition | Status / code | Message | Client action |
|---|---|---|---|

**Example**

```http
POST /v1/resource HTTP/1.1
```

```json
{ }
```

## 7. Behavior specifications

### 7.1 Normal flow
<Numbered steps.>

### 7.2 Alternative flows
<One subsection per meaningful alternative.>

### 7.3 Error handling

| Condition | Detection | Response | Retryable | Notes |
|---|---|---|---|---|

### 7.4 Edge cases
<Empty input, maximum size, concurrent modification, clock skew, partial failure.>

### 7.5 Idempotency
<Which operations are idempotent, and the key.>

## 8. Constraints and assumptions

### 8.1 Constraints
<Hard limits: environment, platform, regulation, dependency versions.>

### 8.2 Assumptions
<Things taken as true. Each one, if false, breaks something — say what.>

## 9. Acceptance criteria

| Requirement ID | Acceptance criterion | Test method | Pass condition |
|---|---|---|---|

## 10. Traceability

| Requirement | Source (goal / regulation / issue) | Design element | Test |
|---|---|---|---|

## 11. Open issues

| ID | Issue | Impact | Owner | Target date |
|---|---|---|---|---|

## Appendix A: Requirement index

## Appendix B: Glossary

## Appendix C: Change log

| Version | Date | Author | Change |
|---|---|---|---|
```

---

## Rules for writing specifications

1. **One requirement, one sentence, one behavior.** "The system MUST validate the input and return an error" is two requirements. Split them.
2. **Requirements describe observable behavior, not implementation.** "MUST store the record in a table with an index on `workspace_id`" is a design decision wearing a requirement's clothes. "MUST return results only for the requesting workspace" is a requirement.
3. **Every MUST has a verification method.** If you cannot name the test, the requirement is not testable — either fix it or downgrade it to SHOULD.
4. **Quantify every non-functional requirement.** "MUST be fast" is not a requirement. "MUST return within 500 ms at p95 for a 10,000-record collection" is.
5. **Specify error behavior for every external call.** The most common source of implementation divergence is unhandled failure.
6. **State the conditions.** A latency target without a load condition is not a target.
7. **Keep IDs stable.** Never renumber. Never reuse. Requirements are referenced from tests, tickets, and other documents for years.
8. **Do not specify what you do not know.** Mark it as an open issue in section 11 rather than inventing a value.
9. **Include the non-scope.** It is the cheapest way to prevent scope creep.

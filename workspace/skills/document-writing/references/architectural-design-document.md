# Architectural Design Document Template

**Use when:** the document defines the internal design of one application — modules, classes, interfaces, data structures, and control flow. The reader is an implementer who needs to know where to put code.

**Do not use for:** design spanning multiple services or processes (use `system-design-document.md`), or for stating requirements without implementation detail (use `technical-specification.md`).

---

## Template

```markdown
# <Application> Architectural Design

| Field | Value |
|---|---|
| Author | <name or agent> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / In Review / Final / Implemented |
| Owner | |
| Reviewers | |
| Applies to | <release / version> |
| Related documents | <spec, system design, ADRs> |

## 1. Introduction

### 1.1 Purpose
<What this document defines and why.>

### 1.2 Scope
<Which parts of the application are covered.>

### 1.3 Non-scope
<What is decided elsewhere.>

### 1.4 Design drivers
<The forces that shaped the design. These are what the reader uses to
understand why a choice was made.>

| Driver | Type | Priority | Implication |
|---|---|---|---|

### 1.5 Constraints
<Language, framework, runtime, library, and platform constraints.>

### 1.6 Glossary

| Term | Meaning |
|---|---|

## 2. Architecture overview

### 2.1 Module map

```
┌─────────────────────────────────────────────┐
│  Presentation / API layer                   │
├─────────────────────────────────────────────┤
│  Application services                       │
├──────────────┬──────────────┬───────────────┤
│  Domain      │  Domain      │  Domain       │
├──────────────┴──────────────┴───────────────┤
│  Infrastructure (persistence, clients, I/O) │
└─────────────────────────────────────────────┘
```

### 2.2 Layer responsibilities

| Layer | Responsibility | May depend on | Must not depend on |
|---|---|---|

### 2.3 Dependency rules
<The rules that keep the architecture intact, and how they are
enforced — by lint rule, by test, or by convention.>

## 3. Module specifications

### 3.1 <Module name>

| Field | Value |
|---|---|
| Path | |
| Responsibility | |
| Public interface | |
| Depends on | |
| Depended on by | |
| Threading / concurrency | |

**Key types**

```python
class Order:
    """..."""
```

**Key operations**

| Operation | Signature | Preconditions | Postconditions | Errors |
|---|---|---|---|---|

**Invariants**
<What must always be true inside this module. These are the rules the
code must not break.>

## 4. Control flow

### 4.1 Primary sequence

| Step | Module | Operation | State touched |
|---|---|---|---|

### 4.2 State machine
<For stateful entities: states, transitions, guards, terminal states.>

```
[State A] --event--> [State B]
```

| From | Event | Guard | To | Side effects |
|---|---|---|---|---|

### 4.3 Error handling strategy

| Layer | Strategy | Rationale |
|---|---|---|

### 4.4 Concurrency model

| Concern | Approach | Rationale |
|---|---|---|
| Shared state | | |
| Locking | | |
| Async boundaries | | |
| Idempotency | | |

## 5. Data design

### 5.1 Entities and value objects

| Name | Kind | Definition | Invariants |
|---|---|---|---|

### 5.2 Collections and schemas

| Collection | Purpose | Key | Indexes | Retention |
|---|---|---|---|---|

### 5.3 Serialization

| Boundary | Format | Schema | Versioning |
|---|---|---|---|

### 5.4 Data flow and ownership
<Who writes, who reads, who is authoritative.>

## 6. Interfaces

### 6.1 Internal interfaces

| Interface | Provider | Consumers | Contract | Stability |
|---|---|---|---|---|

### 6.2 Extension points
<Where the design is meant to be extended, and the contract for doing so.>

## 7. Cross-cutting concerns

### 7.1 Error handling
### 7.2 Logging and tracing
### 7.3 Configuration
### 7.4 Security
### 7.5 Privacy and PII handling
### 7.6 Testing strategy

| Layer | What is tested | Tooling | Target |
|---|---|---|---|

## 8. Design decisions

<One subsection per significant decision. These are the parts a future
reader will question.>

### 8.1 <Decision>

| Field | Value |
|---|---|
| Status | Proposed / Accepted / Superseded |
| Context | <the forces> |
| Decision | <what was decided> |
| Alternatives considered | |
| Consequences | <good and bad> |
| Revisit when | <the trigger that would change this> |

## 9. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|

## 10. Open questions

| ID | Question | Impact | Owner | Target date |
|---|---|---|---|---|

## Appendix A: Module index

## Appendix B: Class / type index

## Appendix C: Change log
```

---

## Rules for writing architectural design documents

1. **State the drivers before the design.** A reader who does not know the constraints cannot judge the choices. Design drivers are the reason the design is what it is.
2. **Record the rejected alternatives.** The most common question a future reader asks is "why not X?". Answer it in the document.
3. **Give each decision a "revisit when" trigger.** A design without a trigger becomes permanent by accident.
4. **Specify invariants explicitly.** An invariant that is not written down is an invariant that will be broken.
5. **Show dependency direction.** The dependency rules section is what stops the architecture eroding.
6. **Distinguish the interface from the implementation.** The public interface is the contract; the implementation is replaceable.
7. **Do not specify what the code already shows.** This document captures intent and structure, not a line-by-line transcription.
8. **Keep it at the right altitude.** If the document contains the full source, it will be wrong the moment the code changes.

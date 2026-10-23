# System Design Document Template

**Use when:** the document defines a system spanning multiple services or processes — service boundaries, deployment topology, data ownership, data flow, scaling, reliability, and security. The reader decides whether the system will work and what it will cost.

**Do not use for:** the internal design of a single application (use `architectural-design-document.md`).

---

## Template

```markdown
# <System> Design

| Field | Value |
|---|---|
| Author | <name or agent> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / In Review / Final / Implemented |
| Owner | |
| Reviewers | |
| Applies to | <release / version> |
| Related documents | <spec, ADRs, threat model> |

## 1. Introduction

### 1.1 Purpose
<What this document defines.>

### 1.2 Scope
<Which services, data stores, and integrations are covered.>

### 1.3 Non-scope
<What is out of the boundary.>

### 1.4 Glossary

| Term | Meaning |
|---|---|

## 2. Requirements and constraints

### 2.1 Functional requirements
<Summary. Full list lives in the specification.>

### 2.2 Non-functional requirements

| ID | Requirement | Target | Measurement |
|---|---|---|---|

### 2.3 Capacity assumptions

| Quantity | Value | Basis | Growth |
|---|---|---|---|

### 2.4 Constraints
<Environment, budget, regulation, team size, existing infrastructure.>

## 3. System context

### 3.1 Context diagram

```
                    ┌──────────────┐
   customers ──────▶│   Channels   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  BizCare     │
                    │  platform    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Business │ │  Model   │ │  Object  │
        │   APIs   │ │ provider │ │  store   │
        └──────────┘ └──────────┘ └──────────┘
```

### 3.2 External systems

| System | Direction | Protocol | Data | Failure impact |
|---|---|---|---|---|

### 3.3 Actors and trust boundaries

| Actor | Trust level | Can reach | Notes |
|---|---|---|---|

## 4. Service decomposition

### 4.1 Service catalog

| Service | Responsibility | Owns data | Depends on | Scaling unit |
|---|---|---|---|---|

### 4.2 Boundary rationale
<Why these boundaries and not others. What is cohesive here.>

### 4.3 Deployment topology

```
┌────────────────────────────────────────────────────┐
│ Host (4 vCPU / 12 GB RAM)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │
│  │ backend  │ │ postgres │ │ qdrant   │ │ minio │ │
│  └──────────┘ └──────────┘ └──────────┘ └───────┘ │
└────────────────────────────────────────────────────┘
```

| Component | Runtime | CPU | Memory | Disk | Port |
|---|---|---|---|---|---|

### 4.4 Resource budget

| Component | Measured / estimated | Limit | Headroom |
|---|---|---|---|

## 5. Data architecture

### 5.1 Data stores

| Store | Type | Purpose | Data owned | Consistency | Backup |
|---|---|---|---|---|---|

### 5.2 Data ownership
<Exactly one service owns each data set. State it.>

### 5.3 Data flow

| From | To | Data | Transport | Volume | Retention |
|---|---|---|---|---|---|

### 5.4 Data lifecycle and retention

| Data set | Created by | Retention | Deleted by | Legal basis |
|---|---|---|---|---|

### 5.5 Multi-tenancy and isolation

| Concern | Mechanism | Enforced at | Verified by |
|---|---|---|---|

### 5.6 Consistency model
<Where strong consistency is required and where eventual is acceptable.>

## 6. Key flows

### 6.1 <Flow name>

| Step | Component | Operation | Latency | Failure handling |
|---|---|---|---|---|

### 6.2 <Flow name>

## 7. Reliability

### 7.1 Failure modes

| Failure | Detection | Response | User impact | Recovery |
|---|---|---|---|---|

### 7.2 Retry and timeout policy

| Call | Timeout | Retries | Backoff | Idempotent |
|---|---|---|---|---|

### 7.3 Degradation behavior
<What the system does when a dependency is down. Partial function is
acceptable; silent wrong answers are not.>

### 7.4 Recovery objectives

| Objective | Target | Mechanism |
|---|---|---|
| RTO | | |
| RPO | | |

### 7.5 Backup and restore

| Store | Backup method | Frequency | Retention | Restore test |
|---|---|---|---|---|

## 8. Scalability and performance

| Dimension | Current | Limit | Scaling strategy | Trigger |
|---|---|---|---|---|

### 8.1 Bottlenecks

### 8.2 Load shedding and rate limiting

## 9. Security

### 9.1 Trust boundaries and threat model

| Threat | Impact | Likelihood | Mitigation | Verified by |
|---|---|---|---|---|

### 9.2 Authentication and authorization

| Surface | Mechanism | Scope |
|---|---|---|

### 9.3 Secrets management

| Secret | Storage | Rotation | Scope |
|---|---|---|---|

### 9.4 Data protection

| Data class | At rest | In transit | In logs | Retention |
|---|---|---|---|---|

### 9.5 Tenant isolation
<The mechanism, and the test that proves it.>

## 10. Observability

| Signal | Type | Emitted by | Destination | Used for |
|---|---|---|---|---|

### 10.1 Metrics
### 10.2 Logging
### 10.3 Tracing
### 10.4 Alerting

| Alert | Condition | Severity | Action |
|---|---|---|---|

## 11. Deployment and operations

### 11.1 Environments

| Environment | Purpose | Data | Scale |
|---|---|---|---|

### 11.2 Release process
### 11.3 Rollback
### 11.4 Runbook index

| Runbook | Trigger |
|---|---|

## 12. Cost

| Component | Unit | Quantity | Unit cost | Total |
|---|---|---|---|---|

## 13. Design decisions

### 13.1 <Decision>

| Field | Value |
|---|---|
| Status | Proposed / Accepted / Superseded |
| Context | |
| Decision | |
| Alternatives considered | |
| Consequences | |
| Revisit when | |

## 14. Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|

## 15. Open questions

| ID | Question | Impact | Owner | Target date |
|---|---|---|---|---|

## Appendix A: Service catalog

## Appendix B: Data inventory

## Appendix C: API inventory

## Appendix D: Change log
```

---

## Rules for writing system design documents

1. **Show the topology.** A reader who cannot picture the deployment cannot evaluate the resource budget.
2. **State data ownership unambiguously.** Every data set has exactly one owner. Ambiguity here causes the distributed monolith.
3. **Budget the resources.** A design that does not fit the target host is not a design. Show the numbers against the limits.
4. **Design for the failure modes, not the happy path.** The failure table is the most-read section of a real system design document.
5. **Specify degradation behavior.** When a dependency is down, say what the system does. "Returns an error" is acceptable; "answers from stale data without saying so" is not.
6. **Make isolation testable.** State the mechanism and the test that proves it.
7. **Include cost.** A design without a cost estimate will be rejected in review.
8. **Record the rejected alternatives.** Especially for the storage and queue choices, which are the hardest to reverse.
9. **Keep the diagrams load-bearing.** A diagram that does not add information beyond the tables should be deleted.

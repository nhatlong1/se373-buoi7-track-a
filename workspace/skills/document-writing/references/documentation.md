# Documentation Template

**Use when:** documenting something that exists for someone who will use, operate, or extend it — README, how-to guide, tutorial, reference manual, runbook, onboarding guide.

**Do not use for:** specifying something that does not exist yet (use `technical-specification.md`).

---

## Choose the documentation type first

| Type | Reader's question | Structure |
|---|---|---|
| **README** | What is this, and how do I run it? | Overview, quick start, then links |
| **How-to guide** | How do I do X? | Task-oriented, goal in the title |
| **Tutorial** | Teach me by doing | Learning-oriented, step by step, with expected output |
| **Reference** | What are the exact parameters? | Exhaustive, alphabetical or grouped, no narrative |
| **Runbook** | What do I do when it breaks? | Symptom → diagnosis → action |
| **Onboarding** | How do I get productive here? | Environment, concepts, first task, where things live |

Mixing types is the most common documentation failure. A tutorial that stops to explain every parameter is exhausting; a reference that walks through a scenario is unusable. Pick one and commit.

---

## Template

```markdown
# <Title>

| Field | Value |
|---|---|
| Owner | <name or team> |
| Last updated | <YYYY-MM-DD> |
| Applies to | <version / release> |
| Audience | <who this is for> |

## 1. Overview

<One or two paragraphs. What this is, who it is for, what problem it
solves. If the reader has to read more than this to decide whether to
continue, the overview is too vague.>

### 1.1 Prerequisites

| Requirement | Version | How to check |
|---|---|---|

### 1.2 Terminology

| Term | Meaning |
|---|---|

## 2. Quick start

<The shortest path from nothing to a working result. If the reader
follows this and it does not work, the documentation is broken.>

```bash
# commands, copy-pasteable, no placeholders
```

**Expected output:**

```
```

## 3. <Main content>

### 3.1 <Task or topic>

<For a how-to: state the goal, then the steps, then the verification.>

**Goal:** <what the reader will have achieved>

**Steps:**

1. <action>
2. <action>

**Verify:** <how the reader confirms it worked>

**If it fails:** <the most likely failure and its fix>

### 3.2 <Task or topic>

## 4. Common tasks

| Task | How |
|---|---|
| <task> | <link to section> |

## 5. Configuration

| Setting | Type | Default | Required | Description |
|---|---|---|---|---|

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|

## 7. Limitations and caveats

<What does not work, what is unsupported, what is slow, what is
experimental.>

## 8. Related documentation

| Document | For |
|---|---|

## Appendix A: Full reference

## Appendix B: Glossary
```

---

## Rules for writing documentation

1. **Write for the reader's task, not the system's structure.** Organize by what the reader is trying to do, not by which module implements it.
2. **Every command must be runnable as written.** No `YOUR_API_KEY`, no `<path>`, no "adjust as needed". Use a real-looking value and say where to substitute it.
3. **Show expected output.** A reader who cannot tell whether the command worked will run it again, or worse, assume it failed.
4. **One step, one action.** "Install the dependencies and configure the environment" is two steps.
5. **Say what breaks.** If a step only works on a clean machine, say so.
6. **Document the failure modes.** The troubleshooting table is the highest-value section for a reader who is already stuck.
7. **Keep it current.** A stale document is worse than none, because it is trusted. Put a last-updated date and a version it applies to.
8. **Do not explain what the reader already knows.** Skip the tutorial of the language, the framework, and the shell.
9. **Prefer a copy-pasteable block over a prose description of a command.**
10. **Link out rather than duplicating.** If the API is documented elsewhere, link. Duplicated docs diverge.

# Code Review Report Template

**Use when:** a pending change — a diff, branch, or pull request — needs assessment before merge. The reader is the author, who wants to know what to fix and what to ignore.

**Do not use for:** documenting an existing codebase (use `code-analysis-report.md`).

---

## Template

```markdown
# Code Review: <change title>

| Field | Value |
|---|---|
| Author | <name or agent> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / In Review / Final |
| Change under review | <PR / branch / commit range> |
| Base | <base branch or commit> |
| Author of change | <who wrote it> |
| Reviewer | <who reviewed> |
| Verdict | Approve / Approve with comments / Request changes / Block |

## 1. Summary of the change

<3–5 sentences. What the change does and why it exists. The reader
should not need to read the diff to know what this is.>

### 1.1 Files touched

| File | Lines | Change | Risk |
|---|---|---|---|

### 1.2 What the reviewer verified

<What was actually checked: read, executed, tested, benchmarked. Be
explicit about what was only read and not run.>

## 2. Verdict

**<Approve | Approve with comments | Request changes | Block>**

<One paragraph of reasoning. If requesting changes, name the blocking
issues here in one line each.>

## 3. Findings

<Ordered by severity, highest first. Within a severity, ordered by file
and line.>

### 3.1 Blocking

#### B1. <Short title>

| Field | Value |
|---|---|
| Severity | Blocking |
| Location | `path/to/file.py:142` |
| Category | Correctness / Security / Data loss / Breaking change / Compliance |
| Confidence | High / Medium / Low |

**What is wrong**
<The defect, stated precisely.>

**Why it matters**
<The concrete consequence: wrong output, data loss, security exposure,
broken contract.>

**Suggested fix**
<The change, as a diff or a precise description.>

```python
# before
...
# after
...
```

### 3.2 Major

#### M1. <Short title>
<Same structure as above.>

### 3.3 Minor

#### m1. <Short title>
<Same structure, shorter.>

### 3.4 Nitpick

<Style, naming, comment wording. One line each. Do not pad this
section.>

## 4. What is good

<Specific strengths. Name the construct and the reason it works. This
section is read, and it tells the author what to keep.>

## 5. Testing assessment

| Aspect | Assessment |
|---|---|
| New behavior covered | <yes/no/partially — where> |
| Edge cases covered | <which> |
| Regression risk | <what could break> |
| Test quality | <assertions meaningful or superficial> |
| Manual verification needed | <what and why> |

## 6. Security and data handling

<Only if the change touches auth, input handling, secrets, PII, or
destructive operations. Otherwise state "Not applicable — no auth, input,
secret, or destructive paths touched.">

| Concern | Finding |
|---|---|

## 7. Performance and resource impact

<Only if relevant. Otherwise state "Not applicable.">

| Concern | Assessment |
|---|---|
| Query / algorithm cost | |
| Memory | |
| I/O | |
| Network | |

## 8. Open questions for the author

<Things that are not defects but that the reviewer needs answered.>

## 9. Review limitations

<What the reviewer did not check, could not check, or could not verify.
State it plainly.>

## Appendix A: Full findings list

| ID | Severity | Location | Summary |
|---|---|---|---|
```

---

## Severity definitions

Use these consistently. A reviewer who uses "critical" for a typo destroys the signal.

| Severity | Meaning | Effect on merge |
|---|---|---|
| **Blocking** | Causes incorrect behavior, data loss, a security hole, or a broken contract. | Must be fixed. |
| **Major** | Real defect or significant design problem, but bounded — wrong edge case, missing error handling, poor performance at scale. | Should be fixed before merge. |
| **Minor** | Small correctness or clarity issue with limited blast radius. | Author's discretion. |
| **Nitpick** | Style, naming, formatting. | Ignore at will. |

## Rules for writing findings

1. **One defect per finding.** If a finding needs "and", it is two findings.
2. **Locate it precisely.** `file:line` beats "in the parser".
3. **State the consequence, not the rule.** "This drops the last chunk when the document ends without a newline, so the final paragraph is never indexed" beats "handle the trailing newline case".
4. **Suggest a fix, do not write the whole patch.** The author owns the code. Give the shape of the fix and the reasoning.
5. **Do not report style as correctness.** If it is a style preference, it is a nitpick.
6. **Do not invent findings to look thorough.** A short review with three real findings beats a long one with fifteen speculative ones. Mark uncertain findings with low confidence.
7. **Say what is good.** It calibrates the author and makes the blocking findings credible.
8. **Never claim to have run something you did not run.** If you only read the code, say so in section 1.2 and section 9.

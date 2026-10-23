# Research Report Template

**Use when:** the agent investigated a question and produced evidence — experiments, measurements, surveys, source review, or a combination. The reader wants to know what was found, how it was found, and how much to trust it.

**Do not use for:** reviewing a pending change (use `code-review-report.md`), documenting an existing codebase (use `code-analysis-report.md`), or reviewing a specification (use `spec-analysis-report.md`).

---

## Template

```markdown
# <Research question as a title>

| Field | Value |
|---|---|
| Author | <name or agent> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / In Review / Final |
| Research question | <the question, stated precisely> |
| Scope | <what was investigated> |
| Out of scope | <what was deliberately not investigated> |

## Executive summary

<3–6 sentences. State the answer to the research question first, then the
single most important supporting finding, then the biggest caveat. A
reader who reads only this section should be able to act.>

## 1. Background and motivation

<Why this question matters. What decision or action the answer informs.
What was already known before this work started, and what remained open.>

## 2. Research question and scope

### 2.1 Question
<The question, stated so it can be answered yes/no or with a bounded
range. State any sub-questions.>

### 2.2 Scope
<What is included. What is explicitly excluded, and why.>

### 2.3 Definitions
<Key terms, operational definitions, and the measurement units used.>

## 3. Method

### 3.1 Approach
<The strategy. Why this approach answers the question.>

### 3.2 Data sources
| Source | Type | Size / coverage | Collected on | Notes |
|---|---|---|---|---|

### 3.3 Procedure
<The steps taken, in order, reproducibly enough that someone else could
repeat the work.>

### 3.4 Analysis method
<How data was processed. Statistical or qualitative techniques. Tools and
versions.>

### 3.5 Reproducibility
<Code, data, seeds, environment, versions. Where the artifacts live.>

## 4. Results

### 4.1 <Finding group>
<Each finding: what was observed, with the number, and the exhibit that
shows it.>

| Metric | Value | Baseline | Delta | Source |
|---|---|---|---|---|

### 4.2 <Finding group>

### 4.3 Summary of results
<Table of all findings against the research question.>

## 5. Analysis and discussion

### 5.1 Interpretation
<What the results mean. Why they might be what they are. Alternative
explanations considered and ruled out, or explicitly left open.>

### 5.2 Comparison with prior work
<Where this agrees or disagrees with existing findings. Cite.>

### 5.3 Implications
<What follows for the decision this research informs.>

## 6. Threats to validity

| Threat | Type | Likelihood | Mitigation applied | Residual risk |
|---|---|---|---|---|

<Cover: internal validity, external validity, construct validity,
statistical conclusion validity. Be specific about this study, not
generic.>

## 7. Conclusion

<Direct answer to the research question. Confidence level and the
conditions under which it holds.>

## 8. Recommendations

| # | Recommendation | Rationale | Priority | Owner | Effort |
|---|---|---|---|---|---|

## 9. Limitations and open questions

<What was not tested, what the sample could not represent, what remains
unanswered, and what would change the conclusion.>

## 10. Conclusion and next steps

<One paragraph. What happens next and when.>

## References

<Numbered, with enough detail to retrieve. Include access dates for
web sources.>

## Appendices

- Appendix A: Raw data or full result tables
- Appendix B: Tool versions and environment
- Appendix C: Instrument or prompt used
```

---

## Notes on filling this in

- **The method section is not optional.** A result without a method cannot be trusted or reproduced. If the method is short, say so explicitly rather than padding.
- **Report negative and null results.** A finding that did not replicate is a finding. Suppressing it is the fastest way to lose credibility.
- **Every number needs a baseline.** "Recall@5 = 0.87" is meaningless without the prior value or the target.
- **Threats to validity should be specific.** "Sample was small" is weak. "The 12 test messages were authored by the same person who wrote the prompt, so they share its blind spots" is useful.
- **Distinguish exploratory from confirmatory analysis.** If you looked at the data before forming the hypothesis, say so.

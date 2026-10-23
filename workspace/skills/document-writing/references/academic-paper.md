# Academic Paper / White Paper Template

**Use when:** writing a formal paper or a white paper. Two variants are given below — pick one and do not blend them.

| Variant | Reader | Register | Use when |
|---|---|---|---|
| **Academic paper** | Researchers, reviewers, peers | Formal, impersonal, citation-heavy | The work contributes to a literature, is being peer-reviewed, or is a course submission assessed on method |
| **White paper** | Decision-makers, technical and business stakeholders | Direct, recommendation-forward, minimal apparatus | The work informs a decision, a strategy, or an adoption choice |

---

## Variant A — Academic Paper

```markdown
# <Title>

| Field | Value |
|---|---|
| Authors | <names and affiliations> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / Submitted / Accepted |
| Venue / Course | |
| Keywords | <4–6 terms> |
| Abstract word count | <n> |

## Abstract

<150–250 words. Self-contained: problem, method, key result, significance.
No citations, no undefined abbreviations, no "in this paper we". A reader
who reads only the abstract should know whether to continue.>

## 1. Introduction

### 1.1 Context and motivation
<The problem, its scale, and why it matters now.>

### 1.2 Problem statement
<The precise question or gap.>

### 1.3 Objectives and contributions

| # | Contribution | Where addressed |
|---|---|---|

### 1.4 Scope and non-scope

### 1.5 Organization of the paper
<One short paragraph mapping sections to the argument.>

## 2. Background and related work

### 2.1 Background
<The concepts a reader needs to follow the method.>

### 2.2 Related work

| Study | Focus | Method | Dataset / setting | Findings | Limitation | Difference from this work |
|---|---|---|---|---|---|---|

<Position this work against the literature. "Our contribution is X,
which prior work does not address because Y.">

### 2.3 Research gap
<What is not yet known or solved.>

## 3. Method

### 3.1 Overview
<The approach, in a paragraph, before the detail.>

### 3.2 Problem formulation
<Formal definitions. Notation table.>

| Symbol | Meaning |
|---|---|

### 3.3 System or algorithm design
<Architecture, components, algorithms, pseudocode.>

### 3.4 Data and dataset

| Split | Size | Source | Preprocessing |
|---|---|---|---|

### 3.5 Evaluation protocol

| Metric | Definition | Why this metric |
|---|---|---|

### 3.6 Baselines and ablations
<What it is compared against, and what is removed to test each part.>

### 3.7 Implementation details
<Framework, versions, hardware, hyperparameters, seeds, training details.>

### 3.8 Reproducibility
<Code, data, environment, artifacts.>

## 4. Results

### 4.1 Main results

| Method | Metric 1 | Metric 2 | Metric 3 |
|---|---|---|---|

### 4.2 Ablation study

| Variant | Δ Metric | Interpretation |
|---|---|---|

### 4.3 Qualitative analysis
<Examples, error analysis, case studies.>

### 4.4 Statistical significance
<Tests, confidence intervals, effect sizes, multiple-comparison handling.>

## 5. Discussion

### 5.1 Interpretation
<What the results mean.>

### 5.2 Comparison with prior work
<Where this agrees or disagrees, and why.>

### 5.3 Practical implications
<What a practitioner should do differently.>

### 5.4 Limitations
<What the study cannot support.>

### 5.5 Threats to validity
<Internal, external, construct, statistical conclusion.>

## 6. Conclusion and future work

<What was established. What comes next.>

## Acknowledgments

## References

<Numbered, in a consistent style. Every citation in the text appears
here; every entry here is cited in the text.>

## Appendices

- Appendix A: Full result tables
- Appendix B: Prompts and hyperparameters
- Appendix C: Additional figures
```

---

## Variant B — White Paper

```markdown
# <Title>

| Field | Value |
|---|---|
| Author | <name or agent> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / In Review / Final / Published |
| Audience | <who this is for> |
| Keywords | <4–6 terms> |

## Executive summary

<200–300 words. The situation, the finding, and the recommended action.
Written so that a reader who stops here can still make the decision.>

## 1. The situation

<The context the reader is in. The pressure they are under. Why this
matters now. Written for someone who knows their own domain but not
this one.>

## 2. What we examined

<Scope, method, and evidence base. Brief but honest. The reader needs to
know how much weight to put on what follows.>

## 3. Findings

### 3.1 <Finding>

<Each finding: what it is, the evidence, and what it means for the
reader.>

### 3.2 <Finding>

### 3.3 Summary

| Finding | Evidence | Implication | Confidence |
|---|---|---|---|

## 4. Analysis

<The reasoning that connects findings to a conclusion. Where the
evidence is mixed, say so.>

## 5. Recommendations

| # | Recommendation | Rationale | Effort | Impact | Owner |
|---|---|---|---|---|---|

<Ordered by priority. Each recommendation must be actionable by a
specific role without further interpretation.>

## 6. Implementation considerations

<What it takes to act: dependencies, risks, sequencing, cost.>

## 7. Limitations and open questions

## 8. Conclusion

<One paragraph. The single sentence you want repeated.>

## References

## Appendix A: Methodology detail

## Appendix B: Supporting data
```

---

## Rules for writing papers and white papers

1. **The abstract is the hardest part.** Write it last, and make it self-contained. No undefined abbreviations, no citations, no forward references.
2. **Every claim in the abstract must be supported later.** The abstract is a promise about the body.
3. **Related work is a positioning argument, not a bibliography.** For each cited work, state what it did and how this work differs. A table works well when the literature is large.
4. **Report negative and null results.** A paper that only reports what worked is not credible, and reviewers look for the omitted experiment.
5. **State the limitations in the limitations section, not only in the discussion.** Do not bury them.
6. **Every number needs a baseline and a measure of uncertainty.** A metric without a comparison is decoration.
7. **Make the method reproducible.** Code, data, versions, seeds, hyperparameters. If it cannot be reproduced, it cannot be believed.
8. **Do not overclaim.** "Improves accuracy" and "improves accuracy on our dataset" are very different statements. Use the second.
9. **White papers are not academic papers.** A white paper leads with the recommendation and minimizes apparatus. An academic paper leads with the contribution and keeps the apparatus. Blending them serves neither reader.
10. **Check every citation.** Every reference in the list is cited in the text, and every citation in the text appears in the list. Mismatches are the most common reviewer complaint.

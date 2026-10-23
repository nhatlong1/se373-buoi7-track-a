---
name: "document-writing"
description: "Author any written deliverable - report, specification, design document, documentation, paper, or general prose - using a type-appropriate template plus shared writing-quality rules; use whenever the agent must produce a document, report, spec, design doc, README, or written analysis for a reader."
---

# Document Writing

Produce written deliverables that a real reader can act on. This skill supplies (a) a set of writing rules that apply to every document, and (b) a library of templates for common document types.

## When to Use

Trigger this skill when the agent is about to write anything a reader will consume as a document:

- A report of any kind: research, code review, code analysis, spec analysis, incident, status, audit, post-mortem.
- A technical specification, requirements document, or API contract.
- A design document: graphical/UI, architectural (code-level), or system (architecture-level).
- User or developer documentation: README, how-to guide, tutorial, reference manual, runbook.
- An academic paper, white paper, or technical memo.
- Any long-form written analysis, proposal, or proposal-adjacent document.

## When Not to Use

Do not load this skill for:

- Chat replies, emails, commit messages, code comments, docstrings, or issue comments. These are short-form and follow their own conventions.
- A one-paragraph summary of a document you are also writing. Write the document first, then summarize it.
- Editing an existing document where the user asked for a specific narrow change. Apply the relevant rules inline instead of restructuring.

## Procedure

1. **Classify the document type.** Pick the template from the index below. If the type genuinely does not fit any template, use `references/general.md`. If two templates fit, use the disambiguation notes in the index.
2. **Establish the contract before drafting.** Write down, explicitly, even if only in your reasoning:
   - **Audience** — who reads this, and what do they already know?
   - **Purpose** — what does this document enable the reader to do or decide?
   - **Decision** — if the reader must make one decision, what is it?
   - **Constraints** — length limit, required format, deadline, house style, required sections.
   - **Evidence available** — what can you actually cite? What is unknown?
   If the audience or purpose is unclear and cannot be inferred, ask one clarifying question rather than guessing. A document written for the wrong reader is wasted work.
3. **Gather evidence.** Collect the material the template's sections require. Never invent a number, a citation, a benchmark, an API signature, or a quote. Mark unknowns as `TBD` or `Unknown` rather than filling them plausibly.
4. **Outline against the template.** Use the template's section order as the default spine. Adapt it to the document — but do not delete the spine's load-bearing sections without a reason. If you drop a section, say why in the document or in your handover note.
5. **Draft** using the writing rules below. Write the summary section last, after the body is settled.
6. **Self-review** against the checklist at the end of this file. Fix what fails.
7. **Deliver** the document with its metadata block intact, plus a short handover note listing: what you wrote, what you could not verify, and what the reader must supply or decide.

## Writing Rules

These apply to every document produced with this skill, regardless of template.

### Purpose and audience

1. **Write the one-sentence purpose first.** "This document tells X how to Y so that Z." If you cannot write that sentence, you do not yet know what to write.
2. **Match depth to the reader.** An executive needs the decision, the risk, and the cost. An implementer needs the interface, the edge cases, and the failure modes. A reviewer needs the claim, the evidence, and the limitation. Writing one document for all three audiences usually means it serves none.
3. **State scope and non-scope.** Non-scope is what prevents the "why did you not cover X" question. It is not filler.

### Structure

4. **Order sections by the reader's questions, not by the order you did the work.** Nobody cares that you read the code before the spec.
5. **Lead with the answer.** Reports open with the conclusion. How-tos open with the task. Specifications open with scope. Specifications that build up to the requirement are read once.
6. **One idea per paragraph, one topic per section.** If a paragraph needs "also" or "additionally", split it.
7. **Make every heading readable on its own in a table of contents.** "Results" is weak. "Recall@5 fell below the 0.85 threshold after the filter change" is strong.
8. **Do not repeat content.** Cross-reference by section number instead. Duplicated content drifts out of sync and readers trust the wrong copy.

### Language

9. **Prefer concrete nouns and verbs.** "The service rejects the request" over "A rejection is performed by the service."
10. **Use the active voice.** "The reviewer blocks the message" over "The message is blocked by the reviewer." Reserve the passive for the actor genuinely being unknown or irrelevant.
11. **Use the right tense.** Present for current behavior and for requirements, past for what happened, future only for genuine plans. Do not write "the system will return an error" in a spec describing current behavior.
12. **Cut hedges and intensifiers.** very, really, quite, basically, actually, simply, just, clearly, obviously, essentially, in order to, it is important to note that, it should be noted that. Each one weakens the sentence without adding meaning.
13. **Match requirement strength to intent.** Use MUST / SHOULD / MAY (or "must" / "should" / "may") deliberately. "Must" means a test can fail if it is violated. If nothing can fail, it is not a must.
14. **Define a term once, then use it consistently.** If there are more than a handful of domain terms, keep a glossary. Do not alternate between "customer", "client", and "buyer" for the same thing.
15. **Give numbers a unit and a baseline.** "40% faster" is incomplete without "than what". "2.1 GB" is incomplete without "peak RSS".
16. **Define jargon on first use.** Assume the reader is smart but new to this codebase, this domain, or this project.

### Evidence and honesty

17. **Make every checkable claim traceable.** Attach a source: `file:line`, test name, URL, measurement, or an explicit "assumption". A claim with no source is an opinion wearing a suit.
18. **Mark unknowns as unknowns.** `TBD`, `Unknown`, `Not measured`. A plausible invented number is worse than a blank, because it will be cited.
19. **State confidence and what would change the conclusion.** "This holds for the 2 workspaces tested; it would likely fail above 50 concurrent sessions, which was not tested."
20. **Separate fact, inference, and recommendation.** Label them when they could be confused. A recommendation presented as a finding is how bad decisions get made.

### Presenting information

21. **Match the form to the content.** Tables for comparison and for anything with parallel fields. Ordered lists for sequences and procedures. Prose for argument, narrative, and nuance. A table of prose is unreadable; a paragraph of tabular data is unscannable.
22. **Number figures, tables, and code blocks**, and refer to them by number ("see Table 3"). Unnumbered exhibits get mis-cited.
23. **Keep paragraphs short.** Break at topic shifts. If a paragraph exceeds roughly six lines on screen, it probably contains two ideas.
24. **Front-load.** Respect the reader's time: summary first, detail after, appendices last.

### Mechanics

25. **Be consistent** in terminology, capitalization, heading case, date format, and number format throughout the document.
26. **Make figures accessible.** Alt text for every image and diagram. Never use color as the only carrier of meaning. Do not rely on a table's visual layout to convey a relationship.
27. **Include metadata**: title, author or owner, date, version, status, and reviewers. A document without an owner has no one to ask when it goes stale.
28. **Include a change log** for any living document.
29. **Proofread for defects**: broken section references, wrong numbers, leftover `{{PLACEHOLDERS}}`, inconsistent terms, headings with no content beneath them, and content that contradicts an earlier section.

## Shared Report Spine

All four report templates (research, code review, code analysis, spec analysis) share this spine, because all four answer the same sequence of reader questions. Each template specializes it; none of them drops it.

| Spine section | Reader question it answers |
|---|---|
| Metadata header | Who wrote this, when, and can I trust this version? |
| Executive summary | What is the answer, in 30 seconds? |
| Scope and method | What was examined, how, and what was deliberately excluded? |
| Findings | What did I observe? Organized by theme, not by document order. |
| Evidence | Where does each finding come from? |
| Analysis | Why does each finding matter? Severity, impact, likelihood. |
| Conclusion / verdict | So what is the overall judgment? |
| Recommendations | What should happen next, in what order, owned by whom? |
| Limitations and open questions | What did I not check, and what would change the answer? |
| Appendices | The raw material, long listings, glossary, full data. |

"Evidence" and "Analysis" are often embedded inside each finding rather than split into separate top-level sections — a finding that carries its own source and its own severity is easier to act on than one that must be cross-referenced. Keep the content, not necessarily the heading.

The two sections most often missing, and the two that make a report credible, are **Scope and method** and **Limitations**. If a report is short, cut the executive summary's length, not those two.

## Template Index

All templates live flat in `references/`. Read the chosen template before drafting.

| Template | Use for | When to use |
|---|---|---|
| `references/general.md` | Any document with no preset shape | Default catch-all. Instructs the writer to work freely while keeping the writing rules. Use when no other template fits, or when the user explicitly asks for an unstructured document. |
| `references/research-report.md` | Investigation of a question with evidence | The agent gathered data, ran experiments, or surveyed sources to answer a question. Includes method, search strategy, and threats to validity. |
| `references/code-review-report.md` | Review of a proposed change | A diff, branch, or PR needs a verdict before merge. Findings are severity-ranked with `file:line` and a suggested fix. |
| `references/code-analysis-report.md` | Study of an existing codebase | The agent is documenting how a system actually works, its dependencies, and its risks. Descriptive, not evaluative of a pending change. |
| `references/spec-analysis-report.md` | Analysis of a specification document | A spec must be reviewed for gaps, ambiguity, contradictions, feasibility, and testability before implementation. Produces a requirement inventory and a traceability matrix. |
| `references/technical-specification.md` | Normative requirements and interfaces | The document defines what a system must do: requirements with IDs, interfaces, data model, error handling, acceptance criteria. |
| `references/documentation.md` | User and developer documentation | README, how-to guide, tutorial, reference manual, runbook. Task-oriented, copy-pasteable, with troubleshooting. |
| `references/graphical-design-document.md` | Design language, UI description, UI requirements | The document defines how an interface looks and behaves: visual language, component inventory, screen states and flows, and testable UI requirements. |
| `references/architectural-design-document.md` | Code-level design | The document defines modules, classes, interfaces, data structures, and control flow inside one application. |
| `references/system-design-document.md` | System-level architecture | The document defines services, deployment topology, data stores, data flows, scaling, reliability, and security across a whole system. |
| `references/academic-paper.md` | Paper or white paper | A formal write-up with abstract, related work, method, results, and references. Includes a white-paper variant for executive audiences. |

### Choosing between close relatives

- **Code review vs. code analysis.** Review = a *pending change* and a merge verdict. Analysis = an *existing codebase* and an understanding of it. If there is a diff, use review. If there is a repository, use analysis.
- **Architectural design vs. system design.** Architectural = inside one application: modules, classes, interfaces, control flow. System = across services: boundaries, deployment, data ownership, failure modes. If it spans processes, use system design.
- **Technical specification vs. design document.** Specification = *what* must be true, in testable terms, with no commitment to implementation. Design document = *how* it will be built. A spec that describes classes is a design document.
- **Research report vs. academic paper vs. white paper.** Research report = the agent's own investigation, method and results. Academic paper = a contribution to a literature, with related work and citations. White paper = a research report aimed at decision-makers, with recommendations for action and minimal formal apparatus.
- **Documentation vs. technical specification.** Documentation = how to use or operate something that exists. Specification = what to build.

## Self-Review Checklist

Run this before delivering. Each item is pass/fail.

- [ ] The purpose sentence is present and the document serves the stated reader.
- [ ] Scope and non-scope are stated.
- [ ] The summary states the answer, not the topic.
- [ ] Every heading is meaningful read alone in a table of contents.
- [ ] No paragraph mixes two ideas.
- [ ] No hedges or intensifiers from the cut list remain.
- [ ] Every checkable claim has a traceable source, or is labelled as an assumption.
- [ ] No invented numbers, citations, benchmarks, or API signatures.
- [ ] Numbers carry units and a baseline.
- [ ] Terms are used consistently; jargon is defined on first use.
- [ ] Tables are used for comparison, lists for sequences, prose for argument.
- [ ] Figures and tables are numbered and referenced by number.
- [ ] Metadata block is complete: title, owner, date, version, status.
- [ ] No `{{PLACEHOLDER}}` text remains.
- [ ] Section cross-references resolve.
- [ ] Figures have alt text; no meaning is carried by color alone.
- [ ] Limitations and open questions are stated.
- [ ] The document does not contradict itself.

## Output Specification

- Write the document to the workspace `output/` directory unless the user specifies another path.
- Keep the template's metadata block at the top of the file, filled in. If a field is unknown, write `TBD` rather than deleting the line.
- Use Markdown unless the user asks for another format.
- Deliver with a short handover note: what the document is, who it is for, what you could not verify, and what the reader must supply or decide.

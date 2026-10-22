---
name: "authoring-skills"
description: "Guidelines and instructions for authoring or updating modular skills in workspace/skills/."
---

# Authoring Skills

## When to Use
Use this skill whenever creating a new skill or updating an existing skill under `workspace/skills/`.

## Principles
1. **Single Responsibility**: Each skill must have exactly one clear, dedicated responsibility.
2. **Slug and Description Rules**:
   - The directory name and frontmatter `name` must match exactly and use lower-case kebab-case (e.g. `csv-analysis`).
   - The `description` must be a single line, keyword-dense, concisely stating when and why the agent should use the skill.
3. **Directory Layout**:
   - `skills/<slug>/SKILL.md`: Main instructions and workflow.
   - `skills/<slug>/references/`: Optional supporting reference documents, templates, or domain assets.
4. **Authoring Procedure**:
   - Read `skills/authoring-skills/references/skill-template.md` using `read_file` if you need a starting template.
   - Write `skills/<slug>/SKILL.md` using `write_file`.
   - Write any accompanying reference documents under `skills/<slug>/references/<name>.md` using `write_file`.
5. **Freshness Caveat**:
   - Newly authored skills become part of the available skills catalog on the next conversational turn, after catalog rescanning.

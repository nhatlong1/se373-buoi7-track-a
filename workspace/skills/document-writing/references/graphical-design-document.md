# Graphical / UI Design Document Template

**Use when:** the document defines how an interface looks and behaves — design language, visual system, component inventory, screen states and flows, and testable UI requirements.

**Do not use for:** backend architecture (use `system-design-document.md`), or a written specification of behavior with no visual component (use `technical-specification.md`).

---

## Template

```markdown
# <Product> UI Design Document

| Field | Value |
|---|---|
| Author | <name or agent> |
| Date | <YYYY-MM-DD> |
| Version | <v1.0> |
| Status | Draft / In Review / Final / Implemented |
| Owner | |
| Applies to | <release / version> |
| Related documents | <spec, design system link, prototype link> |

## 1. Introduction

### 1.1 Purpose
<What this document defines.>

### 1.2 Scope
<Which surfaces, platforms, and states are covered.>

### 1.3 Non-scope
<What is not defined here — backend behavior, marketing pages, native mobile.>

### 1.4 Design principles

<Three to five principles, each with a one-line rationale. These are the
tie-breakers when the rules below conflict.>

| # | Principle | Rationale |
|---|---|---|

### 1.5 Target users and context of use

| User | Goal | Context | Constraints |
|---|---|---|---|

## 2. Design language

### 2.1 Visual foundations

| Token | Value | Usage |
|---|---|---|
| Color / primary | | |
| Color / surface | | |
| Color / text | | |
| Typography / family | | |
| Typography / scale | | |
| Spacing / base unit | | |
| Radius | | |
| Elevation / shadow | | |
| Motion / duration | | |

### 2.2 Color and contrast

| Pairing | Foreground | Background | Contrast ratio | WCAG level |
|---|---|---|---|---|

<State the target conformance level. Do not rely on color alone to
carry meaning anywhere in the product.>

### 2.3 Iconography and imagery

| Asset | Style | Sizes | Usage |
|---|---|---|---|

### 2.4 Layout and grid

| Breakpoint | Columns | Gutter | Margin | Behavior |
|---|---|---|---|---|

### 2.5 Voice and tone

| Context | Tone | Do | Do not |
|---|---|---|---|

## 3. Component inventory

<One row per component. This is the index into sections 4 and 5.>

| ID | Component | Category | Variants | States | Section |
|---|---|---|---|---|---|

## 4. Component specifications

### 4.1 <Component name>

**Purpose.** <What it is for.>

**Anatomy.** <The parts, labeled.>

```
┌──────────────────────────────┐
│ [icon] Label            [⋯]  │
│ Subtext or helper text       │
│ ──────────────────────────── │
│ [action]                      │
└──────────────────────────────┘
```

| Part | Element | Behavior |
|---|---|---|

**Variants**

| Variant | When to use | Difference |
|---|---|---|

**States**

| State | Trigger | Appearance | Allowed actions |
|---|---|---|---|
| Default | | | |
| Hover | | | |
| Focus | | | |
| Active | | | |
| Disabled | | | |
| Loading | | | |
| Error | | | |
| Empty | | | |

**Content rules**

| Rule | Detail |
|---|---|
| Maximum length | |
| Truncation | |
| Required label | |
| Placeholder vs. label | |

**Accessibility**

| Concern | Requirement |
|---|---|
| Keyboard | |
| Screen reader | |
| Focus order | |
| Target size | |

**Usage**

```html
<!-- correct -->
```

```html
<!-- incorrect -->
```

## 5. Screen specifications

### 5.1 <Screen name>

**Purpose.** <What the user accomplishes here.>

**Entry points.** <How the user gets here.>

**Layout.**

```
┌───────────────────────────────────────────────┐
│ Header                                        │
├───────────────────────────────────────────────┤
│                                               │
│  Main content area                            │
│                                               │
├───────────────────────────────────────────────┤
│ Footer / action bar                           │
└───────────────────────────────────────────────┘
```

**Elements.**

| Element | Component | Behavior |
|---|---|---|

**Data and states.**

| State | Condition | Display | User action |
|---|---|---|---|
| Loading | | | |
| Populated | | | |
| Empty | | | |
| Partial | | | |
| Error | | | |
| Permission denied | | | |

**Responsive behavior.**

| Breakpoint | Layout change |
|---|---|

**Accessibility.**

## 6. Flows

### 6.1 <Flow name>

```
[Entry] → [Step 1] → [Step 2] → [Decision]
                        ↓
                  [Error path]
```

| Step | Screen | User action | System response | Next |
|---|---|---|---|---|

### 6.2 Error and empty states
<Every flow needs a defined failure path.>

## 7. Interaction and motion

| Interaction | Trigger | Duration | Easing | Reduced-motion behavior |
|---|---|---|---|---|

## 8. Content and microcopy

| Location | Text | Max length | Notes |
|---|---|---|---|

## 9. UI requirements

<The testable requirements. Same conventions as a technical
specification: stable IDs, MUST / SHOULD / MAY, verification method.>

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-UI-001 | | MUST | |

## 10. Design tokens and assets

| Asset | Location | Format | Owner |
|---|---|---|---|

## 11. Accessibility conformance

| Guideline | Level | Status | Notes |
|---|---|---|---|
| WCAG | 2.2 AA | | |

## 12. Open questions

| ID | Question | Impact | Owner | Target date |
|---|---|---|---|---|

## Appendix A: Component index

## Appendix B: Screen inventory

## Appendix C: Change log
```

---

## Rules for writing UI design documents

1. **Every component needs all eight states.** Default, hover, focus, active, disabled, loading, error, empty. A component spec that omits the error state is incomplete, and the error state is where the real design work is.
2. **Specify focus explicitly.** Keyboard focus is where most design systems are vague and where accessibility actually fails.
3. **Never rely on color alone.** Every state that is signaled by color must also be signaled by text, shape, icon, or position.
4. **Give real content.** "Lorem ipsum" hides layout problems. Use realistic Vietnamese or English strings of the right length.
5. **Show the wrong version too.** The incorrect example teaches more than the correct one.
6. **Define the empty state.** It is the first thing a new user sees and the most commonly skipped.
7. **Specify reduced-motion behavior.** Motion preferences are an accessibility requirement, not a nicety.
8. **Keep tokens and components consistent.** If a value appears in two places, it belongs in the token table.
9. **Requirements must be verifiable.** "MUST be usable" is not a requirement. "MUST be operable by keyboard alone, with a visible focus indicator on every interactive element" is.

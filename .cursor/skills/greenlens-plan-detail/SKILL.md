---
name: greenlens-plan-detail
description: >-
  Expands roadmap into an execution markdown under docs/plans/ from the
  canonical docs/AI_Service_Development_Plan.md plus user priorities. Invoke via
  /greenlens-plan-detail or /plan when you need granular steps before coding.
disable-model-invocation: true
---

# GreenLens — Detailed implementation planning

## When to use

- Workspace slash `/plan` or `@greenlens-plan-detail`.
- You need actionable sequence, touched files, and acceptance criteria before `/execute`.

## Instructions

Gather from the prompt or ask briefly:

1. Phase or theme (examples: Phase 1 EXIF/geo, Phase 2 duplicates).
2. Any decisions already documented in canonical plan §8.

Write **one new** markdown file under `docs/plans/` using either:

- `phase-{n}-{slug}.md`
- `{YYYY}-{MM}-{DD}-{slug}.md` for spikes

Every plan file MUST include sections for:

| Section | Contents |
|---------|----------|
| Goals / non-goals | In and out of scope tied to phases in master plan |
| BR & endpoints | Copy or reference verbatim target responses from `@docs/AI_Service_Development_Plan.md` |
| Execution checklist | Ordered steps for one merge-sized chunk of work |
| Files & modules | Tables of files to touch or create mapping to `app/`, tests, infra |
| Test plan | Fixtures, happy path plus primary edge classes from plan pitfalls |
| Risks | Fallbacks referencing plan §§6–§9 |

Do **not** replace `docs/AI_Service_Development_Plan.md` — augment it locally.

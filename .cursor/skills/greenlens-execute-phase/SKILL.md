---
name: greenlens-execute-phase
description: >-
  Executes GreenLens AI Service work strictly by phase reading
  docs/AI_Service_Development_Plan.md and optional docs/plans/*.md detail
  plans. Invoke via /greenlens-execute-phase or /execute project command when
  user wants backlog implementation aligned to BR/endpoints without scope creep.
disable-model-invocation: true
---

# GreenLens — Execute phase workflow

## When to use

- Workspace slash `/execute`, `/excute`, or `@greenlens-execute-phase`.
- Explicit request to ship a numbered phase endpoint, `app/core/` module, or matching tests from project documentation.

## Instructions

### Before coding

1. Load `docs/AI_Service_Development_Plan.md` and settle **phase**, **endpoint**, **BR**.
2. If `docs/plans/` contains a markdown plan for this scope, follow it in order through its checklist items.
3. Check plan sections on traceability and open questions — do not redefine API contract without aligning to repo docs first.

### While implementing

- Keep routes thin; put logic under `app/core/`, integrations under `app/services/`, schemas under `app/models/` as in plan §3.
- Settings only via `app/config.py` and env; mirror new variables into `.env.example`.
- Prefer structured logs where inference touches production audit paths BR-AI-005.

### After changes

- Add or extend tests under `tests/unit/` or `tests/integration/` keyed to BR IDs from matrix §7 in the canonical plan doc.
- Run `uv run ruff check .` and `uv run pytest` unless the repo documents different commands.

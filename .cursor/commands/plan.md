---
description: Tạo file plan chi tiết trong docs/plans (@greenlens-plan-detail skill)
---

# /plan — Kế hoạch chi tiết trong `docs/plans/`

Project command trong `.cursor/commands/` ([Skills doc](https://cursor.com/docs/skills.md)).

Đọc **`@greenlens-plan-detail`** hoặc `.cursor/skills/greenlens-plan-detail/SKILL.md` và làm đúng hướng dẫn trong đó.

## Gán subagent

| Bước | Subagent | Vai trò |
|------|----------|---------|
| 0 (khuyến nghị) | `/greenlens-scout` | Dò repo **read-only**, so với plan §3 — gợi ý checklist + chia agent song song |
| 1 | Agent chính (+ skill plan) | Viết file `docs/plans/*.md` theo skill |
| 2 (sau khi có plan) | `/greenlens-contract-audit` | Tuỳ chọn — so sánh draft plan với `docs/AI_Service_Development_Plan.md` trước khi code |

**Bước 1 — Đọc source:** `docs/AI_Service_Development_Plan.md` (phase, endpoint, pitfalls, §7 BR matrix).

**Bước 2 — Làm rõ với user (nếu chưa có trong prompt):**

- Phase / feature cụ thể.
- Deadline hoặc ưu tiên MVP.

**Bước 3 — Tạo file** dưới `docs/plans/` theo convention trong skill (`phase-{N}-{slug}.md` hoặc `YYYY-MM-DD-{slug}.md`).

**Bước 4:** Trong phiên chỉ **tạo/cập nhật** file plan và gỏi trong chat đường dẫn file; không tự lan sang implement code trừ khi user sau đó dùng **`/execute`**.

---
description: Thực thi phase theo docs plan + docs/plans (@greenlens-execute-phase skill)
---

# /execute — Thực thi theo kế hoạch dự án

Tệp này nằm trong **project commands**: `.cursor/commands/*.md`; tên file (không đuôi) = lệnh sau `/` trong Agent (xem [Cursor — Agent Skills](https://cursor.com/docs/skills.md): phần *Migrating rules and commands to skills*).

Đọc skill **`@greenlens-execute-phase`** hoặc `.cursor/skills/greenlens-execute-phase/SKILL.md` và làm đúng từng bước trong đó (frontmatter skill phải trùng tên thư mục — đúng chuẩn [Skill format](https://cursor.com/docs/skills.md)).

## Gán subagent (Cursor)

| Bước | Subagent | Khi nào |
|------|----------|---------|
| 0 (tuỳ chọn) | `/greenlens-scout` | Phạm vi lớn hoặc repo vừa đổi — **read-only**, gợi ý chia song song |
| HTTP / schema | `/greenlens-api-v1` | Router, Pydantic `app/models/` |
| Logic / tích hợp | `/greenlens-core-services` | `app/core`, `app/services`, `app/workers` |
| ML offline | `/greenlens-ml-artifacts` | Chỉ công việc dưới `ml/` |
| Container | `/greenlens-docker-infra` | `docker/`, compose, env đi kèm |
| Test / BR | `/greenlens-test-br` | `tests/**`, map §7 |
| Sau merge / release | `/greenlens-contract-audit` | Read-only đối chiếu plan |
| Kẹt lỗi khi làm | `/greenlens-debug` | Cô lập nguyên nhân trước khi vá (xem `/debug`) |

Agent cha **có thể chạy song song** các subagent có `is_background: true` và **phân vùng path** rõ (tránh cùng file). Tham chiếu: [Subagents](https://cursor.com/docs/subagents.md).

**Ngữ cảnh bắt buộc:**

1. Mở và tham chiếu `docs/AI_Service_Development_Plan.md` — phase hiện tại và backlog liên quan.
2. Nếu user chỉ định file trong `docs/plans/`, ưu tiên file đó; nếu không, hỏi user: **Phase nào?** **Endpoint/module nào?** có cần tạo plan chi tiết trước không.

**Việc cần làm ngay sau khi có scope:**

- Triển khai code/tests tối thiểu để đóng deliverable của phase đó (theo mục từng phase trong plan).
- Chạy kiểm thử và lint của repo sau thay đổi.

Nếu phạm vi chưa rõ: đề xuất 2–3 bước nhỏ tiếp theo rồi thực hiện bước 1 trong phiên hiện tại.

---
description: Alias /execute — cùng skill greenlens-execute-phase
---

# /excute

Cùng **`/execute`**. Workspace command basename = slash name ([docs](https://cursor.com/docs/skills.md)).

Đọc **`@greenlens-execute-phase`** hoặc `.cursor/skills/greenlens-execute-phase/SKILL.md`.

**Gán subagent:** giống hệt **`/execute`** — xem bảng trong [`execute.md`](execute.md) (`/greenlens-scout` → `/greenlens-api-v1` / `/greenlens-core-services` / `/greenlens-ml-artifacts` / `/greenlens-docker-infra` / `/greenlens-test-br` / `/greenlens-contract-audit` / `/greenlens-debug`).

**Ngữ cảnh bắt buộc:**

1. Mở và tham chiếu `docs/AI_Service_Development_Plan.md` — phase hiện tại và backlog liên quan.
2. Nếu user chỉ định file trong `docs/plans/`, ưu tiên file đó; nếu không, hỏi user: **Phase nào?** **Endpoint/module nào?** có cần tạo plan chi tiết trước không.

**Việc cần làm ngay sau khi có scope:**

- Triển khai code/tests tối thiểu để đóng deliverable của phase đó (theo mục từng phase trong plan).
- Chạy kiểm thử và lint của repo sau thay đổi.

Nếu phạm vi chưa rõ: đề xuất 2–3 bước nhỏ tiếp theo rồi thực hiện bước 1 trong phiên hiện tại.

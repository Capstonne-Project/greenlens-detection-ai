---
description: Bugfix — tái hiện, patch tối thiểu, test + lint, không đổi scope
---

# /fix — Sửa lỗi có kiểm soát

Project command: `.cursor/commands/fix.md` (Cursor [Skills](https://cursor.com/docs/skills.md)).

## Gán subagent

| Bước | Subagent | Vai trò |
|------|----------|---------|
| 1 (nếu chưa rõ gốc) | `/greenlens-debug` | Giả thuyết + cô lập tầng |
| 2 | Theo lớp lỗi | `/greenlens-api-v1`, `/greenlens-core-services`, `/greenlens-docker-infra`, `/greenlens-ml-artifacts` |
| 3 | `/greenlens-test-br` | Regression / test BR |
| 4 (tuỳ chọn) | `/greenlens-contract-audit` | Read-only không lệch contract sau patch |

1. **Tái hiện:** Xác định symptom (HTTP status, traceback, testcase fail). Chạy lệnh/tệp test cụ thể để tái hiện nếu chưa rõ.

2. **Phạm vi:** Sửa tối thiểu cho đủ testcase / hành vi đúng — không refactor rộng, không đổi contract API trừ khi user đồng ý hoặc ghi rõ trong `docs/AI_Service_Development_Plan.md`.

3. **Kiểm tra:** Viết/regression test nếu thiếu. `uv run pytest` và lint (vd `uv run ruff check .`) sau khi sửa.

4. **Ghi nhận:** Ngắn gọn trong tóm tắt đổi gì và tại sao (giả định, edge case đã cover).

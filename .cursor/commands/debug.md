---
description: Debug có giả thuyết, chứng cứ và đối chiếu master plan trong docs/
---

# /debug — Gỡ lỗi có hệ thống

Project command: `.cursor/commands/debug.md` ([Cursor Skills](https://cursor.com/docs/skills.md)).

## Gán subagent

| Vai trò | Subagent |
|---------|----------|
| **Chính** | `/greenlens-debug` — delegate toàn quy trình dưới đây cho subagent này |
| Hỗ trợ | `/greenlens-scout` — read-only khi chưa rõ file/flow liên quan |
| Sau gốc lỗi | `/fix` + subagent lớp + `/greenlens-test-br` |

1. **Thu thập bằng chứng:** Log (structlog/console), traceback đầy đủ, request/response curl hoặc TestClient dump, phiên bản config/env có liên quan (không paste secret).

2. **Giả thuyết có thứ tự:** Liệt kê 3–5 nguyên nhân khả dĩ; với mỗi cái, nêu cách **falsify** bằng một bước kiểm tra nhanh (log, breakpoint, test nhỏ).

3. **Cô lập:** Thu hẹp tới một module/`app/core`/`app/api/v1`/settings — tránh đổi nhiều lớp cùng lúc cho đến khi chứng minh được gốc lỗi.

4. **BR & plan:** Đối chiếu hành vi mong đợi với `docs/AI_Service_Development_Plan.md` (đặc biệt EXIF/GPS/threshold inference/timeout §6).

5. **Kết luận:** Sau khi tìm ra gốc, chuyển sang sửa theo **`/fix`** (patch nhỏ + test).

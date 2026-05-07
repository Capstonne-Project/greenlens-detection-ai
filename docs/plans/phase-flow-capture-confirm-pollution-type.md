# Plan — Luồng chụp ảnh → xác nhận loại ô nhiễm (demo + API)

**Nguồn chuẩn:** `docs/AI_Service_Development_Plan.md` (§1 hai luồng inference, §5.1 demo app flow màn Camera / Sau khi chụp, Phase 3 `POST /classify`, §7 BR-AI-001).
**Mục tiêu sprint:** Cho phép **test end-to-end tối thiểu** luồng user chụp hoặc chọn ảnh → nhận gợi ý loại ô nhiễm (`action`, `confidence`) → **user xác nhận / chỉnh** ngay trong UI demo (không phụ thuộc .NET hay storage URL).

---

## Goals / non-goals

**Goals**

- Giữ contract JSON hiện có **`POST /api/v1/classify`** (`image_url`) cho .NET và pipeline đã có.
- Thêm **`POST /api/v1/classify-upload`** (multipart ảnh) để test nhanh từ browser/mobile **không cần upload S3** — mô phỏng “chụp xong gửi thẳng AI”.
- Static page **`/demo/demo_capture_classify.html`**: input file + `capture="environment"` trên mobile, hiển thị `AUTO_FILL` / `SUGGEST` / `KEEP_USER_CHOICE` và UI xác nhận loại (manual override hiển thị).
- Ghi log inference kiểu hiện tại (`model_version`, latency) để chuẩn bị BR-AI-005 sau.

**Non-goals**

- Không thay `docs/AI_Service_Development_Plan.md`.
- Không làm full React Native demo app trong repo Python (App thật vẫn theo §5.1 RN); demo web chỉ để QA/stakeholder thử luồng logic.
- Không binding submit báo cáo .NET trong phiên này — chỉ “xác nhận loại” ở phía client demo.

---

## BR & endpoints

**BR-AI-001** (canonical §Phase 3 / §7):

- Confidence ≥ **0.8** → coi là đủ mạnh cho **AUTO_FILL**.
- **0.5–0.8** → **SUGGEST**.
- Dưới 0.5 → **KEEP_USER_CHOICE** (“Tiếng ồn” không infer từ ảnh — Option A trong master).

**Response mục tiêu** (giữ khớp plan gốc, trường có thể bổ sung không phá backward-compat):

```json
{
  "predictions": [{"class": "TRASH", "confidence": 0.92, "bbox_count": 5}],
  "primary_class": "TRASH",
  "confidence": 0.92,
  "action": "AUTO_FILL",
  "model_version": "v0.1.0-yolov8n",
  "inference_time_ms": 230,
  "noise_supported": false
}
```

**Endpoint demo bổ sung:**

| Method | Path | Mục đích |
|--------|------|----------|
| POST | `/api/v1/classify-upload` | `multipart/form-data` field `image` — cùng `ClassifyResponse`. |
| GET | `/demo/demo_capture_classify.html` | Trang tĩnh (qua `StaticFiles`). |

---

## Execution checklist

1. Refactor nhẹ `classify`: hàm dùng chung `bytes` → `ClassifyResponse` để tránh trùng lặp giữa `image_url` và upload.
2. Implement `POST /api/v1/classify-upload` (Annotated `UploadFile`).
3. Thêm `static/demo_capture_classify.html`: chụp/chọn ảnh → `fetch` multipart → render kết quả → nút xác nhận loại (dropdown 5 loại §BR-REP-005, nhãn noise disabled khi `noise_supported: false`).
4. Mount `StaticFiles` trong `app/main.py` prefix `/demo`.
5. Integration test multipart (JPEG minimal).
6. Chạy `uv run ruff check .` và `uv run pytest`.

---

## Files & modules

| Thành phần | Path |
|------------|------|
| API classify | `app/api/v1/classify.py` — shared builder + `/classify-upload` |
| Static demo | `static/demo/demo_capture_classify.html` |
| Entry | `app/main.py` — mount `/demo` |
| Tests | `tests/integration/test_api_v1_p1_p3.py` hoặc file mới `tests/integration/test_capture_classify_flow.py` |

---

## Test plan

| Case | Kỳ vọng |
|------|---------|
| JPEG nhỏ qua multipart | 200, có `model_version`; stub khi không có weights (`KEEP_USER_CHOICE`) |
| File corrupt / empty | 422 hoặc 400 tùy FastAPI validation |
| Mobile Safari | File input `capture="environment"` mở camera (thiết bị cho phép) |

---

## Risks

| Risk | Mitigation (master §6–§9) |
|------|---------------------------|
| XSS qua demo tĩnh | Không `innerHTML` với dữ liệu không tin cậy; chỉ text node / escape |
| CORS / mở file:// | Luôn mở qua `http://localhost:PORT/demo/...` cùng origin |
| File lớn DOS | Sau này throttle/size limit (Phase 6); MVP giới hạn Pillow load + timeout inference |

---

## Acceptance criteria

- Developer chạy `uvicorn`, mở `/demo/demo_capture_classify.html`, chụp/chọn ảnh và thấy **`action`** + **`primary_class`** + có thể **ghi nhận loại đã xác nhận** trong UI (state cục bộ).
- `/docs` hiển thị cả `POST /classify` và `POST /classify-upload`.

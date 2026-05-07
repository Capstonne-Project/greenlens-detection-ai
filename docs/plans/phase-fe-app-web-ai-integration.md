# Plan — Tích hợp FE (React Native App + Web) với AI Service

**Nguồn chuẩn:** `docs/AI_Service_Development_Plan.md` (§1 kiến trúc, §5 FE/Mobile test, §7 BR matrix, §8 câu hỏi alignment, §9 risks).
**Trạng thái repo Python:** Phase 0 skeleton (`app/main.py`, health); chưa có `/classify`, `/verify-image`, `/check-duplicate`.

---

## Goals / non-goals

**Goals**

- Thống nhất **luồng dữ liệu**: App và Web không “gắn chặt” vào FastAPI Python trực tiếp trong mọi màn — mặc định đi qua **.NET Backend** (auth, CRUD, quota, BR-REP-010); chỉ luồng **real-time camera** có thể gọi AI trực tiếp nếu team chấp nhận (theo §1 master plan).
- Có **OpenAPI/Python → contract** chia sẻ với FE (generated client hoặc hand-written types) và **environment** (`AI_SERVICE_URL`, feature flags).
- FE (App + Web) có **test theo tier** trong §5.3 master plan (Tier 1 on-device; Tier 2 server; Tier 3 E2E sau .NET).

**Non-goals**

- Không thay canonical `docs/AI_Service_Development_Plan.md`.
- Không implement model training trong plan này (tham chiếu `phase-ai-*` khác trong `docs/plans/`).
- Không quyết định một mình các mục §8 — ghi rõ “cần align” và default đề xuất.

---

## BR & endpoints

**Luồng đề xuất cho App + Web**

| Client | Gọi trực tiếp Python AI? | Ghi chú |
|--------|---------------------------|---------|
| Web | **Không** (mặc định) | Upload qua .NET; .NET orchestrate gọi AI. |
| App — form / gallery | **Không** (mặc định) | Giống Web. |
| App — camera preview | **Có thể** | On-device `.tflite` + tuỳ chọn gọi AI server cho pipeline đầy đủ (§1). |

**BR & endpoint liên quan FE** (trích ý từ master plan §7 — mapping đầy đủ xem bảng gốc):

| BR ID | Endpoint Python (mục tiêu) | Ý nghĩa cho FE |
|-------|----------------------------|----------------|
| BR-AI-001 | `POST /api/v1/classify` | Gợi ý loại ô nhiễm, `action`: AUTO_FILL \| SUGGEST \| KEEP_USER_CHOICE; `noise_supported: false` nếu chọn Option A §Phase 3. |
| BR-AI-002, BR-REP-030 | `POST /api/v1/check-duplicate` | Hiển thị cảnh báo trùng / `should_flag`. |
| BR-AI-003 | `POST /api/v1/classify` (severity) | Map ratio → Low/Med/High/Critical; logic override nằm server/.NET. |
| BR-AI-004, BR-AI-007, BR-REP-003, BR-REP-011 | `POST /api/v1/verify-image` | Flags, warnings, EXIF/GPS, strip URL. |
| BR-AI-005 | Mọi endpoint | FE gửi `report_id` / correlation id nếu .NET truyền; audit chủ yếu phía server. |
| BR-AI-006 | Timeout / 202 + `task_id` | UI: “Đang phân tích…” / retry; không block submit vĩnh viễn. |
| BR-REP-014 | `POST /api/v1/verify-cleanup` | Màn cleanup team: before/after, tối thiểu 2 ảnh after. |

**Response mẫu (tham chiếu verbatim từ master plan)**

- `POST /api/v1/verify-image` — multipart + `valid`, `exif`, `flags`, `warnings`, `stripped_image_url` (Phase 1).
- `POST /api/v1/check-duplicate` — `is_potential_duplicate`, `matches[]`, `should_flag`, `reused_image_30days` (Phase 2).
- `POST /api/v1/classify` — `predictions`, `primary_class`, `confidence`, `action`, `model_version`, `inference_time_ms` (Phase 3).

---

## Execution checklist

1. **Align với .NET (§8):** Quyết URL nội bộ AI, auth (API key / mTLS / private network), timeout 5s, payload (URL ảnh vs multipart). Ghi vào contract repo hoặc wiki.
2. **OpenAPI:** Xuất spec từ FastAPI (`/openapi.json`); .NET generate client; FE Web dùng types từ OpenAPI hoặc từ .NET DTO đã thống nhất.
3. **Web**
   - Luồng tạo báo cáo: upload ảnh → .NET trả về (hoặc SSE/poll) kết quả AI flags nếu async.
   - Hiển thị `flags`, `warnings`, duplicate suggestion theo copy UX đã có BR.
   - Không embed secret AI key trên browser; mọi gọi qua .NET.
4. **App (React Native)**
   - Tier 1: tích hợp `.tflite` theo §5.1 (camera, overlay, threshold BR-AI-001).
   - Tier 2: client gọi **endpoint .NET** (khuyến nghị) hoặc dev-only trực tiếp Python qua tunnel; bật flag môi trường.
   - Màn Settings/Debug: base URL, mock mode, model version (§5.1).
5. **Mock server:** `scripts/mock_server.py` (master §5.2) — schema realistic để UI làm trước khi model xong.
6. **Postman:** `docs/postman/ai-service.postman_collection.json` (§5.4) — chia sẻ QA + mobile.
7. **E2E (Tier 3):** Sau khi Python + .NET xong — flow submit, `ai_pending`, retry (BR-AI-006).

---

## Files & modules

| Khu vực | File / artifact | Ghi chú |
|---------|-----------------|--------|
| Contract | OpenAPI export, NSwag / Kiota / openapi-generator | Theo §9 master “Document API contract”. |
| Python (mock) | `scripts/mock_server.py` | Chưa có — tạo theo §5.2. |
| Docs QA | `docs/postman/ai-service.postman_collection.json` | Chưa có — tạo theo §5.4. |
| App | RN screens: Camera, Post-capture, Settings | §5.1 flow. |
| Web | Components: upload, flag banner, duplicate alert | Phụ thuộc design system dự án .NET/FE. |
| Config | `.env`, `AI_SERVICE_BASE_URL`, `USE_MOCK_AI` | Không commit secret. |

---

## Test plan

| Tier | Mục tiêu | Edge / pitfall |
|------|----------|----------------|
| Web | Upload + hiển thị response hợp schema | Timeout, partial response, ảnh không EXIF. |
| App Tier 1 | 20 ảnh đa dạng, FPS &lt; 500ms target mid-range | Thiết bị yếu, camera permission. |
| App Tier 2 | Field-by-field so với OpenAPI | GPS ngoài VN, ảnh đã chỉnh sửa. |
| E2E | Full flow với .NET | AI down → `ai_pending` (BR-AI-006). |

---

## Risks

| Risk | Mitigation (tham §6–§9 master) |
|------|--------------------------------|
| FE phụ thuộc schema thay đổi | Version field `model_version` + contract tests; changelog API. |
| Lộ endpoint AI ra public | Chỉ .NET gọi AI trong prod; App dùng .NET JWT. |
| Web bundle chứa key | Kiểm tra pipeline build; chỉ backend holds AI credentials. |
| Mock drift khỏi thật | Generate mock từ cùng OpenAPI examples / pydantic schemas. |

---

## Acceptance criteria (tổng hợp)

- Web: không gọi trực tiếp AI production URL; có UI cho flags duplicate/verify.
- App: có demo path on-device + path server qua .NET (hoặc documented dev exception).
- Postman collection + mock server cho phép QA test không cần model thật.
- Danh sách §8 đã có quyết định ghi lại (hoặc explicit “deferred” với owner).

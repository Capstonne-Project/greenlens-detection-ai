# Plan — AI Service: Phase 1–3 (EXIF/Geo, Duplicate, Classification)

**Nguồn chuẩn:** `docs/AI_Service_Development_Plan.md` (Phase 1–3, §7 BR matrix, pitfalls §Phase 1–2, §Phase 3).
**Baseline repo:** Phase 0 partial — `app/main.py`, `app/api/v1/health.py`, `app/config.py`, `app/utils/logger.py`; **chưa** có các router trong tree đề xuất §3.

---

## Goals / non-goals

**Goals**

- **`POST /api/v1/verify-image`:** multipart ảnh + optional claimed GPS/time; trả EXIF/geo validation, flags (BR-REP-003, BR-REP-011, BR-AI-007 strip path theo contract).
- **`POST /api/v1/check-duplicate`:** JSON body với `image_url`, geo, type, time; scoring pHash + haversine + time; `reused_image_30days` (BR-AI-002, BR-REP-030, phần BR-AI-004 duplicate).
- **`POST /api/v1/classify`:** JSON `image_url` → YOLO predictions + `model_version` + `action` theo ngưỡng BR-AI-001; document `noise_supported`.
- Dataset + train + export (Phase 3.1–3.4) đủ cho POC tối thiểu (master: ~500 ảnh/class POC).

**Non-goals**

- Manipulation ELA nâng cao (Phase 5), ARQ worker đầy đủ (Phase 6) — chỉ stub hook nếu cần contract.
- Query trực tiếp Postgres từ AI — **mặc định** .NET truyền metadata ứng viên (master Phase 2 khuyến nghị); nếu §8 quyết khác thì cập nhật plan này.

---

## BR & endpoints

**Phase 1 — `POST /api/v1/verify-image`**

Request: `multipart/form-data` — `image`, optional `claimed_lat`, `claimed_lng`, `claimed_timestamp` (ISO 8601).

Response (verbatim structure từ master §Phase 1):

```json
{
  "valid": true,
  "exif": {
    "has_gps": true,
    "gps_lat": 10.762622,
    "gps_lng": 106.660172,
    "captured_at": "2026-05-06T10:30:00+07:00",
    "modified_at": "2026-05-06T11:45:00+07:00",
    "device": "iPhone 14",
    "in_vietnam": true
  },
  "flags": ["suspicious_edit_time_diff"],
  "warnings": ["Ảnh có thể không phản ánh hiện trạng thực tế"],
  "stripped_image_url": "s3://..."
}
```

**BR:** BR-REP-003, BR-REP-011, BR-AI-007 (strip output URL).

**Phase 2 — `POST /api/v1/check-duplicate`**

Request/response theo master §Phase 2 (JSON `image_url`, `lat`, `lng`, `pollution_type`, `timestamp`, `exclude_report_id`).

**BR:** BR-REP-030, BR-AI-002, BR-AI-004 (phần ảnh trùng trong 30 ngày — cần cache/kênh dữ liệu từ .NET).

**Phase 3 — `POST /api/v1/classify`**

Response theo master §Phase 3 (gồm `model_version`, `inference_time_ms`, `action`).

**BR:** BR-AI-001, BR-REP-005 (5 loại; “Tiếng ồn”: khuyến nghị Option A — không infer từ ảnh).

**§7 mapping:** BR-REP-003, BR-REP-011, BR-AI-007 → verify; BR-AI-002, BR-REP-030 → duplicate; BR-AI-001, BR-AI-003 (severity field sau Phase 4) → classify.

---

## Execution checklist

**Chung**

1. Thêm routers `app/api/v1/verify.py`, `duplicate.py`, `classify.py`; include trong `app/main.py` prefix `/api/v1`.
2. Pydantic schemas `app/models/` cho request/response từng endpoint.
3. Dependency load model (lazy) cho classify — tránh break `/health` khi weights chưa có.

**Phase 1**

4. Implement `core/exif_analyzer.py` (parse, time diff suspicious, strip sensitive EXIF workflow).
5. Implement `core/geo_validator.py` (bbox VN lat 8–24, lng 102–110; optional polygon sau).
6. `services/storage_service.py`: download/upload MinIO/S3 placeholder nếu `stripped_image_url` required.
7. Unit tests fixtures 10+ ảnh (có/không GPS, edited, NGOài VN, stripped social).

**Phase 2**

8. Implement `core/duplicate_detector.py`: pHash 64-bit, similarity = `1 - hamming/64`, haversine, composite score — align threshold “> 0.85” với §8 câu 3.
9. Define interface: nhận **danh sách ứng viên** từ caller (.NET) thay vì tự query DB (default).

**Phase 3**

10. Dataset: TACO/Roboflow + ảnh VN context; label YOLO format; split 70/20/10.
11. Train `ultralytics` fine-tune; log MLflow/W&B.
12. Eval mAP + confusion matrix; export `.onnx` server, `.tflite` mobile (chi tiết export trong plan Phase 8).
13. Wired `pollution_classifier.py` + thresholds config (`pydantic-settings`).

---

## Files & modules

| Thành phần | Path gợi ý |
|------------|------------|
| API | `app/api/v1/verify.py`, `duplicate.py`, `classify.py` |
| Core | `app/core/exif_analyzer.py`, `geo_validator.py`, `duplicate_detector.py`, `pollution_classifier.py` |
| Models | `app/models/verify.py`, `duplicate.py`, `classify.py` |
| Services | `app/services/storage_service.py`, `cache_service.py` (Redis cho pHash 30d nếu dùng) |
| Config | `app/config.py` — thresholds, model path, S3 |
| ML | `ml/training/`, `ml/export/`, `ml/weights/` (gitignore artifacts) |
| Tests | `tests/unit/`, `tests/integration/` + `tests/fixtures/images/` |

---

## Test plan

| Area | Happy path | Edge / pitfall (master) |
|------|------------|-------------------------|
| EXIF | Ảnh iPhone có GPS | Rational → decimal; nhiều format DateTime; social strip ≠ suspicious mặc định |
| Geo | Point trong VN | Ra khỏi bbox; biên hải nếu sau này polygon |
| Duplicate | Hai ảnh gần giống, gần nhau trong 24h | Self-match `exclude_report_id`; scale similarity |
| Classify | Một class dominant | confidence 0.5–0.8 vs ≥0.8; class dễ nhầm chemical/water |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Dataset VN thiếu | §9: active learning sau launch; POC với public set + subset VN |
| Model chưa có → CI fail | Optional weights path; skip integration test khi `MODEL_PATH` unset |
| pHash scale ambiguity | Ghi rõ công thức trong API doc; align §8 câu 3 |
| Strip EXIF storage | §8 câu 7 — version mới vs ghi đè; default “new object key” |

---

## Acceptance criteria

- OpenAPI hiển thị đủ 3 endpoint; contract khớp ví dụ JSON trong master (trường có thể mở rộng backward-compatible).
- Tests: unit EXIF/geo; unit duplicate scoring; integration HTTP ít nhất verify + một happy classify (hoặc skipped có lý do).
- Mọi response classify có `model_version` (BR-AI-005 readiness).

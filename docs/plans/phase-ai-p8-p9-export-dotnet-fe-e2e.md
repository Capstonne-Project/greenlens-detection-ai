# Plan — AI Service: Phase 8–9 (Mobile export, docs) + E2E với .NET & FE

**Nguồn chuẩn:** `docs/AI_Service_Development_Plan.md` (Phase 8–9, §5, §7, §9).
**Mục tiêu tổng:** Đóng gói artifact mobile, tài liệu model, và kiểm thử end-to-end với .NET + App + Web.

---

## Goals / non-goals

**Goals**

- **Phase 8:** Script export `.tflite` INT8 (+ float16 fallback); `docs/MODEL_CARD.md`; `labels.txt` đồng bộ index; versioning tag artifact; hướng dẫn preprocess cho RN.
- **Phase 9:** E2E mobile → upload → .NET → AI; load test (k6/locust); chaos AI down → BR-AI-006; OpenAPI cho NSwag.
- **FE alignment:** Đảm bảo App/Web dùng cùng enum loại ô nhiễm với server; kiểm tra `action` và `flags` trên UI (tham chiếu `phase-fe-app-web-ai-integration.md`).

**Non-goals**

- Đào tạo lại model đầy đủ trong phase này (giả định weights đã có từ Phase 3).

---

## BR & endpoints

**Không endpoint mới bắt buộc** so với Phase 1–7; Phase 8–9 nhấn vào:

- **BR-AI-005:** Mọi inference log đủ field cho audit khi E2E chạy.
- **BR-AI-006:** .NET fallback khi AI timeout/down — verify bằng chaos test.
- **BR-AI-001:** Ngưỡng trên device khớp policy server (document nếu khác do quantize).

**§7:** Liên kết test `test_audit_log.py`, `test_timeout_fallback.py` với kịch bản Phase 9.

---

## Execution checklist

**Phase 8**

1. `ml/export/export_tflite.py` — input shape, normalize, INT8 calibration set.
2. Kiểm tra inference emulator Android/iOS (sample script hoặc RN demo).
3. Viết `docs/MODEL_CARD.md`: data, metrics, bias, limitations (noise, low-light).
4. Publish artifact `vX.Y.Z-yolov8n-int8` lên storage agreed (§8 câu 5).
5. Giao `labels.txt` + checksum cho mobile.

**Phase 9**

6. Contract: export OpenAPI JSON committed hoặc generated in CI; .NET NSwag pipeline.
7. E2E script (pytest + httpx **hoặc** Postman runner) cho flow: create report → AI callbacks/poll.
8. k6/locust: ~100 RPS target tùy infra; ghi SLO latency.
9. Chaos: stop AI container; assert .NET tạo report `ai_pending` và recovery.
10. **Web + App smoke:** sau E2E backend — UI nhận đúng DTO .NET (không nhân đôi parse Python).

---

## Files & modules

| Artifact | Path / ghi chú |
|----------|----------------|
| Export | `ml/export/export_tflite.py` |
| Model card | `docs/MODEL_CARD.md` |
| Labels | `ml/weights/labels.txt` (hoặc cùng thư mục release) |
| Postman | `docs/postman/ai-service.postman_collection.json` |
| Bench | `scripts/benchmark.py`, k6/locust scripts trong `scripts/load/` (tạo nếu cần) |
| API doc | `docs/API.md` — link OpenAPI |

---

## Test plan

| Loại | Nội dung |
|------|----------|
| Model export | Output size budget (~50MB risk §9); latency on-device tier |
| Contract | Breaking change check giữa OpenAPI versions |
| Load | P95 inference; error rate under burst |
| Chaos | Timeout, 503, intermittent Redis |
| E2E FE | Duplicate warning visible; classify suggest visible; offline queue behavior App |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Quantized drift vs server | Dual threshold hoặc “SUGGEST only” on device |
| Large .tflite | Prune / smaller YOLO variant |
| E2E flake | Idempotent report id; test data isolation |
| Web không test AI trực tiếp | Focus E2E qua .NET API contract tests |

---

## Acceptance criteria

- Mobile nhận đủ gói: `.tflite`, `labels.txt`, preprocess spec, model version string khớp API.
- OpenAPI đã handoff .NET; một E2E run xanh trên staging.
- Load test report lưu (ảnh Grafana hoặc markdown kết quả trong CI artifact — tuỳ team).
- Cross-reference: hoàn thành checklist trong `phase-fe-app-web-ai-integration.md` Tier 3.

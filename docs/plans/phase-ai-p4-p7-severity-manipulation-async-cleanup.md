# Plan — AI Service: Phase 4–7 (Severity, Manipulation/Flags, Resilience, Cleanup)

**Nguồn chuẩn:** `docs/AI_Service_Development_Plan.md` (Phase 4–7, §6–9, §7 BR matrix).
**Phụ thuộc:** Phase 1–3 (đặc biệt YOLO output cho severity; duplicate/pHash cho BR-AI-004 mở rộng).

---

## Goals / non-goals

**Goals**

- **Phase 4 — Severity (BR-AI-003):** `pollution_ratio` từ bbox area / image area; map threshold configurable; chuẩn bị override policy (Python hoặc .NET — ghi rõ owner); v2 segmentation deferred.
- **Phase 5 — Flags (BR-AI-004 + mở rộng verify):** ELA v1; `no_pollution_detected`; tái sử dụng ảnh 30 ngày (mở rộng Phase 2 + Redis TTL); mở rộng payload `verify-image` với `manipulation_score`, flags bổ sung.
- **Phase 6 — BR-AI-005, BR-AI-006:** Timeout ~4.5s, 202 + `task_id`; ARQ/Celery worker retry; structured audit fields; Prometheus metrics; `/ready` reflects model load.
- **Phase 7 — `POST /api/v1/verify-cleanup`:** BR-REP-014/023 checks theo master.

**Non-goals**

- MantraNet/BusterNet (Phase 5 phase 2) trừ khi spike riêng.
- Full horizontal autoscaling k8s — chỉ metrics + hooks sẵn sàng.

---

## BR & endpoints

**Severity (trong pipeline classify hoặc field bổ sung)**

- v1 thresholds: &lt;5% Low; 5–15% Medium; 15–40% High; &gt;40% Critical (config).
- Override snippet (master §Phase 4):

```python
if abs(ai_severity - user_severity) >= 2 and ai_confidence >= 0.85:
    final_severity = ai_severity
    log_override(reason="AI override", user=user_severity, ai=ai_severity)
else:
    final_severity = user_severity
```

(Ghi chú triển khai: logic “final” có thể nằm .NET; AI chỉ trả `ai_severity` + `ai_confidence`.)

**Mở rộng `POST /api/v1/verify-image` (Phase 5)**

```json
{
  "flags": [
    "manipulation_detected",
    "no_pollution_in_image",
    "reused_image_30days"
  ],
  "manipulation_score": 0.73,
  "matched_old_report_id": "uuid-of-original"
}
```

**`POST /api/v1/verify-cleanup` (Phase 7)** — request/response verbatim master §Phase 7:

Request:

```json
{
  "before_image_url": "s3://...",
  "after_images": ["s3://...", "s3://..."],
  "report_id": "uuid"
}
```

Response:

```json
{
  "valid": true,
  "checks": {
    "min_after_count_met": true,
    "after_images_unique": true,
    "after_different_from_before": true,
    "after_taken_recently": true
  },
  "issues": []
}
```

**§7 mapping:** BR-AI-003 → severity module; BR-AI-004 → verify + manipulation; BR-AI-005 → logging middleware; BR-AI-006 → timeout/deps; BR-REP-014 → verify-cleanup.

---

## Execution checklist

**Phase 4**

1. Add `core/severity_estimator.py`; wire sau inference (bbox conf threshold từ Phase 3).
2. Expose severity trong response classify hoặc `POST /api/v1/batch-analyze` (nếu thêm sau).
3. Config thresholds trong settings; document cho Admin.

**Phase 5**

4. `core/manipulation_detector.py` — ELA JPEG pipeline; score 0–1.
5. Flag `no_pollution` khi max conf &lt; 0.3 (master).
6. Redis/service: keyspace pHash 30d toàn cục; API nhận candidates từ .NET hoặc cache hit.
7. Merge flags vào verify response; versioning schema (optional fields).

**Phase 6**

8. Middleware timeout 4.5s; response 202 schema { `task_id`, `status` }.
9. `workers/retry_worker.py` ARQ: consume `ai_pending` (contract với .NET).
10. Persist audit: `ai_inference_logs` qua HTTP tới .NET **hoặc** direct PG nếu §8 quyết — default ghi structured log + async sink.
11. Metrics: `ai_inference_duration_seconds`, histogram confidence, duplicate counter.
12. `/ready` checks model file + Redis (optional).

**Phase 7**

13. Router `app/api/v1/cleanup.py` (hoặc tên tương đương); reuse pHash + EXIF time check ≤24h.

---

## Files & modules

| Phase | Files |
|-------|--------|
| 4 | `app/core/severity_estimator.py`, config keys, tests `test_severity_override.py` |
| 5 | `app/core/manipulation_detector.py`, extend `verify.py`, `cache_service.py` |
| 6 | `app/api/deps.py` (timeout), `app/workers/retry_worker.py`, `app/utils/metrics.py`, logging middleware |
| 7 | `app/api/v1/cleanup.py` (verify-cleanup), tests `test_cleanup_verify.py` |

---

## Test plan

| Module | Cases |
|--------|--------|
| Severity | ratio biên 5/15/40%; không bbox; multi-bbox sum |
| Manipulation | ảnh gốc vs paste vùng; false positive tolerance documented |
| 30-day reuse | hash trùng xa geo; TTL expiry |
| Timeout | inference chậm → 202; worker completes |
| Cleanup | &lt;2 after; after trùng before; EXIF giả |

---

## Risks

| Risk | Mitigation (master §9) |
|------|-------------------------|
| False positive manipulation | Officer UI: nhãn “gợi ý”, không auto-reject |
| Worker backlog | Observable queue depth; rate limit §8 câu 6 |
| Audit PII | Log hash input, không log raw image |
| Severity mismatch user | Policy rõ ràng; log override BR-AI-005 |

---

## Acceptance criteria

- Verify response có thể chứa đủ flags Phase 5 mà không break clients cũ (optional fields).
- Timeout + 202 path có test contract; worker xử lý ít nhất một retry story.
- `verify-cleanup` khớp schema master; tests cho `issues` khi vi phạm.

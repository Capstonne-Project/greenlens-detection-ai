# 🤖 AI Service - Development Plan

**Project:** SU26SE049 - Crowdsourced App for Reporting Environmental Pollution
**Module:** AI Microservice (Python)
**Vai trò:** Microservice độc lập, được .NET Backend gọi qua REST/gRPC; Mobile app cũng có thể gọi trực tiếp cho luồng "real-time camera"

---

## 1. Bức tranh tổng quan kiến trúc

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  React Native│────▶│  .NET Backend   │────▶│  Python AI       │
│  Mobile App  │     │  (Auth, CRUD,   │     │  Service (FastAPI│
│  + .tflite   │     │   State, DB)    │     │  + YOLO + ML)    │
└──────────────┘     └─────────────────┘     └──────────────────┘
       │                     │                        │
       │  (real-time scan)   │                        │
       └─────────────────────┴────────────────────────┘
              Mobile gọi AI trực tiếp khi cần tốc độ
              .NET gọi AI cho các tác vụ async/heavy
```

**Hai loại AI inference song song:**

1. **On-device (mobile)**: YOLOv8/v11 Nano `.tflite` — chạy real-time trong camera viewfinder, hiển thị bounding box và auto-fill nhanh. Repo Python này có nhiệm vụ **train + export** model `.tflite` cho mobile.
2. **Server-side (Python service)**: Model đầy đủ (YOLOv8s/m), chạy lại khi báo cáo được submit, kèm các tác vụ nặng: pHash duplicate, EXIF analysis, manipulation detection, severity refinement.

**Tại sao cần cả 2?** Mobile cần phản hồi <500ms cho UX "một chạm", nhưng confidence từ Nano model chỉ đủ cho gợi ý sơ bộ. Server-side chạy lại với model lớn hơn để xác nhận và làm các kiểm tra mà mobile không làm được (so khớp với DB ảnh cũ trong 30 ngày — BR-AI-004).

---

## 2. Tech stack đề xuất

| Thành phần | Lựa chọn | Lý do |
|---|---|---|
| Web framework | **FastAPI** | Async native, OpenAPI tự động → .NET dễ generate client, hỗ trợ Pydantic validation |
| Object Detection | **Ultralytics YOLOv8/v11** | BR yêu cầu, có sẵn export `.tflite`, `.onnx`, `.pt` |
| Image processing | **OpenCV + Pillow** | Tiêu chuẩn |
| EXIF | **piexif + ExifRead** | piexif ghi/strip, ExifRead đọc tốt hơn cho file lạ |
| Perceptual hash | **imagehash** (pHash, dHash) | Đúng theo BR-AI-002 |
| Manipulation detection | **PIL ELA + noise analysis** (giai đoạn đầu) → cân nhắc model CNN sau | ELA detect được copy-paste/photoshop cơ bản |
| Geo | **Shapely + GeoPy** | Tính khoảng cách haversine 50m, check polygon VN |
| Database client | **asyncpg (PostgreSQL)** hoặc **httpx** gọi .NET API | Tùy bạn cho AI tự query DB hay luôn đi qua .NET |
| Cache / Queue | **Redis** | Cache hash 30 ngày (BR-AI-004), queue cho fallback (BR-AI-006) |
| Background job | **Celery hoặc ARQ** | ARQ async-native, nhẹ hơn Celery |
| Container | **Docker + docker-compose** | Deploy đồng bộ với .NET |
| Testing | **pytest + pytest-asyncio + httpx** | |
| Config | **pydantic-settings** | Đọc env vars an toàn |
| Logging | **structlog + JSON logs** | Audit log BR-AI-005 |

---

## 3. Cấu trúc repo đề xuất

```
ai-service/
├── app/
│   ├── main.py                    # FastAPI entry
│   ├── config.py                  # pydantic-settings
│   ├── api/
│   │   ├── v1/
│   │   │   ├── classify.py        # POST /classify (BR-AI-001, 003)
│   │   │   ├── duplicate.py       # POST /check-duplicate (BR-AI-002)
│   │   │   ├── verify.py          # POST /verify-image (BR-AI-004, REP-011)
│   │   │   ├── batch.py           # POST /batch-analyze (full pipeline)
│   │   │   └── health.py          # GET /health, /ready
│   │   └── deps.py                # Dependency injection
│   ├── core/
│   │   ├── pollution_classifier.py    # YOLO wrapper
│   │   ├── severity_estimator.py      # Diện tích → Low/Med/High/Critical
│   │   ├── duplicate_detector.py      # pHash + GPS + time
│   │   ├── exif_analyzer.py           # EXIF parse + suspicious detect
│   │   ├── manipulation_detector.py   # ELA / noise analysis
│   │   └── geo_validator.py           # Check VN bbox
│   ├── models/                    # Pydantic schemas (request/response)
│   ├── services/
│   │   ├── cache_service.py       # Redis wrapper
│   │   └── storage_service.py     # S3/MinIO để fetch ảnh
│   ├── workers/
│   │   └── retry_worker.py        # ARQ worker cho 'ai_pending' (BR-AI-006)
│   └── utils/
│       ├── logger.py
│       └── metrics.py             # Prometheus
├── ml/
│   ├── training/
│   │   ├── train_yolo.py          # Script train
│   │   ├── data/                  # YOLO format dataset
│   │   └── configs/               # data.yaml, hyp.yaml
│   ├── export/
│   │   └── export_tflite.py       # Export .tflite cho mobile
│   ├── notebooks/                 # EDA, evaluation
│   └── weights/                   # Model artifacts (.pt, .tflite, .onnx)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/                  # Sample images
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.gpu             # Cho training
│   └── docker-compose.yml
├── scripts/
│   ├── seed_test_data.py
│   └── benchmark.py
├── docs/
│   ├── API.md
│   ├── BR_TRACEABILITY.md         # Map BR → endpoint/test
│   └── MODEL_CARD.md
├── .env.example
├── pyproject.toml                 # Poetry hoặc uv
├── requirements.txt
└── README.md
```

---

## 4. Chi tiết các Phase phát triển

### 📌 PHASE 0 — Setup & Foundation (3-5 ngày)

**Mục tiêu:** Có được skeleton chạy được + CI/CD tối thiểu.

**Việc cần làm:**

- Khởi tạo repo, chọn package manager (gợi ý `uv` hoặc `poetry`).
- Setup FastAPI skeleton với endpoint `/health` và `/ready` (Kubernetes-style).
- Dockerfile multi-stage (build → runtime), docker-compose có Redis + MinIO (giả lập S3).
- Setup pre-commit hooks: `ruff`, `black`, `mypy`.
- GitHub Actions: lint + test cơ bản trên PR.
- Tạo `.env.example` và `config.py` đọc settings.
- Setup logging structured JSON (cho production) và pretty (cho dev).
- Tạo README.md có hướng dẫn `docker-compose up`.

**Deliverable:** Chạy `docker-compose up`, gọi `GET /health` trả 200. CI pass trên PR rỗng.

**Lưu ý:** Đừng vội thêm model ở phase này. Mục tiêu là "đi đường ray" trước.

---

### 📌 PHASE 1 — Data Validation & EXIF Pipeline (5-7 ngày)

**Mục tiêu:** Implement các BR không cần ML model — đây là phần "nhanh thắng" và dùng được ngay.

**BR phụ trách:**
- BR-REP-003: GPS trong lãnh thổ VN (lat 8.0–24.0, lng 102.0–110.0)
- BR-REP-011: EXIF metadata, đánh dấu Suspicious nếu chỉnh sửa >1h
- BR-AI-007: Strip EXIF nhạy cảm

**Endpoint cần build:**

```
POST /api/v1/verify-image
Body: multipart/form-data
  - image: file
  - claimed_lat: float (optional)
  - claimed_lng: float (optional)
  - claimed_timestamp: ISO 8601 (optional)

Response:
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
  "stripped_image_url": "s3://..." // sau khi strip EXIF nhạy cảm
}
```

**Module cần code:**
- `core/exif_analyzer.py`: parse EXIF, tính chênh lệch DateTimeOriginal vs DateTime (modified)
- `core/geo_validator.py`: bbox check + (tùy chọn) check polygon VN từ GeoJSON cho chính xác hơn (loại trừ vùng biển quốc tế)
- `services/storage_service.py`: download ảnh từ S3/MinIO, upload bản đã strip

**Test cần có:**
- Unit test với 10+ ảnh fixture (có/không GPS, đã chỉnh sửa, ngoài VN, ảnh fake EXIF…)
- Integration test gọi qua HTTP

**⚠️ Pitfall thường gặp:**
- EXIF DateTime có nhiều format và timezone khác nhau, parse cẩn thận.
- iPhone ghi GPS theo dạng rational, cần convert sang decimal đúng.
- Một số ảnh từ Facebook/Zalo bị strip hết EXIF — đừng coi đó là suspicious mặc định.

---

### 📌 PHASE 2 — Duplicate Detection (5-7 ngày)

**Mục tiêu:** Phát hiện báo cáo trùng theo BR-REP-030 và BR-AI-002.

**BR phụ trách:**
- BR-REP-030: Cùng loại + GPS ≤50m + trong 24h
- BR-AI-002: pHash > 0.85
- BR-AI-004 (phần "ảnh trùng ảnh đã dùng trong 30 ngày")

**Endpoint:**

```
POST /api/v1/check-duplicate
Body:
{
  "image_url": "s3://...",
  "lat": 10.762,
  "lng": 106.660,
  "pollution_type": "TRASH",
  "timestamp": "2026-05-06T10:30:00Z",
  "exclude_report_id": "uuid-tránh-self-match"
}

Response:
{
  "is_potential_duplicate": true,
  "matches": [
    {
      "report_id": "uuid",
      "phash_similarity": 0.92,
      "distance_meters": 23,
      "time_diff_hours": 4,
      "match_score": 0.89
    }
  ],
  "should_flag": true,
  "reused_image_30days": false  // BR-AI-004
}
```

**Module cần code:**
- `core/duplicate_detector.py`:
  - Tính pHash 64-bit (dùng `imagehash.phash`)
  - **Quan trọng:** pHash so sánh bằng Hamming distance, similarity = 1 - (hamming/64). BR ghi "pHash > 0.85" → cần normalize cho rõ.
  - Haversine distance giữa 2 GPS points
  - Composite score = weighted(pHash, geo, time)

**Cần thảo luận với team .NET:**
- AI service sẽ **query trực tiếp** DB Postgres để lấy danh sách ảnh ứng viên trong vòng 50m + 24h, hay .NET sẽ fetch trước rồi truyền vào AI?
- Khuyến nghị: .NET fetch metadata (id, pHash đã lưu, GPS, time) → truyền vào AI để score. AI **không trực tiếp đụng DB business**. Lưu pHash trong DB của .NET ngay khi tạo report.

**Cache strategy:**
- pHash của mọi ảnh active trong 30 ngày → Redis sorted set hoặc cache layer.

---

### 📌 PHASE 3 — Pollution Classification Model (10-15 ngày)

**Mục tiêu:** Train YOLO classify 5 loại ô nhiễm.

**BR phụ trách:**
- BR-AI-001: Phân loại + confidence threshold (≥0.8 auto, 0.5-0.8 suggest)
- BR-REP-005: 5 loại — Rác thải, Nước thải, Khói/khí, Tiếng ồn, Hóa chất

**⚠️ Vấn đề lớn cần xử lý:** "Tiếng ồn" không phân loại được từ ảnh. Cần thống nhất với team:
- Option A: Bỏ "Tiếng ồn" khỏi AI — luôn user-input, không AI suggest.
- Option B: Train detect "loa, máy phát điện, công trường" như proxy cho noise.
- **Khuyến nghị: Option A.** Document rõ trong response: `noise_supported: false`.

**Các bước:**

#### 3.1 Dataset (3-5 ngày)
- Thu thập:
  - **TACO dataset** (Trash Annotations in Context) — public, có annotation
  - **Roboflow Universe** — search "trash", "garbage", "pollution"
  - **Tự crawl + label** ảnh VN context (Google Image, Foody, báo điện tử) — context VN rất khác Tây
- Label tool: **CVAT** (open source, self-host) hoặc Roboflow (free tier)
- Format: YOLO format (txt label files)
- Split: 70/20/10 train/val/test
- **Mục tiêu tối thiểu:** 500 ảnh/class cho POC, 2000+/class cho production

#### 3.2 Training (3-5 ngày)
- Bắt đầu với `yolov8n.pt` pretrained → fine-tune
- Track experiments với **MLflow** hoặc **Weights & Biases**
- Hyperparameter: batch=16, epochs=100, imgsz=640, mosaic augmentation
- Train trên Colab Pro / Kaggle / GPU cloud nếu không có máy

#### 3.3 Evaluation (2 ngày)
- Metrics: mAP@0.5, mAP@0.5:0.95, precision/recall per class
- Confusion matrix → tìm class hay nhầm lẫn (chemical vs water rất dễ nhầm)
- Test trên ảnh user-realistic (ảnh chụp vội, blur, ngược sáng…)

#### 3.4 Export & Integration (2-3 ngày)
- Export `.tflite` (INT8 quantize) cho mobile
- Export `.onnx` cho server inference (nhanh hơn `.pt`)
- Build endpoint `/classify`:

```
POST /api/v1/classify
Body: { "image_url": "s3://..." }

Response:
{
  "predictions": [
    {"class": "TRASH", "confidence": 0.92, "bbox_count": 5},
    {"class": "WATER", "confidence": 0.34, "bbox_count": 1}
  ],
  "primary_class": "TRASH",
  "confidence": 0.92,
  "action": "AUTO_FILL",  // AUTO_FILL | SUGGEST | KEEP_USER_CHOICE
  "model_version": "v1.0.0-yolov8n",
  "inference_time_ms": 230
}
```

**Lưu ý quan trọng:**
- **Model versioning:** mỗi response phải kèm `model_version` để audit log (BR-AI-005).
- Lưu weights ở **DVC** hoặc **MLflow Registry**, không commit vào Git.
- Có endpoint `/models` để Admin xem model hiện tại đang chạy.

---

### 📌 PHASE 4 — Severity Estimation (5-7 ngày)

**Mục tiêu:** BR-AI-003 — đánh giá mức độ Low/Medium/High/Critical từ diện tích vùng ô nhiễm.

**Approach (đơn giản → phức tạp):**

**v1 (đơn giản, làm trước):**
- Chạy YOLO detection → tổng diện tích bbox / diện tích ảnh = `pollution_ratio`
- Map theo threshold:
  - `< 5%`: Low
  - `5-15%`: Medium
  - `15-40%`: High
  - `> 40%`: Critical
- Threshold lấy từ config, Admin có thể chỉnh.

**v2 (tốt hơn, làm sau khi có data):**
- Dùng **YOLO segmentation** (yolov8n-seg) thay vì detection để có mask chính xác
- Cộng thêm yếu tố "loại chất" (chemical = +1 severity tier)
- Cộng thêm "mật độ báo cáo lân cận" (cần data từ .NET, query DB)

**Override logic (BR-AI-003):**
```python
if abs(ai_severity - user_severity) >= 2 and ai_confidence >= 0.85:
    final_severity = ai_severity
    log_override(reason="AI override", user=user_severity, ai=ai_severity)
else:
    final_severity = user_severity
```

---

### 📌 PHASE 5 — Manipulation Detection & Suspicious Flag (5-7 ngày)

**Mục tiêu:** BR-AI-004 — flag ảnh đã chỉnh sửa, ảnh không có ô nhiễm, ảnh trùng 30 ngày.

**3 sub-tasks:**

#### 5.1 Detect manipulation (khó nhất)
- **Phase 1 — ELA (Error Level Analysis):** so sánh ảnh gốc với ảnh re-compress JPEG quality 95. Vùng đã chỉnh sửa có error level khác. Đơn giản, chạy nhanh, đủ tốt cho POC.
- **Phase 2 (sau):** Dùng pretrained model như **MantraNet** hoặc **BusterNet**. Phức tạp hơn, cần GPU, độ chính xác tốt hơn nhiều.
- **Honest disclaimer:** Không model nào hoàn hảo. False positive sẽ có. Kết quả chỉ là gợi ý cho Officer (BR-AI-005).

#### 5.2 Detect "không có ô nhiễm trong ảnh"
- Nếu YOLO không detect được object nào với confidence > 0.3 → flag "no_pollution_detected"
- Hoặc user submit ảnh meme, ảnh selfie… → có thể train classifier nhị phân (pollution vs not) song song.

#### 5.3 Detect ảnh tái sử dụng trong 30 ngày
- Đã làm trong Phase 2 (duplicate). Mở rộng: query toàn bộ ảnh active (không chỉ trong 50m) trong 30 ngày → so pHash.
- Cache pHash trong Redis với TTL 30 ngày.

**Endpoint mở rộng `/verify-image`:**

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

---

### 📌 PHASE 6 — Resilience, Async & Audit (5-7 ngày)

**Mục tiêu:** Đảm bảo BR-AI-005 (audit) và BR-AI-006 (fallback 5s).

**Việc cần làm:**

- **Timeout middleware:** mọi request có timeout cứng 4.5s (để .NET có 5s budget). Nếu timeout → trả 202 Accepted với `task_id`, .NET tag `ai_pending`.
- **Worker (ARQ):** background job xử lý lại các ảnh `ai_pending`, retry sau 1h (BR-AI-006).
- **Audit log:** mọi inference ghi vào structured log + persist vào bảng `ai_inference_logs` (PostgreSQL):
  - `report_id`, `model_version`, `input_hash`, `predictions`, `latency_ms`, `timestamp`
- **Metrics (Prometheus):**
  - `ai_inference_duration_seconds{endpoint, status}`
  - `ai_classification_confidence_bucket`
  - `ai_duplicate_detection_count`
- **Health checks:** `/health` (live) và `/ready` (model loaded?)

---

### 📌 PHASE 7 — Cleanup Team Verification (3-5 ngày)

**Mục tiêu:** BR-REP-014/023 — verify ảnh before/after của Cleanup Team.

**Endpoint:**

```
POST /api/v1/verify-cleanup
Body:
{
  "before_image_url": "s3://...",
  "after_images": ["s3://...", "s3://..."],  // ít nhất 2
  "report_id": "uuid"
}

Response:
{
  "valid": true,
  "checks": {
    "min_after_count_met": true,         // ≥2 ảnh after
    "after_images_unique": true,         // pHash check, không trùng nhau
    "after_different_from_before": true, // pHash before vs after
    "after_taken_recently": true         // EXIF ≤24h trước submit
  },
  "issues": []
}
```

---

### 📌 PHASE 8 — Mobile Model Export & Documentation (3-5 ngày)

**Mục tiêu:** Đóng gói model `.tflite` cho team Mobile + viết tài liệu integration.

**Việc cần làm:**

- Script export `.tflite`:
  - INT8 quantization (nhỏ hơn ~4x, nhanh hơn ~2x trên CPU mobile)
  - Float16 fallback cho thiết bị có GPU
  - Test inference trên emulator Android/iOS
- Tạo **Model Card** (`docs/MODEL_CARD.md`):
  - Dataset gì, bao nhiêu ảnh, bias đã biết
  - Performance metrics
  - Limitations (không nhận noise, kém với ảnh ban đêm…)
- Tài liệu cho mobile team: input shape, preprocessing (resize, normalize), output parsing.
- File `labels.txt` đi kèm (đảm bảo index khớp với `.tflite`).
- Versioning: artifact tag `v1.0.0-yolov8n-int8`.

---

### 📌 PHASE 9 — Integration Testing với .NET & Mobile (5-7 ngày)

- E2E test: mobile chụp → upload → .NET gọi AI → response → state machine.
- Load test: dùng **k6** hoặc **locust** giả lập 100 req/s.
- Chaos test: AI down → .NET fallback đúng (BR-AI-006).
- Document API contract: OpenAPI spec gửi cho team .NET để generate C# client (NSwag).

---

## 5. Hướng dẫn FE/Mobile App Test

Đây là phần tách riêng để team Mobile có thể test AI Service trước khi tích hợp full với .NET.

### 5.1 Test app tối thiểu (Mobile demo app)

**Mục đích:** Cho team Mobile có app nhỏ để verify model hoạt động đúng trên thiết bị thật.

**Stack:**
- React Native (CLI, không Expo nếu cần native module .tflite)
- `react-native-vision-camera` (camera real-time)
- `react-native-fast-tflite` hoặc `vision-camera-image-labeler` (load .tflite)
- `react-native-image-picker` (chọn ảnh từ gallery để test)

**Flow demo app:**

```
[Màn hình 1: Camera Live Preview]
  - Hiển thị bounding boxes real-time (mỗi 500ms)
  - Confidence + class name overlay
  - Nút "Capture"

[Màn hình 2: Sau khi chụp]
  - Hiển thị ảnh + AI result
  - Hiển thị: class, confidence, action (AUTO_FILL/SUGGEST/KEEP)
  - Form auto-fill: dropdown loại ô nhiễm (đã chọn sẵn nếu AUTO_FILL)
  - Nút "Send to AI Server" để test full pipeline server-side
  - Hiển thị: GPS, EXIF info, severity, duplicate matches

[Màn hình 3: Settings/Debug]
  - Switch model version
  - Toggle on-device vs server inference
  - Log viewer
```

### 5.2 Backend mock cho Mobile test sớm

Trong khi AI service chưa hoàn chỉnh, build **mock server** (cũng FastAPI, ~50 dòng):
- Endpoint nhận multipart/form-data
- Return random nhưng realistic response theo schema đã thống nhất
- Mobile team có thể bắt đầu UI trước khi model ready

Đặt trong `ai-service/scripts/mock_server.py`.

### 5.3 Test plan cho Mobile team

Có 3 tầng test:

**Tier 1: Test on-device .tflite (không cần network)**
- Chụp 20 ảnh đa dạng (rác, nước, khói, ảnh không liên quan)
- Verify confidence threshold logic đúng theo BR-AI-001
- Đo FPS, latency trên các thiết bị thật (low/mid/high-end)
- Mục tiêu: <500ms inference trên mid-range Android (Snapdragon 6xx)

**Tier 2: Test server-side AI**
- Upload ảnh → kiểm tra response field by field
- Test edge cases: ảnh không có EXIF, GPS ngoài VN, ảnh đã chỉnh sửa
- Test duplicate: upload 2 ảnh giống nhau ở cùng vị trí

**Tier 3: Test E2E**
- Sau khi .NET integrate, test full flow: capture → AI → submit → verify state
- Test fallback: tắt AI service, verify .NET vẫn tạo report với `ai_pending`

### 5.4 Postman/Insomnia collection

Phải có collection sẵn trong repo (`docs/postman/ai-service.postman_collection.json`) để mobile team test API trực tiếp không cần code.

---

## 6. Roadmap tổng (Timeline ước tính)

| Phase | Thời gian | Phụ thuộc |
|---|---|---|
| 0. Setup | 3-5 ngày | — |
| 1. EXIF/Geo validation | 5-7 ngày | Phase 0 |
| 2. Duplicate detection | 5-7 ngày | Phase 0 |
| 3. Classification model | 10-15 ngày | Phase 0 (song song với 1, 2) |
| 4. Severity estimation | 5-7 ngày | Phase 3 |
| 5. Manipulation detection | 5-7 ngày | Phase 1, 2 |
| 6. Resilience & audit | 5-7 ngày | Phase 1-5 |
| 7. Cleanup verification | 3-5 ngày | Phase 1, 2 |
| 8. Mobile export & docs | 3-5 ngày | Phase 3 |
| 9. Integration testing | 5-7 ngày | Tất cả |

**Tổng ước tính:** ~10-12 tuần cho 1 dev FT, hoặc 6-8 tuần cho 2 devs làm song song.

**MVP tối thiểu để demo (4-5 tuần):** Phase 0 + 1 + 2 + 3 (POC model với dataset nhỏ). Bỏ qua manipulation detection và severity tinh vi.

---

## 7. BR Traceability Matrix (cần có trong repo)

| BR ID | Endpoint | Module | Test |
|---|---|---|---|
| BR-AI-001 | `/classify` | `pollution_classifier.py` | `test_classify_threshold.py` |
| BR-AI-002 | `/check-duplicate` | `duplicate_detector.py` | `test_phash_similarity.py` |
| BR-AI-003 | `/classify` (severity field) | `severity_estimator.py` | `test_severity_override.py` |
| BR-AI-004 | `/verify-image` | `manipulation_detector.py` | `test_suspicious_flags.py` |
| BR-AI-005 | All endpoints (logging middleware) | `utils/logger.py` | `test_audit_log.py` |
| BR-AI-006 | All endpoints (timeout) | `api/deps.py` | `test_timeout_fallback.py` |
| BR-AI-007 | `/verify-image` (strip output) | `exif_analyzer.py` | `test_exif_strip.py` |
| BR-REP-003 | `/verify-image` | `geo_validator.py` | `test_vn_bbox.py` |
| BR-REP-011 | `/verify-image` | `exif_analyzer.py` | `test_exif_modified.py` |
| BR-REP-014 | `/verify-cleanup` | (Phase 7) | `test_cleanup_verify.py` |
| BR-REP-030 | `/check-duplicate` | `duplicate_detector.py` | `test_duplicate_rules.py` |

---

## 8. Câu hỏi cần làm rõ với team trước khi code

Đây là những điểm BR chưa rõ, nên align trước:

1. **AI service có quyền query trực tiếp DB Postgres của .NET không?** Hay luôn đi qua HTTP API?
2. **"Tiếng ồn"** xử lý thế nào khi AI không thể phân loại từ ảnh?
3. **pHash threshold "> 0.85"** — định nghĩa similarity scale là gì? Hamming distance / 64?
4. **Severity threshold cho diện tích** — 5%/15%/40% có chấp nhận không, hay business team có config khác?
5. **Model storage:** dùng MLflow Registry, DVC, hay đơn giản là S3 bucket có versioning?
6. **Inference quota:** có rate limit phía AI service không? (BR-REP-010 limit ở user level, nhưng AI cần limit riêng để bảo vệ?)
7. **Strip EXIF** (BR-AI-007) — strip xong lưu ở đâu? Ghi đè ảnh gốc hay lưu version mới?
8. **Privacy:** ảnh có chứa người, có cần blur mặt trước khi training/storing không?

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Dataset không đủ cho VN context | Model accuracy thấp | Crowdsource từ chính app sau khi launch (active learning) |
| Mobile model size > 50MB | App nặng, user không tải | Aggressive INT8 quantization, prune model, dùng yolov8n hoặc nhỏ hơn |
| Inference latency > 5s trên server | BR-AI-006 trigger liên tục | Pre-load model vào memory, dùng ONNX runtime với GPU, scale horizontal |
| False positive cao cho manipulation detection | Officer mất niềm tin | Document rõ score là "gợi ý", không auto-reject |
| EXIF dễ bị fake | Suspicious flag không đủ tin cậy | Combine với network signals (IP geo vs GPS), behavioral (time pattern) |
| Privacy issue khi model train trên ảnh user | Vi phạm BR-DAT, GDPR | Chỉ train trên data đã anonymize + có consent rõ ràng trong T&C |

---

## 10. Bước tiếp theo bạn nên làm

1. **Review plan này** với team .NET và Mobile, align về API contract.
2. **Quyết định 8 câu hỏi** ở mục 8.
3. **Bắt đầu Phase 0** ngay — setup repo, không cần đợi quyết định model.
4. **Song song:** team Mobile bắt đầu prototype demo app với mock server.
5. **Bắt đầu thu thập dataset** — đây là bottleneck lớn nhất, cần làm sớm.

Khi cần đi sâu vào phase nào (ví dụ: chi tiết code Phase 1, hay dataset strategy Phase 3), nói cho tôi biết để zoom in.

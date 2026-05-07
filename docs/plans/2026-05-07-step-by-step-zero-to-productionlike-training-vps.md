# Plan — Step-by-step từ zero tới feature AI thật (không demo) trên VPS

**Nguồn chuẩn:** `docs/AI_Service_Development_Plan.md` (Phase 3 model classification, Phase 4 severity, Phase 5 no-pollution flag, §7 BR matrix, §9 risks).
**Mục tiêu người dùng:** Chưa có dataset, chưa có kinh nghiệm train, chưa có VPS; cần checklist chi tiết có ví dụ làm được ngay.

---

## Goals / non-goals

**Goals**

- Có quy trình đầy đủ từ **không có gì** đến lúc API trả được: `primary_class`, `image_relevance`, `severity`, `model_version`.
- Có output cụ thể theo từng mốc:
  1) dataset YOLO hợp lệ,
  2) train trên VPS ra `best.pt`,
  3) local/API load model thật (`model_loaded: true`),
  4) test ảnh thật có kết quả hợp lý.
- Bám BR hiện có:
  - BR-AI-001 (`action`, confidence policy),
  - BR-AI-003 (`severity`),
  - BR-AI-005 (`model_version` cho audit),
  - Phase 5 no-pollution (`image_relevance` / cảnh báo ảnh tào lao).

**Non-goals**

- Không làm mọi phase còn lại (manipulation detector nâng cao, worker retry BR-AI-006, cleanup verify, mobile export) trong tài liệu này.
- Không đảm bảo accuracy production ngay lần train đầu; mục tiêu là **pipeline đúng + có baseline thật**.

---

## BR & endpoints

**Endpoint trọng tâm**

- `POST /api/v1/classify-upload` (test nhanh bằng ảnh chụp/chọn từ browser).
- `POST /api/v1/classify` (input URL, dùng cho tích hợp .NET/backend).
- `GET /api/v1/ready` (kiểm tra model có load thật hay chưa).

**Response kiểm tra (thực dụng cho đồ án)**

- `primary_class`: loại ô nhiễm chính (TRASH/WATER/SMOKE/CHEMICAL)
- `action`: AUTO_FILL / SUGGEST / KEEP_USER_CHOICE
- `image_relevance`: POLLUTION_LIKELY / NOT_POLLUTION_OR_UNRELATED / UNCLEAR_NEED_MANUAL_REVIEW
- `severity`: LOW / MEDIUM / HIGH / CRITICAL
- `pollution_coverage_ratio`: tỷ lệ vùng ô nhiễm trên ảnh
- `model_version`: bắt buộc để trace kết quả

**Pass condition tối thiểu**

- `GET /api/v1/ready` trả `model_loaded: true`.
- `/classify-upload` trả đầy đủ trường ở trên và không còn `demo-no-weights`.

---

## Execution checklist

### Step 0 — Chốt quy ước nghiệp vụ (30-60 phút)

1. Chốt 4 class train:
   - `0 TRASH`
   - `1 WATER`
   - `2 SMOKE`
   - `3 CHEMICAL`
2. Chốt guideline gán nhãn:
   - Không cần tách từng chai/lon nếu mục tiêu là cảnh ô nhiễm; có thể dùng bbox theo cụm hợp lý.
   - `NOISE` không infer từ ảnh (user chọn tay).
3. Chốt mốc POC đầu:
   - Ít nhất 200-500 ảnh có nhãn (nếu chưa đạt, có thể chạy thử với ít hơn nhưng phải ghi rõ hạn chế).

### Step 1 — Chuẩn bị local baseline (1-2 giờ)

1. Từ repo root:
   - `uv sync`
2. Tải baseline weight để kiểm tra môi trường:
   - `uv run python scripts/download_baseline_weights.py`
3. Kiểm tra file có tồn tại:
   - `ml/weights/yolov8n.pt`

### Step 2 — Thu thập ảnh thô (1-3 ngày, có thể song song)

1. Nguồn ảnh:
   - Ảnh tự chụp thực tế (ưu tiên bối cảnh VN),
   - nguồn mở có license rõ.
2. Mỗi class nên có ảnh đa dạng:
   - sáng/tối, gần/xa, mưa/nắng, góc chụp ngang/chéo, ảnh hơi blur.
3. Không để toàn một loại (ví dụ toàn TRASH) vì model sẽ bias mạnh.

### Step 3 — Gán nhãn YOLO (1-4 ngày)

1. Dùng CVAT/Roboflow/Label Studio.
2. Export YOLO detection.
3. Đặt dữ liệu đúng cấu trúc:

```text
ml/training/data/pollution/
  images/train/
  images/val/
  labels/train/
  labels/val/
```

4. Rule bắt buộc:
   - Mỗi ảnh có file `.txt` cùng tên gốc.
   - Dòng nhãn YOLO: `class xc yc w h` (0..1).
   - Không trùng ảnh giữa train và val.

### Step 4 — Validate dataset trước khi train (bắt buộc)

1. Chạy:
   - `uv run python ml/training/scripts/verify_yolo_dataset.py --root ml/training/data/pollution`
2. Chỉ qua bước tiếp theo khi:
   - Không còn lỗi thiếu cặp ảnh/nhãn,
   - class id không bị ngoài [0..3],
   - không còn file nhãn orphan.

### Step 5 — Chuẩn bị VPS train (0.5-1 ngày)

1. Chọn VPS GPU (khuyến nghị) + Ubuntu.
2. Cài công cụ:
   - `git`, `tmux`, `uv`.
3. Clone repo lên VPS.
4. Upload dataset từ local sang VPS đúng y cấu trúc `ml/training/data/pollution`.

### Step 6 — Train trên VPS (vòng 1)

1. Trên VPS, kiểm lại dataset:
   - `uv run python ml/training/scripts/verify_yolo_dataset.py --root ml/training/data/pollution`
2. Tải baseline trên VPS:
   - `uv run python scripts/download_baseline_weights.py`
3. Chạy train trong tmux:
   - `uv run python ml/training/train_yolo.py --epochs 50 --imgsz 640 --batch 8`
4. Nếu OOM:
   - giảm `--batch` xuống 4 hoặc 2.

### Step 7 — Thu model và tích hợp lại local/API

1. Lấy file:
   - `ml/training/runs/pollution_detect/weights/best.pt`
2. Copy về local:
   - đặt tại `ml/weights/best.pt`
3. Cấu hình `.env`:
   - `MODEL_PATH=ml/weights/best.pt`
   - `MODEL_VERSION=v1.0.0-<date-or-tag>`
   - `CLASSIFY_DEMO_MODE=false`
4. Khởi động API:
   - `uv run uvicorn app.main:app --host 0.0.0.0 --reload --port 8000`

### Step 8 — Test acceptance (bắt buộc trước báo cáo)

1. `GET /api/v1/ready`:
   - mong đợi `model_loaded: true`.
2. Test ảnh:
   - một ảnh ô nhiễm rõ,
   - một ảnh mơ hồ,
   - một ảnh tào lao.
3. Check output:
   - `image_relevance` phân biệt được,
   - `severity` có giá trị hợp lý,
   - `primary_class` không rỗng với ảnh ô nhiễm rõ.

### Step 9 — Vòng lặp cải thiện (v2, v3)

1. Lấy ảnh fail-case từ Step 8.
2. Annotate thêm ảnh tương tự (hard cases).
3. Train lại từ checkpoint tốt:
   - có thể dùng `--model ml/weights/best.pt`.
4. So sánh trước/sau trên cùng tập val.

---

## Files & modules

| Nhóm | File / thư mục | Vai trò |
|------|-----------------|--------|
| Train script | `ml/training/train_yolo.py` | Chạy fine-tune YOLO |
| Dataset config | `ml/training/configs/pollution_data.yaml` | Map path + class names |
| Dataset checker | `ml/training/scripts/verify_yolo_dataset.py` | Bắt lỗi cấu trúc nhãn/ảnh |
| Baseline weight downloader | `scripts/download_baseline_weights.py` | Tải `yolov8n.pt` |
| Runtime config | `.env` | Trỏ `MODEL_PATH`, `MODEL_VERSION` |
| API endpoint | `app/api/v1/classify.py` | Trả classify + relevance + severity |
| Inference core | `app/core/pollution_classifier.py` | Gom scene-level output |
| Severity rule | `app/core/severity_estimator.py` | Map coverage -> severity band |
| Relevance rule | `app/core/report_image_relevance.py` | Ảnh ô nhiễm vs tào lao |
| Demo UI | `static/demo/demo_capture_classify.html` | Test chụp/chọn ảnh nhanh |

---

## Test plan

### A. Dataset-level

- Chạy `verify_yolo_dataset.py` pass.
- Mỗi class (0..3) có ít nhất một số lượng mẫu trong train + val.
- Không có lỗi thiếu label hoặc label sai format.

### B. Train-level

- Train hoàn tất không crash.
- Có `best.pt` trong `runs/.../weights`.

### C. API-level

- `GET /api/v1/ready`: `model_loaded: true`
- `/api/v1/classify-upload`:
  - ảnh ô nhiễm rõ -> `image_relevance` nghiêng `POLLUTION_LIKELY`
  - ảnh tào lao -> `NOT_POLLUTION_OR_UNRELATED` hoặc `UNCLEAR...`
- Response luôn có `model_version`.

### D. Regression tests trong repo

- Chạy:
  - `uv run ruff check .`
  - `uv run pytest -q`

---

## Risks

| Risk | Ảnh hưởng | Giảm thiểu |
|------|-----------|------------|
| Dataset quá ít / lệch lớp | Model đoán thiên lệch | Bổ sung ảnh fail-case từng vòng |
| Nhãn không nhất quán giữa người annotate | Model học nhiễu | Viết guideline bbox rõ ràng trước khi label |
| VPS mất phiên SSH giữa chừng | Mất job train | Luôn dùng `tmux` |
| OOM khi train | Train fail / rất chậm | Giảm batch/imgsz, dùng GPU VRAM cao hơn |
| Dùng baseline COCO mà không fine-tune | Kết quả không đúng nghiệp vụ | Bắt buộc train ra `best.pt` riêng dự án |
| Overfit val nhỏ | Demo đẹp giả | Tăng val đa dạng, test thêm ảnh ngoài tập train |

---

## Ví dụ điển hình (dễ hiểu)

### Ví dụ 1 — Ảnh kênh đầy rác + nước đục

- Label:
  - nhiều bbox `TRASH`,
  - có thể thêm `WATER` nếu nhóm thống nhất quy tắc vẽ vùng nước ô nhiễm.
- Kỳ vọng infer:
  - `primary_class`: TRASH (hoặc WATER tùy evidence),
  - `image_relevance`: POLLUTION_LIKELY,
  - `severity`: MEDIUM/HIGH tùy coverage ratio.

### Ví dụ 2 — Ảnh phong cảnh bình thường (không ô nhiễm)

- Label dataset: không đưa vào tập dương, hoặc đưa như ảnh âm tùy chiến lược.
- Kỳ vọng infer:
  - `image_relevance`: NOT_POLLUTION_OR_UNRELATED,
  - `action`: KEEP_USER_CHOICE,
  - `severity`: LOW.

### Ví dụ 3 — Ảnh khó (object lạ, ánh sáng xấu)

- Kỳ vọng infer:
  - `image_relevance`: UNCLEAR_NEED_MANUAL_REVIEW.
- Hành động:
  - đưa ảnh này vào batch annotate vòng sau để cải thiện model.

---

## Deliverables (Definition of Done)

- [ ] Dataset YOLO hợp lệ và được kiểm bằng script.
- [ ] Có `best.pt` train từ dữ liệu dự án (không dùng mỗi baseline COCO).
- [ ] `.env` trỏ `MODEL_PATH=ml/weights/best.pt`, `CLASSIFY_DEMO_MODE=false`.
- [ ] API classify trả đầy đủ trường nghiệp vụ (class, relevance, severity).
- [ ] Có ảnh minh chứng trước/sau train cho báo cáo đồ án.

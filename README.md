# AI Service

AI microservice cho hệ thống báo cáo ô nhiễm môi trường (SU26SE049).

## Quick Start

```cmd
uv sync
uv run uvicorn app.main:app --reload
```

Mở: http://localhost:8000/docs

## Local Fine-Tuning Dashboard (upload -> normalize -> train)

Dashboard demo (local training orchestration): `http://localhost:8000/demo/demo_training_dashboard.html`

Supported flow:

1. Upload dataset zip with YOLO folders:
   - `images/train`, `images/val`, `labels/train`, `labels/val`
2. Service normalizes labels (class id + bbox range clamp) and stores dataset metadata.
3. Create local training job (background) from web UI.
4. Poll realtime logs + status + latest metrics from `results.csv`.
5. Optional W&B logging (`enable_wandb` + project/entity/API key or local `WANDB_API_KEY`).

New endpoints:

- `POST /api/v1/training/datasets/upload`
- `POST /api/v1/training/jobs`
- `GET /api/v1/training/jobs`
- `GET /api/v1/training/jobs/{job_id}`
- `GET /api/v1/training/jobs/{job_id}/logs?offset=0&limit=20000`

## Run with Docker

```cmd
cd docker
docker compose up --build
```

## Run tests

```cmd
uv run pytest -v
```

## Bạn đang làm đồ án — nên làm gì tiếp?

Đã có API Phase 1–3 (`verify-image`, `check-duplicate`, `classify`, `classify-upload`) và trang demo chụp ảnh. Thứ tự khuyến nghị:

1. **`copy .env.example .env`** rồi chỉnh: `MODEL_PATH`, `MODEL_VERSION`; đặt **`CLASSIFY_DEMO_MODE=false`** nếu muốn kết quả không phải dữ liệu demo giả.

2. **Có file weights `.pt`:** huấn luyện / fine-tune theo nhãn dự án (TRASH, WATER, SMOKE, CHEMICAL) — xem Phase 3 trong `docs/AI_Service_Development_Plan.md`. File đặt tại ví dụ `ml\weights\best.pt`, trỏ `MODEL_PATH` tới đó.

   Chỉ cần file baseline COCO để kiểm tra pipeline và `GET /api/v1/ready` báo **model_loaded: true**:

   ```cmd
   uv run python scripts\download_baseline_weights.py
   ```

   *(Dự báo: COCO không map vào 4 nhãn ô nhiễm trong code hiện tại → `predictions` có thể vẫn rỗng; dùng khi chứng minh tích hợp Ultralytics đã hoạt động.)*

3. **Chạy:**

   ```cmd
   uv run uvicorn app.main:app --host 0.0.0.0 --reload --port 8000
   ```

   Swagger: `/docs`. Demo luồng chụp: `/demo/demo_capture_classify.html`.

4. **Lưu trữ stripped ảnh thật (tuỳ chọn):** bật MinIO/S3, đặt `STORAGE_STUB_MODE=false` và biến `S3_*` trong `.env`.

5. **Hợp đồng với .NET / App:** họ gửi URL ảnh + JWT nội bộ; không public API AI trực tiếp từ web production. Chi tiết tích hợp FE: `docs/plans/phase-fe-app-web-ai-integration.md`.

6. **Roadmap chức năng còn thiếu so master plan:** severity, manipulation, worker timeout BR-AI-006, verify-cleanup, export TFLite — `docs/plans/phase-ai-p4-p7-*.md` và `phase-ai-p8-p9-*.md`.

7. **Huấn luyện model thật (`best.pt`):** các bước chi tiết + script — `ml/training/README.md` và `uv run python ml\training\train_yolo.py`.

8. **Dataset thật đủ combo 4 lớp (không demo):** quy trình + nguồn gợi ý — `ml/training/DATASET_GUIDE_VI.md`; kiểm tra dữ liệu — `ml/training/scripts/verify_yolo_dataset.py`.


4) Kiểm tra model load thật
Mở:
uv run uvicorn app.main:app

http://127.0.0.1:8000/api/v1/ready
Kỳ vọng:

"model_loaded": true
5) Test feature
http://127.0.0.1:8000/demo/demo_capture_classify.html
Hoặc /docs gọi POST /api/v1/classify-upload
Quan sát các field:

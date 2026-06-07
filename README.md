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

   _(Dự báo: COCO không map vào 4 nhãn ô nhiễm trong code hiện tại → `predictions` có thể vẫn rỗng; dùng khi chứng minh tích hợp Ultralytics đã hoạt động.)_

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
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Kỳ vọng:

"model_loaded": true 5) Test feature
http://127.0.0.1:8000/demo/demo_capture_classify.html
Hoặc /docs gọi POST /api/v1/classify-upload
Quan sát các field:

Bước 1 — Mày push code (làm ngay)

git add -A
git commit -m "chore: training config + retrain action plan"
git push origin dev
Bước 2 — Người kia pull + setup môi trường

git clone <repo_url>
cd greenlens-detection-ai
uv sync # cài dependencies
copy .env.example .env # tạo .env

# Sửa .env: CLASSIFY_DEMO_MODE=false, MODEL_PATH=ml/weights/best.pt

uv run python scripts/download_baseline_weights.py # tự download yolov8n.pt
Bước 3 — Share dataset (phần tốn công nhất)
Mày có 2 cách:

Cách A — USB/Google Drive (đơn giản)

Copy toàn bộ D:\CapsoneProject\DATASETFINAL\ → USB → qua máy kia
Cách B — Roboflow (sạch hơn, vì dataset của mày từ Roboflow)

Share workspace Roboflow với người kia
Họ export lại → upload qua Training Dashboard
Bước 4 — Người kia start server + train

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Mở http://localhost:8000/static/demo/demo_training_dashboard.html

# Upload dataset ZIP → Cấu hình train → Start

Tóm tắt
Thứ Cách share
Code git push ✅
yolov8n.pt Script tự download ✅
Dataset USB hoặc Roboflow share ⚠️
.env Tự tạo từ .env.example ✅
Mày muốn tao giúp viết .env.example đầy đủ không để người kia setup dễ hơn?

khi người kia train xong thì kêu ng đó gửi những gì cho tui để tui set được bên tui ?
Chỉ cần 1 file duy nhất

best.pt
Đường dẫn đầy đủ trên máy người kia:

ml/training/runs/web_jobs/<job_id>/output/pollution_detect/weights/best.pt
Sau khi nhận được best.pt
Bước 1 — Copy vào đúng chỗ:

Copy-Item "best.pt" "ml\weights\best.pt" -Force
Bước 2 — Cập nhật .env:

MODEL_PATH=ml/weights/best.pt
MODEL_VERSION=v3.0.0-3class-150ep-1280px
Bước 3 — Restart server:

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Nếu muốn có thêm số liệu để viết paper
Kêu người kia gửi thêm 2 file này:

File Dùng để làm gì
results.csv Bảng mAP50 theo từng epoch → vẽ biểu đồ
args.yaml Xác nhận config đúng (imgsz=1280, yolov8n.pt sạch)
Cả 2 file nằm cùng thư mục với best.pt:

ml/training/runs/web_jobs/<job_id>/output/pollution_detect/
├── weights/
│ └── best.pt ← bắt buộc
├── results.csv ← cần cho paper
└── args.yaml ← để verify

📊 Tỷ lệ Train/Val/Test Dataset
Dataset đang dùng (train trên Kaggle vừa xong)
Tui tìm được dataset ds_dbd5573b0d_normalized — khớp với kết quả Kaggle (158 val images):

Split Số ảnh Tỷ lệ
Train 1,214 88.4%
Val 159 11.6%
Test ❌ 0 0%
Total 1,373 100%
⚠️ Vấn đề nghiêm trọng với Paper
Không có test set riêng biệt.

Hiện tại val set đang làm cả 2 việc: vừa guide training, vừa đánh giá cuối. Đây là methodological flaw mà reviewer nào cũng sẽ bắt:

❌ Sai: Train (88%) → Val (12%) → báo mAP50 từ Val
✅ Đúng: Train (70%) → Val (15%) → Test (15%) → báo mAP50 từ Test
🔧 Cần làm trước khi viết paper
Tách test set ra ngay bây giờ, trước khi add data VN:

Tỷ lệ chuẩn cho paper:
Train : 70% → ~960 ảnh
Val : 15% → ~206 ảnh (dùng trong training)
Test : 15% → ~207 ảnh (chỉ dùng để báo kết quả cuối, không touch trong lúc train)
Quan trọng: Test set phải được lock lại ngay — không được dùng để tune model, chỉ chạy 1 lần duy nhất để báo số liệu final.

📋 Phân bổ theo class (ước tính từ training result)
Class Val images Val instances Nhận xét
TRASH 42 60 Ổn
WATER 63 152 Nhiều instances nhưng model yếu → class imbalance trong train
SMOKE 53 57 Tốt
WATER có nhiều ảnh nhất nhưng mAP50 chỉ 0.242 → khả năng data quality vấn đề, không phải quantity.

✅ Action plan
Ngay hôm nay → Tách 15% làm test set, lock lại
+4 ngày → Nhận 500 ảnh VN → split tương tự 70/15/15 → merge vào train+val
Train lại → Báo mAP50 từ test set mới clean

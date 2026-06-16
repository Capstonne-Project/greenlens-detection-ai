<div align="center">

<!-- 3D Animated Header -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=200&section=header&text=GreenLens%20AI&fontSize=60&fontColor=fff&animation=twinkling&fontAlignY=35&desc=Environmental%20Pollution%20Detection%20Microservice&descAlignY=55&descSize=18" width="100%"/>

<!-- Animated badges -->
<p>
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.136+-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/YOLOv8-Ultralytics-FF6B35?style=for-the-badge&logo=pytorch&logoColor=white"/>
  <img src="https://img.shields.io/badge/EfficientNet-B0-764ABC?style=for-the-badge&logo=tensorflow&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
</p>

<p>
  <img src="https://img.shields.io/badge/Project-SU26SE049-00C851?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/License-Academic-orange?style=for-the-badge"/>
</p>

<!-- Animated typing -->
<a href="https://git.io/typing-svg">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&pause=1000&color=00C851&center=true&vCenter=true&multiline=true&width=600&height=80&lines=AI+microservice+ph%C3%A2n+lo%E1%BA%A1i+%C3%B4+nhi%E1%BB%85m+m%C3%B4i+tr%C6%B0%E1%BB%9Dng+%F0%9F%8C%BF;TRASH+%E2%80%A2+WATER+%E2%80%A2+SMOKE+%E2%80%A2+CHEMICAL+detection" alt="Typing SVG" />
</a>

</div>

---

## 🗺️ Mindmap — Kiến trúc hệ thống

```
                         ┌─────────────────────────────┐
                         │       GreenLens AI 🌿        │
                         │   FastAPI Microservice        │
                         └──────────┬──────────────────-┘
                                    │
          ┌─────────────────────────┼──────────────────────────┐
          │                         │                          │
   ┌──────▼──────┐         ┌────────▼────────┐        ┌───────▼───────┐
   │  📡 API v1  │         │  🧠 AI Core     │        │  🗄️ Services  │
   └──────┬──────┘         └────────┬────────┘        └───────┬───────┘
          │                         │                          │
   ┌──────┴──────────┐    ┌─────────┴──────────┐    ┌─────────┴──────────┐
   │                 │    │                    │    │                    │
   ▼                 ▼    ▼                    ▼    ▼                    ▼
 /classify     /classify  PollutionClassifier  SceneClassifier  StorageService
 (URL)         -upload    ┌──────────────┐     (EfficientNet)   (S3/MinIO/HTTP)
               │          │  YOLOv8      │
 /verify-image │          │  Detection   │     TrashSubtype     TrainingJobs
 /check-dup    │          ├──────────────┤     Classifier       (Background)
 /training/*   │          │  Severity    │
               │          │  Estimator   │     ImageDecode      WandB Logger
               │          └──────────────┘     (HEIC/JPEG/PNG)
               │
       ┌───────┘
       ▼
   ImageFile
   (HEIC/JPEG/PNG)
   Auto-resize → 1920px
   EXIF-safe decode
```

---

## ✨ Tính năng

| Feature | Mô tả |
|---|---|
| 🔍 **Object Detection** | YOLOv8 phát hiện ô nhiễm với bounding box |
| 🏷️ **Scene Classification** | EfficientNet-B0 phân loại cảnh tổng thể |
| 📊 **Severity Estimation** | Tự động đánh giá mức độ nghiêm trọng |
| ♻️ **Trash Subtype** | Phân loại chi tiết loại rác |
| 📱 **Mobile-First** | Nhận ảnh từ camera ĐT, tự resize, hỗ trợ HEIC |
| 🎯 **4 Classes** | TRASH · WATER · SMOKE · CHEMICAL |
| 🐳 **Docker Ready** | Deploy production với một lệnh |
| 📈 **Training Dashboard** | Web UI upload dataset → train → monitor realtime |

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone <repo_url>
cd greenlens-detection-ai
uv sync
copy .env.example .env
```

### 2. Download model weights

```bash
uv run python scripts/download_baseline_weights.py
```

### 3. Chạy server

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --reload --port 8000
```

Mở Swagger UI: **http://localhost:8000/docs**

---

## 🐳 Docker

```bash
cd docker
docker compose up --build
```

---

## 🏗️ Project Structure

```
greenlens-detection-ai/
├── app/
│   ├── api/v1/
│   │   ├── classify.py        # POST /classify, /classify-upload
│   │   ├── images.py          # Image preview/convert endpoint
│   │   ├── health.py          # GET /ready
│   │   └── training.py        # Training job management
│   ├── core/
│   │   ├── pollution_classifier.py    # Orchestrator (YOLO + EfficientNet)
│   │   ├── scene_classifier.py        # EfficientNet-B0
│   │   ├── trash_subtype_classifier.py
│   │   └── severity_estimator.py
│   ├── services/
│   │   └── storage_service.py  # S3 / HTTP / local file fetch
│   └── utils/
│       └── image_decode.py     # HEIC/JPEG/PNG decode + auto-resize
├── ml/
│   ├── weights/                # best.pt đặt ở đây
│   └── training/               # train_yolo.py, scripts, README
├── docker/
│   └── docker-compose.yml
├── scripts/
│   └── download_baseline_weights.py
└── .env.example
```

---

## 🔌 API Endpoints

```
POST  /api/v1/classify            # Classify từ URL ảnh
POST  /api/v1/classify-upload     # Classify từ file upload (camera/gallery)
POST  /api/v1/images/preview      # Convert HEIC → JPEG preview
GET   /api/v1/ready               # Health check + model_loaded status

POST  /api/v1/training/datasets/upload   # Upload dataset ZIP
POST  /api/v1/training/jobs              # Tạo training job
GET   /api/v1/training/jobs              # List jobs
GET   /api/v1/training/jobs/{id}         # Job status
GET   /api/v1/training/jobs/{id}/logs    # Realtime logs
```

### Response mẫu `/classify-upload`

```json
{
  "primary_class": "TRASH",
  "confidence": 0.87,
  "action": "REPORT",
  "predictions": [
    {
      "pollutant_kind": "TRASH",
      "confidence": 0.87,
      "bbox_count": 3,
      "boxes": [{"x1": 0.1, "y1": 0.2, "x2": 0.5, "y2": 0.6, "confidence": 0.87}]
    }
  ],
  "model_version": "v3.0.0",
  "yolo_active": true
}
```

---

## ⚙️ Cấu hình `.env`

```env
# Model
MODEL_PATH=ml/weights/best.pt
MODEL_VERSION=v3.0.0
CLASSIFY_DEMO_MODE=false        # true = trả dữ liệu giả để test UI

# Storage (tuỳ chọn — bỏ qua để dùng stub mode)
STORAGE_STUB_MODE=true
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=greenlens
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

---

## 🧪 Tests

```bash
uv run pytest -v
```

---

## 📊 Model Performance (v3 — 1,373 ảnh)

| Class | mAP50 | Instances |
|---|---|---|
| TRASH | ~0.71 | 60 val |
| SMOKE | ~0.65 | 57 val |
| WATER | ~0.24 | 152 val |

> WATER mAP thấp do class imbalance trong training data. Roadmap: bổ sung ảnh thực tế VN.

---

## 🗺️ Mindmap — Luồng xử lý ảnh

```
  📱 Điện thoại chụp ảnh
          │
          ▼
  POST /classify-upload
  (multipart/form-data)
          │
          ▼
  ┌───────────────────┐
  │   image_decode    │
  │  ┌─────────────┐  │
  │  │ HEIC? → reg │  │
  │  │ heif opener │  │
  │  └──────┬──────┘  │
  │         ▼         │
  │  Pillow decode    │
  │  (truncate-safe)  │
  │         ▼         │
  │  > 1920px?        │
  │  → resize (LANCZOS│
  │         ▼         │
  │  → JPEG bytes     │
  └─────────┬─────────┘
            │
            ▼
  ┌─────────────────────────────┐
  │     PollutionClassifier     │
  │                             │
  │  ┌──────────┐ ┌──────────┐  │
  │  │  YOLOv8  │ │EffNet-B0 │  │
  │  │Detection │ │  Scene   │  │
  │  └────┬─────┘ └────┬─────┘  │
  │       │            │        │
  │       ▼            ▼        │
  │   Bounding    Scene label   │
  │   Boxes +     + confidence  │
  │   classes                   │
  │       │            │        │
  │       └─────┬──────┘        │
  │             ▼               │
  │    SeverityEstimator        │
  │    TrashSubtypeClassifier   │
  └─────────────┬───────────────┘
                │
                ▼
        ClassifyResponse
        (JSON → Mobile App)
```

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI + Uvicorn |
| **Detection** | YOLOv8 (Ultralytics) |
| **Classification** | EfficientNet-B0 (PyTorch) |
| **Image Processing** | Pillow 12 + pillow-heif |
| **Storage** | AWS S3 / MinIO |
| **Package Manager** | uv |
| **Logging** | structlog |
| **Training Monitor** | Weights & Biases |
| **Container** | Docker Compose |

</div>

---

## 🗺️ Mindmap — Training Pipeline

```
  📁 Dataset (YOLO format)
  images/train + images/val
  labels/train + labels/val
          │
          ▼
  Training Dashboard (Web UI)
  localhost:8000/demo/demo_training_dashboard.html
          │
          ▼
  POST /api/v1/training/datasets/upload
  → normalize labels
  → store metadata
          │
          ▼
  POST /api/v1/training/jobs
  → background training job
          │
          ├──→ YOLOv8 train
          │      imgsz=1280
          │      epochs=150
          │      pretrained=yolov8n.pt
          │
          ├──→ W&B logging (optional)
          │
          ▼
  GET /api/v1/training/jobs/{id}/logs
  → realtime stdout stream
          │
          ▼
  ml/training/runs/web_jobs/{id}/
  ├── weights/best.pt   ← deploy này
  ├── results.csv       ← mAP50 chart
  └── args.yaml         ← verify config
```

---

## 📱 Tích hợp Mobile App

Mobile App (.NET MAUI / React Native) giao tiếp qua **internal JWT** — không expose AI API trực tiếp ra internet:

```
Mobile App
    │  POST image (multipart)
    ▼
.NET Backend (API Gateway)
    │  Verify JWT
    │  Forward bytes
    ▼
GreenLens AI (internal)
    │  classify_upload()
    ▼
ClassifyResponse → Mobile App
```

Chi tiết: `docs/plans/phase-fe-app-web-ai-integration.md`

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%"/>

**SU26SE049 — Capstone Project 2026**

Made with 💚 for a cleaner environment

</div>

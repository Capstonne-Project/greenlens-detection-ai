# Implementation Status — GreenLens Detection AI

> Cập nhật: 2026-05-26

---

## ✅ Đã hoàn thành — Trash Subtype 2-Stage Pipeline

### Flow hệ thống hiện tại (sau khi implement)

```
Input Image
    ↓
[Stage 1] YOLOv8n  →  detect TRASH / WATER / SMOKE + bbox
    ↓
[Stage 2] TrashSubtypeClassifier (EfficientNet-B0)
          → Crop từng TRASH bbox
          → Classify: CONSTRUCTION | ELECTRONIC | HAZARDOUS | MEDICAL | ORGANIC | RECYCLABLE
    ↓
[ScenePollutionClassifier] (song song với Stage 1)
          → WATER / SMOKE probability (scene-level)
    ↓
[Merge + Severity + Relevance]
    ↓
API Response với subtypes field
```

---

## 📁 Files đã thay đổi / tạo mới

### Tạo mới

| File | Mục đích |
|---|---|
| `app/core/trash_subtype_classifier.py` | EfficientNet-B0 wrapper — crop bbox → classify subtype |
| `ml/training/train_trash_subtype_classifier.py` | Script train model subtype (clone từ train_scene_classifier.py) |

### Sửa đổi

| File | Thay đổi |
|---|---|
| `app/config.py` | + `trash_subtype_model_path`, `trash_subtype_threshold` |
| `app/models/classify.py` | + `TrashSubtypePrediction` schema, `subtypes` field trong `ClassificationPrediction`, `subtype/subtype_confidence` trong `DetectedBox`, `trash_subtype_active` trong `ClassifyResponse` |
| `app/core/pollution_classifier.py` | + `_trash_subtype_clf` instance, `_aggregate_subtypes()`, integrate Stage 2 vào `_run_yolo()`, `trash_subtype_active` trong `ClassificationResult` |
| `app/api/v1/classify.py` | + import `TrashSubtypePrediction`, map `subtypes` và `trash_subtype_active` vào response |

---

## 🔄 API Response — Trước và Sau

### Trước

```json
{
  "predictions": [
    {
      "class": "TRASH",
      "confidence": 0.87,
      "bbox_count": 3,
      "boxes": [
        { "x1": 100, "y1": 200, "x2": 300, "y2": 400, "confidence": 0.87 }
      ]
    }
  ],
  "primary_class": "TRASH",
  "severity": "MEDIUM"
}
```

### Sau

```json
{
  "predictions": [
    {
      "class": "TRASH",
      "confidence": 0.87,
      "bbox_count": 3,
      "boxes": [
        {
          "x1": 100, "y1": 200, "x2": 300, "y2": 400,
          "confidence": 0.87,
          "subtype": "RECYCLABLE",
          "subtype_confidence": 0.92
        },
        {
          "x1": 50, "y1": 100, "x2": 150, "y2": 250,
          "confidence": 0.75,
          "subtype": "MEDICAL",
          "subtype_confidence": 0.78
        }
      ],
      "subtypes": [
        { "subtype": "RECYCLABLE", "count": 2, "confidence": 0.92 },
        { "subtype": "MEDICAL",    "count": 1, "confidence": 0.78 }
      ]
    }
  ],
  "primary_class": "TRASH",
  "severity": "MEDIUM",
  "trash_subtype_active": true
}
```

---

## ⚙️ Graceful Degradation

Hệ thống hoạt động đúng ở mọi trạng thái:

| Trạng thái | Behavior |
|---|---|
| Không có `TRASH_SUBTYPE_MODEL_PATH` trong `.env` | `subtypes = null`, `trash_subtype_active = false` |
| Có path nhưng file không tồn tại | Tương tự trên — không crash |
| Có model loaded | `subtypes` populated, `trash_subtype_active = true` |
| TRASH không được detect | `subtypes` không xuất hiện trong response |

---

## 🚧 Còn thiếu — Cần làm tiếp

### 1. Dataset cho Subtype Classifier (chưa có)

```
ml/training/data/trash_subtype/
└── images/
    ├── train/
    │   ├── CONSTRUCTION/   ← cần ~350 ảnh
    │   ├── ELECTRONIC/     ← cần ~350 ảnh
    │   ├── HAZARDOUS/      ← cần ~280 ảnh
    │   ├── MEDICAL/        ← cần ~280 ảnh (khẩu trang VN!)
    │   ├── ORGANIC/        ← cần ~350 ảnh
    │   └── RECYCLABLE/     ← cần ~350 ảnh
    └── val/
        └── (auto-split 15% nếu không có)
```

**Nguồn dataset gợi ý:**
- TACO: https://github.com/pedropro/TACO
- TrashNet: Roboflow → garythung/trashnet
- Kaggle Garbage Classification: mostafaabla/garbage-classification
- Tự chụp ảnh VN: khẩu trang, gạch, rác chợ

### 2. Train model

```bash
# Trên Kaggle T4 (giống cách train YOLO)
uv run python ml/training/train_trash_subtype_classifier.py \
    --data-root ml/training/data/trash_subtype \
    --epochs 100 \
    --batch-size 32
```

### 3. Kích hoạt trong .env

```env
TRASH_SUBTYPE_MODEL_PATH=ml/weights/trash_subtype_classifier.pt
TRASH_SUBTYPE_THRESHOLD=0.40
```

### 4. Test dataset split

- Tách 15% test set từ dataset trước khi train
- Lock test set — chỉ dùng 1 lần để báo số liệu paper

---

## 📊 Trạng thái model hiện tại

| Model | Weights | mAP50 / Accuracy | Trạng thái |
|---|---|---|---|
| **YOLOv8n (YOLO detector)** | `ml/weights/best.pt` (6.4 MB) | mAP50 = 0.597 | ✅ Chạy được |
| **EfficientNet-B0 (scene)** | `ml/weights/scene_classifier.pt` (16 MB) | Chưa đo lại | ✅ Chạy được |
| **EfficientNet-B0 (subtype)** | Chưa có | — | ⏳ Chờ dataset |

### YOLO kết quả chi tiết (greenlens_v3_clean, 150 epochs, Kaggle T4)

| Class | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| SMOKE | 0.712 | 0.842 | 0.813 | 0.410 |
| TRASH | 0.691 | 0.700 | 0.737 | 0.378 |
| WATER | 0.457 | 0.255 | 0.242 | 0.080 |
| **ALL** | **0.620** | **0.599** | **0.597** | **0.289** |

> WATER recall thấp (0.255) vì WATER là scene-level pollution, khó detect bằng bbox.
> Scene classifier (EfficientNet) bù đắp phần này.

---

## 🗺️ Roadmap

```
✅ DONE   Code 2-stage pipeline (Stage 1 YOLO + Stage 2 Subtype)
✅ DONE   API schema mở rộng với subtypes field
✅ DONE   Training script sẵn sàng
⏳ TODO   Thu thập dataset trash subtype (~2k ảnh, 6 classes)
⏳ TODO   Train trash_subtype_classifier.pt trên Kaggle
⏳ TODO   Tách test set 15% — lock trước khi train
⏳ TODO   Nhận 500 ảnh VN (+4 ngày) → add vào YOLO dataset → retrain
⏳ TODO   Đo lại mAP50 với VN data → so sánh với baseline 0.597
⏳ TODO   Viết paper Section 3 (Dataset) + Section 4 (Methodology)
```

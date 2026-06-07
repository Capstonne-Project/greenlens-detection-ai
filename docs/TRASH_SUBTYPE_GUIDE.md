# Hướng dẫn: Phân loại chi tiết loại rác sau khi detect TRASH

> Tài liệu này mô tả flow, dataset, cách train, và cách tích hợp
> hệ thống phân loại loại rác (trash subtype) vào pipeline GreenLens hiện tại.

---

## 1. Bức tranh toàn cảnh — Flow hoạt động

### Hiện tại (Phase 1)

```
Ảnh đầu vào
    ↓
[YOLOv8n] — detect vùng ô nhiễm
    ↓
Kết quả: "TRASH" | "WATER" | "SMOKE" + tọa độ bbox
    ↓
API trả về: { class: "TRASH", confidence: 0.87, severity: "MEDIUM" }
```

### Mục tiêu (Phase 2 — Trash Subtype)

```
Ảnh đầu vào
    ↓
[Stage 1] YOLOv8n — detect vùng ô nhiễm
    ↓
Phát hiện "TRASH" bbox? ──No──→ Kết thúc như cũ
    ↓ Yes
[Stage 2] Crop từng bbox TRASH ra
    ↓
[TrashSubtypeClassifier] — EfficientNet-B0 phân loại từng crop
    ↓
Gộp kết quả: loại rác nào xuất hiện nhiều nhất trong ảnh
    ↓
API trả về:
{
  class: "TRASH",
  confidence: 0.87,
  severity: "MEDIUM",
  subtypes: [
    { subtype: "RECYCLABLE", count: 2, confidence: 0.92 },
    { subtype: "MEDICAL",    count: 1, confidence: 0.78 }
  ]
}
```

---

## 2. Phân tích 9 loại rác — Cái gì detect được bằng CV?

Không phải loại nào cũng nhận dạng được từ ảnh.
Dưới đây là đánh giá thực tế:

| # | Loại rác | Ví dụ cụ thể | Nhận dạng bằng CV? | Lý do |
|---|---|---|---|---|
| 1 | Rác sinh hoạt | Túi nilon, giấy, quần áo cũ | ⚠️ Khó | Quá đa dạng, hay lẫn với loại khác |
| 2 | Rác hữu cơ | Thức ăn thừa, rau củ hỏng | ⚠️ Trung bình | Phân biệt được qua màu sắc, texture |
| 3 | Rác vô cơ | Nhựa, kim loại, cao su | ⚠️ Trung bình | Overlap với Recyclable |
| 4 | Rác tái chế | Chai PET, lon nhôm, carton | ✅ Tốt | Hình dạng đặc trưng, có dataset |
| 5 | Rác nguy hại | Pin, bình hóa chất, bóng đèn | ✅ Tốt | Hình dạng nhận ra được |
| 6 | Rác y tế | Khẩu trang, kim tiêm, bông băng | ✅ Rất tốt | Post-COVID rất phổ biến ở VN |
| 7 | Rác công nghiệp | Dầu thải, phế liệu nhà máy | ❌ Khó | Nhìn giống rác vô cơ thường |
| 8 | Rác điện tử | Điện thoại, laptop, dây cáp | ✅ Tốt | Linh kiện nhận ra được rõ ràng |
| 9 | Rác xây dựng | Gạch, xi măng, bê tông vụn | ✅ Tốt | Texture và màu sắc đặc trưng |

### Kết luận: 6 class khả thi cho paper

Gộp lại những gì phân biệt được rõ bằng mắt:

```python
TRASH_SUBTYPES = [
    "RECYCLABLE",     # Chai PET, lon nhôm, carton → hình dạng rõ
    "ORGANIC",        # Thức ăn, rau củ hỏng → màu, texture
    "MEDICAL",        # Khẩu trang, kim tiêm → rất phổ biến VN
    "ELECTRONIC",     # Điện thoại, laptop, dây cáp → dễ nhận
    "CONSTRUCTION",   # Gạch, xi măng, cát → texture đặc trưng
    "HAZARDOUS",      # Pin, bình hóa chất → hình dạng nhận được
]
```

> **Lý do bỏ "Rác sinh hoạt" và "Rác công nghiệp" riêng:**
> Hai loại này không có đặc điểm visual đủ khác biệt.
> Rác sinh hoạt thường là catch-all của RECYCLABLE + ORGANIC.
> Rác công nghiệp overlap với HAZARDOUS.

---

## 3. Kiến trúc kỹ thuật — 2-Stage Pipeline

```
┌─────────────────────────────────────────────────┐
│                   INPUT IMAGE                    │
└──────────────────────┬──────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│  STAGE 1: YOLOv8n (đang có)                     │
│  → Detect: TRASH / WATER / SMOKE                 │
│  → Output: bbox coordinates + confidence         │
└──────────────────────┬──────────────────────────┘
                       ↓
          Có TRASH bbox không?
          /              \
        Không             Có
          ↓                ↓
     Kết quả cũ    ┌────────────────────────────┐
                   │  STAGE 2: Subtype Classifier │
                   │  (train mới — EfficientNet)  │
                   │                              │
                   │  Với mỗi TRASH bbox:         │
                   │  1. Crop vùng bbox từ ảnh    │
                   │  2. Resize về 224x224         │
                   │  3. Normalize (ImageNet stats)│
                   │  4. EfficientNet-B0 forward   │
                   │  5. Softmax → top-1 subtype   │
                   └──────────────┬───────────────┘
                                  ↓
                   ┌────────────────────────────┐
                   │  AGGREGATE kết quả:         │
                   │  Đếm subtype theo frequency  │
                   │  Sort by count + confidence  │
                   └──────────────┬───────────────┘
                                  ↓
                          Final API Response
```

### Model Stage 2

| Thành phần | Chi tiết |
|---|---|
| Backbone | EfficientNet-B0 (pretrained ImageNet) |
| Custom head | Linear(1280 → 256) → ReLU → Dropout(0.3) → Linear(256 → 6) |
| Input | Cropped TRASH bbox, resize 224×224 |
| Output | Softmax probabilities, 6 classes |
| Weights file | `ml/weights/trash_subtype_classifier.pt` |
| Pattern code | Clone từ `app/core/scene_classifier.py` |

---

## 4. Dataset — Cần chuẩn bị gì?

### 4.1 Yêu cầu tối thiểu

| Class | Min ảnh | Target | Ghi chú |
|---|---|---|---|
| RECYCLABLE | 300 | 500 | Chai PET, lon, carton |
| ORGANIC | 300 | 500 | Thức ăn thừa, rau củ |
| MEDICAL | 200 | 400 | Khẩu trang ← ưu tiên VN |
| ELECTRONIC | 300 | 500 | Điện thoại, laptop, cáp |
| CONSTRUCTION | 300 | 500 | Gạch, xi măng, cát |
| HAZARDOUS | 200 | 400 | Pin, bình hóa chất |
| **Total** | **1,600** | **2,800** | |

### 4.2 Nguồn dataset có sẵn (không cần thu thập từ đầu)

#### Dataset Public — Dùng ngay

| Dataset | Classes có | Số ảnh | Cách lấy |
|---|---|---|---|
| **TACO** (Trash Annotations in Context) | Plastic, Metal, Glass, Paper, Organic | ~1,500 | GitHub: pedropro/TACO |
| **TrashNet** (Stanford) | Glass, Paper, Cardboard, Plastic, Metal, Trash | 2,527 | Roboflow: garythung/trashnet |
| **Open Images v7** (Google) | Bottles, Cans, Electronics, Medical | Lớn | Roboflow Universe |
| **Garbage Classification** | 12 categories | 15,000+ | Kaggle: mostafaabla/garbage-classification |
| **Medical Waste** | Mask, Syringe, Glove | ~800 | Roboflow Universe |

#### Dataset Việt Nam — Cần tự thu thập

| Class | Cách thu thập | Ghi chú |
|---|---|---|
| MEDICAL (khẩu trang) | Chụp tại địa phương | Rất phổ biến sau COVID |
| CONSTRUCTION | Chụp tại công trình | Đặc thù VN (gạch đỏ) |
| ORGANIC | Chợ, bãi rác địa phương | Rau củ VN khác phương Tây |

### 4.3 Format dataset cho Stage 2 Classifier

**KHÔNG cần annotation bbox** (khác Stage 1).
Chỉ cần ảnh được đặt đúng thư mục theo class:

```
ml/training/data/trash_subtype/
├── images/
│   ├── train/
│   │   ├── RECYCLABLE/
│   │   │   ├── img_001.jpg
│   │   │   ├── img_002.jpg
│   │   │   └── ...
│   │   ├── ORGANIC/
│   │   ├── MEDICAL/
│   │   ├── ELECTRONIC/
│   │   ├── CONSTRUCTION/
│   │   └── HAZARDOUS/
│   └── val/
│       ├── RECYCLABLE/
│       ├── ORGANIC/
│       └── ...
```

### 4.4 Tỷ lệ split

```
Train : 70% — dùng để train model
Val   : 15% — monitor trong lúc train (early stopping)
Test  : 15% — chỉ dùng 1 lần để báo kết quả trong paper
```

> **Quan trọng:** Lock test set từ đầu, KHÔNG dùng để tune model.

### 4.5 Data Augmentation (áp dụng khi train)

```python
# Áp dụng cho training set để tăng tính tổng quát
augmentations = [
    RandomHorizontalFlip(p=0.5),
    RandomRotation(degrees=15),
    ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    RandomResizedCrop(224, scale=(0.7, 1.0)),
    GaussianBlur(kernel_size=3, p=0.2),
]

# Val/Test: chỉ resize + normalize, không augment
val_transform = Compose([
    Resize(256),
    CenterCrop(224),
    ToTensor(),
    Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
```

---

## 5. Cách train — Step by Step

### Step 1: Chuẩn bị dataset

```bash
# Download TrashNet từ Roboflow (đã có sẵn format folder)
# Download TACO và convert sang folder structure

# Script convert TACO → folder structure (nếu cần)
uv run python ml/training/scripts/prepare_trash_subtype_dataset.py \
    --taco-dir ml/training/data/taco_raw \
    --output-dir ml/training/data/trash_subtype
```

### Step 2: Train model

```bash
# Train trash subtype classifier
uv run python ml/training/train_trash_subtype_classifier.py \
    --data-dir ml/training/data/trash_subtype \
    --epochs 100 \
    --batch-size 32 \
    --lr 0.001 \
    --output ml/weights/trash_subtype_classifier.pt
```

### Step 3: Evaluate

```bash
# Xem kết quả trên test set
uv run python ml/training/evaluate_trash_subtype.py \
    --weights ml/weights/trash_subtype_classifier.pt \
    --test-dir ml/training/data/trash_subtype/images/test
```

### Hyperparameters đề xuất

| Parameter | Giá trị | Lý do |
|---|---|---|
| Backbone | EfficientNet-B0 | Nhẹ, đã proven, tương thích codebase |
| Pretrained | ImageNet | Transfer learning → hội tụ nhanh hơn |
| Epochs | 100 | Đủ để converge với ~2k ảnh |
| Batch size | 32 | Phù hợp GPU Kaggle T4 |
| Learning rate | 1e-3 (warmup) → 1e-4 | Cosine annealing |
| Optimizer | AdamW | Tốt hơn Adam với weight decay |
| Early stopping | patience=15 | Tránh overfit |
| Input size | 224×224 | Chuẩn EfficientNet-B0 |

---

## 6. Tích hợp vào code hiện tại

### 6.1 Files cần thay đổi

```
app/
├── core/
│   ├── trash_subtype_classifier.py    ← TẠO MỚI (clone từ scene_classifier.py)
│   └── pollution_classifier.py        ← SỬA: tích hợp Stage 2 vào _run_yolo()
├── models/
│   └── classify.py                    ← SỬA: thêm subtypes field vào schema
└── config.py                          ← SỬA: thêm 2 setting mới
```

### 6.2 Thay đổi cụ thể trong pollution_classifier.py

```python
# Hiện tại trong _run_yolo():
predictions = [
    {
        "class": cls,
        "confidence": round(class_best_conf[cls], 4),
        "bbox_count": count,
        "boxes": class_raw_boxes[cls],   # boxes chưa có subtype
    }
]

# Sau khi tích hợp:
predictions = [
    {
        "class": cls,
        "confidence": round(class_best_conf[cls], 4),
        "bbox_count": count,
        "boxes": class_raw_boxes[cls],   # mỗi box có thêm "subtype" và "subtype_confidence"
        "subtypes": _aggregate_subtypes(class_raw_boxes[cls]),  # gộp theo frequency
    }
]
```

### 6.3 API Response mới

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
  "confidence": 0.87,
  "severity": "MEDIUM",
  "action": "AUTO_FILL"
}
```

---

## 7. Graceful Degradation — Nếu chưa có model

Hệ thống thiết kế để **vẫn hoạt động bình thường** khi chưa có weights subtype:

```
trash_subtype_model_path = ""  (rỗng trong .env)
    ↓
TrashSubtypeClassifier.is_loaded() → False
    ↓
subtypes = None  (không có trong response)
    ↓
API vẫn trả TRASH + severity bình thường
```

Nghĩa là có thể **deploy code trước, train model sau**.

---

## 8. Checklist — Từng bước cụ thể

### Phase 2a — Chuẩn bị (tuần này)

- [ ] Download TACO dataset từ GitHub
- [ ] Download TrashNet từ Kaggle
- [ ] Download Medical Waste dataset từ Roboflow
- [ ] Tự chụp ảnh tại VN: khẩu trang, rác xây dựng, rác hữu cơ địa phương
- [ ] Viết script convert sang folder structure
- [ ] Tách test set 15% và LOCK lại

### Phase 2b — Train model (sau khi có dataset)

- [ ] Tạo `ml/training/train_trash_subtype_classifier.py`
- [ ] Train trên Kaggle T4 (100 epochs, ~1 giờ)
- [ ] Đánh giá trên test set — ghi lại accuracy per class
- [ ] Phân tích confusion matrix — class nào dễ nhầm?

### Phase 2c — Tích hợp code

- [ ] Tạo `app/core/trash_subtype_classifier.py`
- [ ] Sửa `app/config.py` — thêm 2 setting
- [ ] Sửa `app/models/classify.py` — thêm subtypes schema
- [ ] Sửa `app/core/pollution_classifier.py` — integrate Stage 2
- [ ] Chạy unit test và test API end-to-end

### Phase 2d — Paper

- [ ] Ghi lại baseline: TRASH-only (Phase 1) vs TRASH+Subtype (Phase 2)
- [ ] Viết Section 4.3 (Trash Subtype Classification Module)
- [ ] Viết Section 5.3 (Subtype Experiment Results)
- [ ] Tạo confusion matrix figure cho paper

---

## 9. Kết quả mong đợi cho paper

### Metrics cần báo cáo

| Metric | RECYCLABLE | ORGANIC | MEDICAL | ELECTRONIC | CONSTRUCTION | HAZARDOUS | Avg |
|---|---|---|---|---|---|---|---|
| Precision | ? | ? | ? | ? | ? | ? | ? |
| Recall | ? | ? | ? | ? | ? | ? | ? |
| F1-Score | ? | ? | ? | ? | ? | ? | ? |
| Accuracy (top-1) | — | — | — | — | — | — | ? |

> Target: Average F1 ≥ 0.75 để đủ sức submit conference.

### Contribution cho paper

> "GreenLens không chỉ phát hiện ô nhiễm rác thải mà còn tự động
> phân loại thành 6 loại rác cụ thể phục vụ công tác xử lý và tái chế,
> đặc biệt phù hợp với bối cảnh rác thải đô thị Việt Nam."

---

## 10. Câu hỏi thường gặp

**Q: Tại sao không train 1 YOLO model với tất cả subclass luôn?**
A: Cần ~2,000 ảnh/class có annotation bbox — quá tốn công gán nhãn.
   Approach 2-stage chỉ cần ảnh folder, không cần vẽ bbox.

**Q: Crop từ bbox YOLO thì có mất ngữ cảnh không?**
A: Có, nhưng crop giữ đủ thông tin về object chính.
   Scene context (background) thường gây nhiễu hơn là giúp ích cho subtype.

**Q: Nếu 1 bbox có nhiều loại rác lẫn lộn thì sao?**
A: Classifier trả ra top-1 subtype của region đó.
   Nhiều bbox → nhiều subtype → aggregate cho toàn ảnh.
   Đây là limitation cần nêu trong paper (Section 6 — Discussion).

**Q: Có thể dùng CLIP hoặc foundation model không?**
A: Có thể, nhưng phức tạp hơn và cần GPU lớn hơn.
   EfficientNet-B0 đủ tốt với dataset 2k-3k ảnh và inference nhanh hơn nhiều.

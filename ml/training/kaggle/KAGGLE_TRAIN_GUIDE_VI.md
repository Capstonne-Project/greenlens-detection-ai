# Huấn luyện GreenLens trên Kaggle (E1 — Fine-tuned YOLO)

> Hướng A — bước 1: train **YOLOv8n 2 class** (TRASH/WATER) trên GPU Kaggle, không cần máy local.

---

## Chuẩn bị trên máy (trước khi máy hỏng)

1. File **`merged_dataset.zip`** từ tab Gộp Dataset (có `images/train|val|test` + `labels/...`).
2. (Tuỳ chọn) Push repo lên GitHub để clone trên Kaggle.

---

## Bước 1 — Upload dataset lên Kaggle

1. Vào [kaggle.com](https://www.kaggle.com) → **Your Work** → **Datasets** → **New Dataset**
2. Upload `merged_dataset.zip` (hoặc zip cả folder đã giải nén)
3. Đặt tên ví dụ: `greenlens-merged-2class`
4. **Public** hoặc **Private** đều được

---

## Bước 2 — Tạo Notebook

1. **New Notebook**
2. **Settings** (bên phải):
   - **Accelerator:** GPU T4 x2 (hoặc P100 nếu có)
   - **Internet:** ON (cần tải `yolov8n.pt`)
   - **Persistence:** bật nếu train > 12h (Kaggle free ~30h/tuần GPU)
3. **Add Data** → tìm dataset `greenlens-merged-2class` → Add

Đường dẫn thường là:

```text
/kaggle/input/greenlens-merged-2class/merged_dataset.zip
```

---

## Bước 3 — Chạy train (copy notebook)

Tạo notebook, dán các cell sau:

### Cell 1 — Kiểm tra GPU

```python
!nvidia-smi
```

### Cell 2 — Train (script trong repo)

**Cách A — Clone repo:**

```python
!git clone https://github.com/<USER>/greenlens-detection-ai.git
%cd greenlens-detection-ai
import os
os.environ["GREENLENS_DATASET_ZIP"] = "/kaggle/input/greenlens-merged-2class/merged_dataset.zip"
os.environ["GREENLENS_EPOCHS"] = "150"
os.environ["GREENLENS_IMGSZ"] = "1280"
os.environ["GREENLENS_BATCH"] = "16"  # OOM → "8"
!python ml/training/kaggle/train_greenlens_e1.py
```

**Cách B — Không clone, train inline:**

```python
!pip install -q ultralytics

import zipfile, shutil
from pathlib import Path
from ultralytics import YOLO

ZIP = "/kaggle/input/greenlens-merged-2class/merged_dataset.zip"
ROOT = Path("/kaggle/working/dataset")
ROOT.mkdir(exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    z.extractall(ROOT)

data_yaml = ROOT / "data.yaml"
if not data_yaml.exists():
    data_yaml.write_text(f"""path: {ROOT}
train: images/train
val: images/val
test: images/test
nc: 2
names:
  0: TRASH
  1: WATER
""")

model = YOLO("yolov8n.pt")
model.train(
    data=str(data_yaml), epochs=150, imgsz=1280, batch=16,
    workers=2, project="/kaggle/working/runs", name="greenlens_e1",
    seed=42, patience=30, amp=True,
)

# Eval test (số cho paper)
model = YOLO("/kaggle/working/runs/greenlens_e1/weights/best.pt")
model.val(data=str(data_yaml), split="test", imgsz=1280)
```

---

## Bước 4 — Download kết quả về máy / Drive

Trong **Output** (bên phải notebook) tải:

| File | Dùng để |
|------|---------|
| `greenlens_e1_output/best.pt` | Deploy `.env` MODEL_PATH |
| `results.csv` | Biểu đồ learning curve paper |
| `args.yaml` | Verify config trong §5.1 |

Hoặc zip:

```python
!cd /kaggle/working && zip -r greenlens_e1_bundle.zip greenlens_e1_output runs/greenlens_e1
```

→ Download `greenlens_e1_bundle.zip`

---

## Bước 5 — Dùng lại trên máy (khi có máy khác)

```powershell
Copy-Item "best.pt" "D:\CapsoneProject\Detection-AI\greenlens-detection-ai\ml\weights\best.pt" -Force
```

`.env`:

```env
MODEL_PATH=ml/weights/best.pt
MODEL_VERSION=v4.0.0-2class-150ep-1280px-kaggle
CLASSIFY_DEMO_MODE=false
```

---

## E0 baseline (COCO, không fine-tune) — chạy trên Kaggle

```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
model.val(data="/kaggle/working/dataset/data.yaml", split="test", imgsz=1280)
```

Ghi mAP → dòng **E0** trong bảng paper.

---

## Xử lý lỗi thường gặp

| Lỗi | Cách sửa |
|-----|----------|
| CUDA OOM | `batch=8` hoặc `imgsz=960` |
| Session 9h timeout | Save checkpoint; `model.train(..., resume=True)` |
| 0 train images | Zip sai cấu trúc — mở zip kiểm tra `images/train/` |
| mAP = 0 | Class id sai — phải 0=TRASH, 1=WATER |

---

## Batch gợi ý theo GPU Kaggle

| GPU | imgsz=1280 | batch |
|-----|------------|-------|
| T4 16GB | 1280 | 8–16 |
| P100 16GB | 1280 | 16 |
| OOM | 960 | 8 |

---

## Sau E1 (Hướng A)

1. Lưu số **test mAP** → bảng paper E1
2. Scene classifier: notebook tương tự với folder `scene/` (WATER/NEGATIVE)
3. Subtype: tab Dashboard hoặc notebook ImageFolder

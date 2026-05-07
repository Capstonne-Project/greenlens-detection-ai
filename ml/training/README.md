# Huấn luyện YOLO — phân loại ô nhiễm (cho `best.pt`)

Service Python đọc nhãn **`TRASH`, `WATER`, `SMOKE`, `CHEMICAL`** (đúng thứ tự `0…3` trong file `pollution_data.yaml`).
Sau khi train xong, copy **`best.pt`** vào `ml/weights/` và trỏ `MODEL_PATH` trong `.env`.

---

## Bước 1 — Chuẩn bị dataset (YOLO detection)

Trong repo, dùng cấu trúc sau (đã khai báo trong `configs/pollution_data.yaml`):

```text
ml/training/data/pollution/
  images/train/
  images/val/
  labels/train/
  labels/val/
```

Quy tắc:

- Mỗi ảnh có **một** file nhãn cùng **tên gốc** (ví dụ `IMG_001.jpg` ↔ `IMG_001.txt`).
- File `.txt`: mỗi dòng một vùng: `class xc yc w h` (tất cả số **0–1**, tâm và kích thước bbox so với ảnh — **định dạng YOLO**).

`class`:

| Id | Nhãn (phải trùng với API) |
|----|---------------------------|
| 0 | TRASH |
| 1 | WATER |
| 2 | SMOKE |
| 3 | CHEMICAL |

Công cụ gán nhãn gợi ý: [CVAT](https://cvat.org/), Roboflow, Label Studio → export **YOLO format**.

Nguyên tắc đồ án: chia **train/val** (ví dụ 80%/20%); đừng trộn cùng ảnh vào hai tập.

**Dataset “thật”, đủ combo 4 lớp, checklist nguồn + QC:** xem **[`DATASET_GUIDE_VI.md`](DATASET_GUIDE_VI.md)**.
**Kiểm tra cấu trúc trước khi train:** `uv run python ml/training/scripts/verify_yolo_dataset.py`
**Export COCO → YOLO:** `uv run python ml/training/scripts/coco_instances_to_yolo.py` (kèm `--map-json`). Sửa file map: mỗi key là **category_id** trong COCO, value là **0–3** (TRASH/WATER/SMOKE/CHEMICAL). Mẫu: `configs/coco_category_map.example.json`.

---

## Bước 2 — Có baseline `yolov8n.pt`

Tải một lần (nếu chưa có):

```powershell
cd D:\CapsoneProject\Detection-AI\greenlens-detection-ai
uv run python scripts\download_baseline_weights.py
```

---

## Bước 3 — Chạy huấn luyện

Từ thư mục gốc repo:

```powershell
uv run python ml\training\train_yolo.py --epochs 50 --batch 16
```

Tham số thường chỉnh: `--epochs`, `--imgsz`, `--batch` (giảm `batch` nếu máy báo thiếu RAM/VRAM).

Kết quả mặc định:

```text
ml/training/runs/pollution_detect/weights/best.pt
```

(Thư mục `runs` đã được `.gitignore` — không đẩy lên Git.)

---

## Bước 4 — Gắn vào AI Service

1. Copy (hoặc đổi tên):

   ```powershell
   copy ml\training\runs\pollution_detect\weights\best.pt ml\weights\best.pt
   ```

2. Trong `.env`:

   ```env
   MODEL_PATH=ml/weights/best.pt
   MODEL_VERSION=v1.0.0-my-team-best
   CLASSIFY_DEMO_MODE=false
   ```

3. Khởi động lại:

   ```powershell
   uv run uvicorn app.main:app --host 0.0.0.0 --reload --port 8000
   ```

4. Kiểm tra: `/api/v1/ready` có `model_loaded: true`; demo `/demo/demo_capture_classify.html` hoặc `/docs` gọi `classify-upload` với ảnh từ tập **val**.

---

## Lưu ý

- **GPU:** có CUDA → Ultralytics thường dùng GPU tự động; chỉ CPU thì train lâu, có thể giảm `--epochs`, `imgsz`, dataset nhỏ cho POC.
- **Chất lượng:** Plan dự án gợi ý cỡ trăm–nghìn ảnh/class cho production; đồ án có thể nêu rõ chỉ POC với ít ảnh và hạn chế.
- **“Tiếng ồn”:** không train từ ảnh theo BR — người dùng nhập tay; flag `noise_supported` trong API là `false`.

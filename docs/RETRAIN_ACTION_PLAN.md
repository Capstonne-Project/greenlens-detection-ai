# 🔁 Kế hoạch Train Lại Model — GreenLens Detection AI

> **Trạng thái hiện tại:** Model `v2.0.0-3class-100ep` đang dùng weights train từ điểm xuất phát sai (nhiễm từ lần train per-class cũ). Cần train lại từ đầu đúng cách.
>
> **Mục tiêu:** Model detect tốt ảnh chụp điện thoại thực tế — góc gần, bãi rác lớn, ánh sáng đa dạng.

---

## 🔍 Chẩn đoán — Tại sao model hiện tại kém

| # | Vấn đề | Biểu hiện | Mức độ |
|---|--------|-----------|--------|
| 1 | **Train từ weights nhiễm** | `args.yaml` cho thấy `model: job_36d3331b55/best.pt` — đây là output của lần train per-class bị catastrophic forgetting, không phải pretrained gốc | 🔴 Nghiêm trọng |
| 2 | **Val loss plateau từ epoch 20** | Val cls_loss: `3.15 → 2.01 → 1.63` — chỉ giảm 0.38 trong 80 epoch cuối → model không generalize được | 🔴 Nghiêm trọng |
| 3 | **imgsz=640 với ảnh điện thoại** | Ảnh điện thoại ~3000×4000px resize về 640px → mất detail, bãi rác lớn không detect được | 🟡 Quan trọng |
| 4 | **False positive WATER** | Model confuse "nền tối/đất ẩm" với nước — dataset WATER thiếu hard negative | 🟡 Quan trọng |
| 5 | **Dataset WATER yếu** | mAP50=0.277, chỉ ~262 ảnh, phân phối không đủ đa dạng | 🟡 Quan trọng |

---

## 📋 TODO — Làm theo thứ tự

### PHASE 1 — Chuẩn bị Dataset (làm trước khi train)

- [ ] **1.1** Kiểm tra lại dataset hiện có tại `D:\CapsoneProject\DATASETFINAL\`
  - Đếm số ảnh: TRASH / WATER / SMOKE (train + val riêng)
  - Mục tiêu tối thiểu: **TRASH ≥ 600, WATER ≥ 400, SMOKE ≥ 400**

- [ ] **1.2** Bổ sung ảnh WATER chất lượng cao (~200 ảnh)
  - ✅ Phải thể hiện rõ **mặt nước**: kênh/ao/sông ô nhiễm, nước thải, bề mặt có sóng hoặc phản chiếu
  - ❌ Tránh: ảnh chỉ là "vùng tối không rõ", nền đất ẩm, bóng cây
  - Nguồn gợi ý: [Roboflow Universe - water pollution](https://universe.roboflow.com/), Google Images

- [ ] **1.3** Thêm **Hard Negative cho WATER** (~100 ảnh, label rỗng)
  - Đường nhựa ướt sau mưa
  - Nền đất tối/ẩm
  - Bóng cây đổ xuống đất
  - Bì nilon/rác đen tối màu
  - → Tạo file `.txt` **rỗng** cho mỗi ảnh này (không có object nào)

- [ ] **1.4** Bổ sung ảnh TRASH góc gần/điện thoại (~150 ảnh)
  - Bãi rác ven đường chiếm >50% diện tích ảnh
  - Góc chụp ngang mặt đất hoặc từ tầm người đứng
  - Rác nhiều túi xanh/đen chồng chất
  - Ảnh chụp bằng điện thoại Android/iOS thực tế (không phải stock photo)

- [ ] **1.5** Verify dataset format bằng script
  ```powershell
  uv run python ml/training/scripts/verify_yolo_dataset.py `
    --dataset-dir D:\CapsoneProject\DATASETFINAL\merged_final `
    --nc 3
  ```

---

### PHASE 2 — Cấu hình Train đúng

- [ ] **2.1** Mở Training Dashboard: `http://localhost:8000/static/demo/demo_training_dashboard.html`

- [ ] **2.2** Upload dataset đã chuẩn bị qua tab **"Gộp Dataset"** hoặc **"Upload YOLO"**

- [ ] **2.3** Cấu hình job train với thông số sau:

  | Tham số | Giá trị | Lý do |
  |---------|---------|-------|
  | **Model gốc** | `yolov8n.pt` (baseline, KHÔNG chọn continue from previous) | Train từ pretrained sạch của Ultralytics |
  | **Image Size** | `1280` | Ảnh điện thoại high-res, detect object lớn |
  | **Epochs** | `150` | Đủ để converge với dataset ~1.5k ảnh + imgsz lớn |
  | **Batch** | `8` | imgsz=1280 cần VRAM nhiều hơn; RTX 3050 4GB nên dùng 8 |
  | **Continue from job** | ❌ **TẮT** | Không dùng weights cũ |

  > ⚠️ **Quan trọng:** Nếu batch=8 bị OOM (out of memory), giảm xuống batch=4

- [ ] **2.4** Xác nhận trong log đầu tiên của job:
  ```
  Model: yolov8n.pt (không phải đường dẫn đến job cũ)
  imgsz: 1280
  ```

---

### PHASE 3 — Monitor Training

- [ ] **3.1** Theo dõi metrics ở epoch 20-30 (checkpoint đầu tiên quan trọng):
  - `mAP50 > 0.35` → đang học được, tiếp tục
  - `mAP50 < 0.20` ở epoch 30 → dataset có vấn đề, dừng và check

- [ ] **3.2** Metrics kỳ vọng sau 150 epochs:

  | Class | mAP50 mục tiêu | Hiện tại |
  |-------|---------------|----------|
  | TRASH | ≥ 0.80 | 0.754 |
  | WATER | ≥ 0.55 | 0.277 ⚠️ |
  | SMOKE | ≥ 0.80 | 0.813 |
  | **Overall** | **≥ 0.72** | 0.614 |

- [ ] **3.3** Nếu WATER vẫn < 0.50 sau 150 epochs → cần thêm data WATER và train thêm 50 epochs với `--resume`

---

### PHASE 4 — Deploy weights mới

- [ ] **4.1** Copy `best.pt` từ output job:
  ```powershell
  Copy-Item "ml\training\runs\web_jobs\<job_id>\output\pollution_detect\weights\best.pt" `
            "ml\weights\best.pt" -Force
  ```

- [ ] **4.2** Cập nhật `.env`:
  ```env
  MODEL_PATH=ml/weights/best.pt
  MODEL_VERSION=v3.0.0-3class-150ep-1280px
  ```

- [ ] **4.3** Restart server:
  ```powershell
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

- [ ] **4.4** Test với ảnh thực tế:
  - ✅ Bãi rác ven đường góc gần (như ảnh đã test hôm nay)
  - ✅ Ảnh có biển báo + rác (test false positive)
  - ✅ Ảnh kênh nước ô nhiễm rõ ràng
  - ✅ Ảnh khói/đốt rác

---

## 🛠️ Fix đã áp dụng hôm nay (không cần làm lại)

- [x] `imgsz=1280` trong `app/core/pollution_classifier.py` (predict call)
- [x] `MODEL_VERSION=v2.0.0-3class-100ep` trong `.env`
- [x] `best.pt` đã copy vào `ml/weights/best.pt`
- [x] Loại bỏ CHEMICAL class hoàn toàn (nc=3)
- [x] OBB → AABB auto-convert trong merge tool

---

## 📌 Ghi chú kỹ thuật quan trọng

### Tại sao phải train ALL class cùng lúc?
YOLO học **decision boundary giữa các class** trong mỗi gradient update. Train từng class riêng → catastrophic forgetting → class sau xóa kiến thức của class trước.

### Tại sao imgsz=1280 thay vì 640?
- Ảnh điện thoại: 3000–4000px
- Resize 640px: mất ~75% resolution → object nhỏ/xa biến mất
- 1280px: giữ được detail, YOLO vẫn xử lý được trong ~150ms trên RTX 3050

### Val loss plateau — nguyên nhân
Val set cần **cùng distribution với ảnh thực tế** (điện thoại, góc gần, ngoài trời). Nếu val set toàn ảnh stock/lab → val loss không phản ánh thực tế, model overfit train set.

### WATER false positive — cách tránh
Hard negative (label rỗng) là cách YOLO học "đây là background". Ảnh đất ẩm/tối → label rỗng → model học không detect WATER ở đó.

---

## 🔗 Files liên quan

| File | Vai trò |
|------|---------|
| [app/core/pollution_classifier.py](../app/core/pollution_classifier.py) | `imgsz=1280` đã fix, inference logic |
| [app/core/training_jobs.py](../app/core/training_jobs.py) | Job orchestration, `_resolve_model_path()` |
| [ml/training/configs/pollution_data.yaml](../ml/training/configs/pollution_data.yaml) | YOLO dataset config (nc=3) |
| [ml/training/train_yolo.py](../ml/training/train_yolo.py) | Train script |
| [.env](../.env) | `MODEL_PATH`, `MODEL_VERSION` |
| [static/demo/demo_training_dashboard.html](../static/demo/demo_training_dashboard.html) | Web UI để upload + train |

---

*Tạo ngày 2026-05-24 — sau training run `job_cc0a413f77` (100ep, mAP50=0.614)*

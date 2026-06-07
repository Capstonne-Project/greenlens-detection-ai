# GreenLens — Playbook đầy đủ cho bài báo (Hướng A)

> **Mục tiêu:** Viết và submit bài báo *Deployable Hybrid Pipeline for Trash & Water Pollution Reporting with Fine-Grained Waste Classification in Vietnamese Urban Contexts*.
>
> **Khớp codebase:** 2 lớp detection `TRASH` / `WATER` · Scene `WATER` / `NEGATIVE` · Subtype 7 lớp · FastAPI pipeline.
>
> **Cập nhật:** 2026-06-07
> **Train trước — viết docs sau.** Cập nhật cột **Trạng thái** và § [Kết quả thực tế](#kết-quả-thực-tế--cập-nhật-sau-mỗi-bước) sau mỗi bước xong.

---

## 0. Trạng thái tiến độ train (tự cập nhật)

| Bước | Việc | Trạng thái | Ngày | Output / ghi chú |
|------|------|------------|------|------------------|
| **0** | Dataset gộp + test khóa | ✅ Xong | | `merged_dataset.zip` |
| **E0** | Eval COCO không fine-tune | ⬜ Chưa | | `paper_output/E0/` |
| **E1** | Train + eval YOLOv8n | ⬜ Chưa | | `paper_output/E1/best.pt` |
| **E1b** | (Tuỳ chọn) Train YOLOv8s | ⬜ Bỏ qua | | So model lớn hơn |
| **E2** | Train scene + đo FP WATER | ⬜ Chưa | | `scene_classifier.pt` |
| **E3** | Train subtype + F1 | ⬜ Chưa | | `trash_subtype_classifier.pt` |
| **Hình** | Learning curve + predict | ⬜ Chưa | | `results.csv`, `fig*.png` |
| **Docs** | Viết paper §1–§7 | ⬜ Để sau | | Sau khi Bảng IV đủ số |

**Legend:** ⬜ Chưa · 🔄 Đang chạy · ✅ Xong · ⏭ Bỏ qua

---

## 0.3 Model nào là **GreenLens (của bạn)**? — đọc trước khi nhìn bảng

Bảng so sánh có nhiều dòng **E0, E1, E2…** — không phải dòng nào cũng là “model đề xuất”. Quy ước paper:

| Mã | Tên trên bảng | Có phải **GreenLens (Ours)**? | Giải thích ngắn |
|----|---------------|-------------------------------|-----------------|
| **E0** | YOLOv8n-COCO | ❌ Baseline đối chứng | Pretrained gốc Ultralytics, **chưa** train data bạn |
| **E1** | FT-YOLOv8n | ⚠️ **Một phần** của GreenLens | YOLO fine-tune **dataset của bạn** — là **detector trong GreenLens**, nhưng **chưa** có scene/subtype/fusion → dùng để so “detector thuần” |
| **E1b** | FT-YOLOv8s | ❌ Baseline tuỳ chọn | Model lớn hơn, cùng data — so accuracy vs tốc độ |
| **E2** | GreenLens-Det | ✅ **Ours (giai đoạn 1)** | E1 + scene fusion + safeguard — **pipeline lai detection** |
| **E3** | **GreenLens-Full** | ✅ **Ours (đề xuất chính)** | E2 + subtype 7 lớp + severity + API — **toàn bộ hệ thống paper** |

### Một câu nhớ

> **Model của bạn trong bài báo = dòng `E3 GreenLens-Full`.**
> **E1** = weight YOLO bạn train (`best.pt`) — thành phần bên trong E3, **không** gọi là “Ours full” trong abstract.

### Bảng IV ghi số thế nào?

| Dòng | mAP (Bảng IV) | Metric khác |
|------|---------------|-------------|
| E0, E1, E1b | `yolo val split=test` | — |
| E2 | **Cùng mAP E1** (cùng `best.pt`) | **Bảng V** — FP WATER, recall |
| **E3** | **Cùng mAP E1** | **Bảng V** + **Bảng VI** subtype F1 |

Trong abstract viết: *“GreenLens (E3) đạt mAP@0.5 = X, vượt baseline COCO (E0) và cải thiện ổn định WATER so với FT-YOLO-only (E1).”*

---

## 0.4 So sánh **GreenLens vs detector liên quan** — story “nổi trội” cho bài báo

Mục tiêu paper của bạn: **GreenLens (E3) tốt hơn các cách detect ô nhiễm phổ biến** — không chỉ “train xong có số”.

### Ai là “đối thủ” (related detectors)?

Chia **2 lớp** — reviewer chấp nhận cả hai:

#### A. Baseline **cùng test set** (bắt buộc — công bằng, bạn tự train trên Kaggle)

| Đối thủ | Thuộc loại detect nào | Vai trò trong paper |
|---------|----------------------|---------------------|
| **E0** YOLOv8n-COCO | Generic object detector, không domain | “Dùng pretrained chung **không đủ** cho rác/nước VN” |
| **E1** FT-YOLOv8n | Single-stage detector (SOTA phổ biến) | “Detector fine-tune **mạnh** nhưng **thiếu** fusion + subtype” |
| **E1b** FT-YOLOv8s | Detector lớn hơn, nặng hơn | “GreenLens nhẹ hơn / cân bằng hơn với accuracy tương đương” |
| **E2** GreenLens-Det | Hybrid detect + scene | Ablation: fusion **có ích** |
| **E3 ★ GreenLens-Full** | **Của bạn** | **Đề xuất** — beat E0, E1 trên metric end-to-end |

#### B. Công trình **liên quan** (Related work — trích số từ paper khác, cẩn thận)

| Công trình | Loại | So với GreenLens |
|------------|------|------------------|
| TACO [9] | Trash detect | Khác task/benchmark — **cite**, không claim beat trực tiếp trừ khi eval cùng test |
| TrashNet [16] | Classify waste | GreenLens **tích hợp** detect + subtype end-to-end |
| YOLO litter (Roboflow) | Single-class trash | GreenLens **2 lớp** TRASH+WATER + subtype |
| Scene water CNN [18] | Scene-only WATER | GreenLens **fusion safeguard** — ít FP hơn scene-alone |

**Quy tắc vàng:** Số **“nổi trội” chính thức** lấy từ **cùng test set của bạn** (nhóm A). Nhóm B dùng **bàn luận** §2 Related work, không ép số khác dataset vào Bảng IV.

---

### Câu chuyện “nổi trội” — 3 claim cần chứng minh

| # | Claim trong paper | So sánh | Metric | GreenLens thắng khi |
|---|-------------------|---------|--------|---------------------|
| **1** | Fine-tune domain-specific **vượt** generic detect | **E3/E1 vs E0** | ALL mAP@0.5 test | E1 mAP >> E0 |
| **2** | Pipeline lai **vượt** detector thuần | **E3 vs E1** | WATER FP ↓, recall WATER ↑, có subtype | E3 ít báo nhầm nước; có 7 loại rác |
| **3** | **Cân bằng** accuracy–deploy | **E3 vs E1b** | mAP gần bằng, latency ↓, size ↓ | E3 mAP ≈ E1b nhưng nhanh/nhẹ hơn + subtype |

**Abstract mẫu (khi có số):**

> *So với YOLOv8n pretrained (E0), GreenLens đạt mAP@0.5 cao hơn **+X%**. So với fine-tuned YOLO-only (E1), pipeline đề xuất giảm **Y%** false positive WATER và cung cấp phân loại **7 loại rác** (macro-F1 = Z) mà detector đơn không có.*

---

### Bảng so sánh detector liên quan (§5.3 — dùng trong bài báo)

**Bảng IV-A — Cùng test set (số do bạn chạy)**

| Detector / Hệ thống | Loại | Fine-tune data bạn | ALL mAP@0.5 | WATER mAP@0.5 | FP WATER ↓ | Subtype | ms/img | **Ours?** |
|---------------------|------|--------------------|-------------|---------------|------------|---------|--------|-----------|
| YOLOv8n-COCO | Single-stage | ❌ | TBD | TBD | — | ❌ | TBD | |
| YOLOv8n-FT | Single-stage | ✅ | TBD | TBD | TBD | ❌ | TBD | |
| YOLOv8s-FT | Single-stage (lớn) | ✅ | TBD | TBD | TBD | ❌ | TBD | |
| GreenLens-Det (E2) | Hybrid YOLO+scene | ✅ | = FT | Bảng V | TBD | ❌ | TBD | ✅ |
| **GreenLens-Full (E3)** | **Hybrid + subtype** | ✅ | = FT | **TBD** | **TBD** | **✅ F1=TBD** | TBD | **★ Ours** |

**Bảng IV-B — Related work (trích literature — không bắt buộc đủ số)**

| Công trình | Method | Dataset / bối cảnh | Metric họ báo | GreenLens khác gì |
|------------|--------|---------------------|---------------|-------------------|
| TACO | Instance seg / detect | Global street | mAP TBD | + WATER + VN + subtype |
| TrashNet | Classify | 6 class recycle | Accuracy TBD | Detect-then-classify trong 1 API |
| … | … | … | … | … |

---

### Bạn cần train / chạy gì trên Kaggle (tối thiểu để claim “nổi trội”)

```
1. E0  — val COCO          → beat claim 1 (phần đầu)
2. E1  — train YOLOv8n     → baseline detect mạnh nhất “đơn giản”
3. E3  — gắn scene+subtype → model của bạn
4. (Khuyên) E1b YOLOv8s    → claim 3 cân bằng speed
5. Đo FP WATER E1 vs E3   → claim 2 (quan trọng cho WATER)
```

Script hiện tại: `--mode all` → E0+E1. Thêm `--mode e1b` nếu muốn hàng YOLOv8s.

---

### Viết §5.3 / §6 sao cho reviewer thấy “nổi trội”

1. **Bảng IV-A** — số test, highlight dòng **GreenLens-Full** in đậm.
2. **Một câu** ngay dưới bảng: *“GreenLens vượt mọi baseline single-stage trên cùng test set về mAP tổng và ổn định WATER.”*
3. **Hình 4–5** — cùng ảnh: E1 miss / false WATER vs E3 đúng.
4. **Đừng** claim “SOTA toàn cầu” — claim **“superior on our Vietnamese citizen-report benchmark”**.

---

## 0.1 Train ngay — làm theo thứ tự (Kaggle)

> **1 notebook Kaggle** chạy lần lượt. Script: `ml/training/kaggle/run_paper_experiments.py`

### Chuẩn bị (1 lần)

1. [kaggle.com](https://www.kaggle.com) → **Datasets** → upload `merged_dataset.zip` → tên VD: `greenlens-merged-2class`
2. **New Notebook** → GPU **T4 x2** → **Internet ON**
3. **Add Data** → chọn dataset vừa upload

### Cell 1 — GPU + clone repo (hoặc upload script)

```python
!nvidia-smi
!pip install -q ultralytics
```

**Cách A — Clone repo (nếu đã push GitHub):**

```python
!git clone https://github.com/YOUR_USER/greenlens-detection-ai.git
%cd greenlens-detection-ai
```

**Cách B — Không clone:** upload file `run_paper_experiments.py` vào Kaggle (Add Data) rồi `%cd` tới folder đó.

### Cell 2 — Sửa đường dẫn dataset

```python
import os
# ← SỬA đúng path Kaggle Input của bạn (Settings → copy path)
os.environ["GREENLENS_DATASET_ZIP"] = "/kaggle/input/greenlens-merged-2class/merged_dataset.zip"
os.environ["GREENLENS_EPOCHS"] = "150"
os.environ["GREENLENS_IMGSZ"] = "1280"
os.environ["GREENLENS_BATCH"] = "8"   # OOM → "4"
```

### Cell 3 — Chạy E0 + E1 (bắt buộc, ~vài giờ)

```python
DATASET_ZIP = "/kaggle/input/greenlens-merged-2class/merged_dataset.zip"  # ← SỬA

!python ml/training/kaggle/run_paper_experiments.py --mode all \
  --dataset-zip "{DATASET_ZIP}" \
  --epochs 150 --imgsz 1280 --batch 8
```

**Output:**

```text
/kaggle/working/paper_output/
  paper_metrics.json    ← số đầy đủ
  BANG_IV.md            ← copy vào playbook § Kết quả thực tế
  E1/best.pt
  E1/results.csv
  E1/args.yaml
  runs/E1_yolov8n/
```

### Cell 4 — (Tuỳ chọn) E1b YOLOv8s — so model lớn hơn

```python
!python ml/training/kaggle/run_paper_experiments.py --mode e1b \
  --dataset-zip "{DATASET_ZIP}" \
  --epochs 150 --imgsz 1280 --batch 4
```

→ Thêm 1 dòng vào Bảng IV: *E1b FT-YOLOv8s*.

### Cell 5 — Download về Drive

```python
!cd /kaggle/working && zip -r paper_output_bundle.zip paper_output/
# Download paper_output_bundle.zip từ Output panel
```

### Cell 6 — Cập nhật playbook

1. Mở `BANG_IV.md` trong bundle
2. Dán vào [§ Kết quả thực tế](#kết-quả-thực-tế--cập-nhật-sau-mỗi-bước)
3. Đổi ⬜ → ✅ ở bảng **§0 Trạng thái** cho E0, E1

---

## 0.2 E2 & E3 — không train YOLO lại

| Exp | Là gì | Cần gì |
|-----|--------|--------|
| **E2** | Cùng `E1/best.pt` + **scene classifier** | Train scene trên Kaggle/local (§3.4) → đo FP WATER |
| **E3** | Cùng E2 + **subtype** | Train subtype ImageFolder → macro-F1 |

Detection metrics (mAP) **dùng chung E1** — E2/E3 bổ sung Bảng V và VI, không train detector mới.

---

## Kết quả thực tế — cập nhật sau mỗi bước

> **Dán output từ `paper_output/BANG_IV.md` vào đây sau Kaggle.** Giữ template §6 bên dưới làm bản nháp.

### Bảng IV — KẾT QUẢ THỰC TẾ (auto-generated)

| Vai trò | Method | Fine-tune | TRASH mAP50 | WATER mAP50 | ALL mAP50 | TRASH P | WATER P |
|---------|--------|-----------|-------------|-------------|-----------|---------|---------|
| Baseline | E0 YOLOv8n-COCO | Không | _chưa chạy_ | _chưa chạy_ | _chưa chạy_ | — | — |
| Baseline FT | E1 FT-YOLOv8n _(detector GreenLens)_ | Có | _chưa chạy_ | _chưa chạy_ | _chưa chạy_ | — | — |
| Baseline (opt) | E1b FT-YOLOv8s | Có | _tuỳ chọn_ | _tuỳ chọn_ | _tuỳ chọn_ | — | — |
| **Ours** | **E2 GreenLens-Det** | Có | _= E1_ | _Bảng V_ | _= E1_ | — | — |
| **Ours ★** | **E3 GreenLens-Full** | Có | _= E1_ | _Bảng V_ | _= E1_ | — | — |

**★ E3 = model đề xuất chính (toàn pipeline).** Kaggle script hiện auto-fill **E0 + E1**; E2/E3 điền sau khi train scene/subtype.

**ΔmAP E1 vs E0:** _TBD%_ (điền sau khi có số)

---

## Mục lục

0. [Trạng thái & train ngay (Kaggle)](#0-trạng-thái-tiến-độ-train-tự-cập-nhật)
1. [Tóm tắt hướng A & câu chuyện paper](#1-tóm-tắt-hướng-a--câu-chuyện-paper)
2. [Checklist trước khi viết](#2-checklist-trước-khi-viết)
3. [Thí nghiệm bắt buộc (E0–E3)](#3-thí-nghiệm-bắt-buộc-e0e3)
4. [Train trên Kaggle (E1)](#4-train-trên-kaggle-e1)
5. [Cấu trúc bài báo (outline đầy đủ)](#5-cấu-trúc-bài-báo-outline-đầy-đủ)
6. [Các bảng so sánh — template điền số](#6-các-bảng-so-sánh--template-điền-số)
7. [Hình ảnh kết quả — lấy ở đâu, chèn thế nào](#7-hình-ảnh-kết-quả--lấy-ở-đâu-chèn-thế-nào)
8. [Abstract & Keywords mẫu](#8-abstract--keywords-mẫu)
9. [Lộ trình 4 tuần](#9-lộ-trình-4-tuần)
10. [Lỗi reviewer hay bắt](#10-lỗi-reviewer-hay-bắt)
11. [File tham chiếu trong repo](#11-file-tham-chiếu-trong-repo)

---

## 1. Tóm tắt hướng A & câu chuyện paper

### 1.1 Claim chính (3 ý — không đổi giữa chừng)

| # | Đóng góp | Nội dung |
|---|----------|----------|
| C1 | **Dataset + fine-tune detector** | Bộ TRASH/WATER (Roboflow + ảnh VN), YOLOv8n fine-tune, test set khóa |
| C2 | **Pipeline lai (method)** | Fine-tuned YOLO + EfficientNet scene (WATER) + **safeguard fusion** |
| C3 | **Detect-then-classify** | Crop TRASH → EfficientNet 7 subtype + severity + HITL API |

### 1.2 Pipeline (Hình 1 — architecture)

```text
Input RGB
    │
    ├─► [Parallel] YOLOv8n (fine-tuned) ──► TRASH / WATER + bbox
    │         │
    │         └─► if TRASH bbox ──► Crop (+4px) ──► EfficientNet subtype (7 lớp)
    │
    └─► [Parallel] EfficientNet scene ──► P(WATER) vs NEGATIVE
              │
              ▼
         Fusion + Safeguard
         (scene chỉ bổ sung WATER khi YOLO đã thấy ≥1 object)
              │
              ▼
         Severity (coverage ratio) + HITL (AUTO_FILL / SUGGEST / KEEP_USER_CHOICE)
              │
              ▼
         JSON API Response
```

**Code:** `app/core/pollution_classifier.py`, `scene_classifier.py`, `trash_subtype_classifier.py`

### 1.3 Baseline vs GreenLens (Ours)

| ID | Tên trên bảng | Vai trò | Mô tả |
|----|---------------|---------|-------|
| **E0** | YOLOv8n-COCO | Baseline | Pretrained COCO, không fine-tune |
| **E1** | FT-YOLOv8n | Baseline FT / **thành phần GreenLens** | Fine-tuned YOLO — `best.pt` — tắt scene & subtype |
| **E1b** | FT-YOLOv8s | Baseline (tuỳ chọn) | Backbone lớn hơn, cùng data |
| **E2** | **GreenLens-Det** | **Ours** | E1 + scene fusion + safeguard |
| **E3** | **GreenLens-Full** | **Ours ★ (đề xuất chính)** | E2 + trash subtype + severity + API |

**Thứ tự train trên Kaggle:** `E0` (5 phút) → `E1` (vài giờ) → tuỳ chọn `E1b` → sau đó `E2`/`E3` module riêng.

**Cùng dataset, cùng test set, cùng config train (epochs, imgsz, seed) cho E1 và E1b.**

---

## 2. Checklist trước khi viết

### Dataset

- [X] `merged_dataset.zip` có `images/train|val|test` + `labels/...`
- [X] `nc: 2` — `0: TRASH`, `1: WATER` (không SMOKE)
- [X] Split **70/15/15**, **test khóa** — không dùng test để tune
- [X] Ghi nguồn: Roboflow project link + license + số ảnh VN tự chụp

### Artifact sau train (lưu Google Drive ngay)

- [ ] `best.pt`
- [ ] `results.csv`
- [ ] `args.yaml`
- [ ] Screenshot / log `yolo val split=test`

### Excel tracking (tạo `paper_metrics.xlsx`)

Sheet **Detection**, **Fusion**, **Subtype**, **Figures** — copy bảng §6 vào.

---

## 3. Thí nghiệm bắt buộc (E0–E3)

### 3.1 Config train thống nhất (ghi vào §5.1)

| Tham số | Giá trị |
|---------|---------|
| Backbone | YOLOv8n |
| Init weights | `yolov8n.pt` (COCO pretrained) |
| Epochs | 150 |
| Image size | 1280 |
| Batch | 8–16 (Kaggle T4: 8 an toàn) |
| Optimizer | AdamW (Ultralytics default) |
| Seed | 42 |
| Patience | 30 |
| AMP | True |

### 3.2 E0 — COCO baseline (5 phút)

```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
model.val(data="path/to/data.yaml", split="test", imgsz=1280)
```

→ mAP thấp → justify fine-tuning.

### 3.3 E1 — Fine-tuned YOLO only (bắt buộc)

Train trên Kaggle (§4) hoặc Dashboard. Eval:

```python
model = YOLO("best.pt")
model.val(data="data.yaml", split="test", imgsz=1280)
```

`.env` khi demo (YOLO-only):

```env
MODEL_PATH=ml/weights/best.pt
SCENE_CLASSIFIER_PATH=
TRASH_SUBTYPE_MODEL_PATH=
CLASSIFY_DEMO_MODE=false
```

### 3.4 E2 — + Scene fusion

1. Chuẩn bị scene data:

```text
ml/training/data/scene/
  images/train/WATER/
  images/train/NEGATIVE/
  images/val/WATER/
  images/val/NEGATIVE/
```

- Ảnh có bbox WATER → `WATER/`
- Hard negative (đường ướt, đất tối, label rỗng) → `NEGATIVE/`

2. Train: Dashboard tab Scene hoặc `train_scene_classifier.py`

3. `.env`:

```env
SCENE_CLASSIFIER_PATH=ml/weights/scene_classifier.pt
SCENE_CLASSIFIER_THRESHOLD=0.45
```

4. So sánh E1 vs E2: **WATER false positive rate** trên folder hard negative (§6 Bảng V).

### 3.5 E3 — + Subtype

1. Gộp ZIP subtype (Dashboard tab Subtype)
2. Train → `trash_subtype_classifier.pt`
3. `.env`: `TRASH_SUBTYPE_MODEL_PATH=ml/weights/trash_subtype_classifier.pt`
4. Eval macro-F1 trên test subtype (§6 Bảng VI).

---

## 4. Train trên Kaggle — chi tiết

> **Quick start:** xem [§0.1 Train ngay](#01-train-ngay--làm-theo-thứ-tự-kaggle).

Chi tiết bổ sung: `ml/training/kaggle/KAGGLE_TRAIN_GUIDE_VI.md`

Script thí nghiệm paper: `ml/training/kaggle/run_paper_experiments.py`

| Mode | Lệnh | Thời gian ước tính |
|------|------|---------------------|
| `e0` | Chỉ eval COCO | ~5 phút |
| `e1` | Train v8n + eval test | 2–6 giờ |
| `e1b` | Train v8s + eval test | 3–8 giờ |
| `all` | e0 + e1 | 2–6 giờ |

### Tóm tắt nhanh (legacy single script)

1. Upload `merged_dataset.zip` → Kaggle Dataset
2. Notebook: GPU T4, Internet ON
3. Chạy `ml/training/kaggle/train_greenlens_e1.py` hoặc cell inline trong guide
4. Download: `best.pt`, `results.csv`, `args.yaml`
5. Chạy `model.val(..., split="test")` → ghi số Bảng IV

---

## 5. Cấu trúc bài báo (outline đầy đủ)

### Title (EN)

**GreenLens: A Deployable Hybrid Detection Pipeline for Trash and Water Pollution Reporting with Fine-Grained Waste Classification in Vietnamese Urban Contexts**

### Title (VI — nếu hội đồng VN)

**GreenLens: Pipeline phát hiện lai rác thải và ô nhiễm nước kèm phân loại chi tiết loại rác cho báo cáo cộng đồng tại đô thị Việt Nam**

---

### §1 Giới thiệu

- **1.1** Bối cảnh ô nhiễm VN, citizen reporting, thiếu pipeline end-to-end
- **1.2** Related approaches ngắn: trash detection, water scene, detect-then-classify
- **1.3** Research gaps (rút gọn **4 gap**, bỏ SMOKE):
  - Gap 1: Dataset VN + TRASH/WATER unified YOLO
  - Gap 2: Hybrid detection + safeguarded scene fusion
  - Gap 3: Fine-grained waste trong pipeline pollution (không chỉ TRASH chung)
  - Gap 4: Deployable API + HITL + severity
- **1.4** Contributions (4 bullet khớp C1–C3 + dataset)
- **1.5** Cấu trúc bài

---

### §2 Công trình liên quan

- 2.1 Object detection (YOLO, TACO, TrashNet)
- 2.2 Scene classification for water pollution
- 2.3 Detect-then-classify waste
- 2.4 AI môi trường / citizen science tại VN

---

### §3 Bộ dữ liệu

- **3.1** Nguồn: Roboflow (global) + ảnh VN (điện thoại, TP.HCM / …)
- **3.2** **Bảng I** — phân bố ảnh theo lớp và split
- **3.3** Quy trình gán nhãn bbox YOLO, QC chéo X%
- **3.4** Augmentation (Ultralytics default + ghi rõ Mosaic/MixUp)
- **3.5** Split 70/15/15, test khóa trước khi tune
- **3.6** Dataset subtype (ImageFolder 7 lớp) — **Bảng II**

**Chú ý paper:** Viết **2 lớp** TRASH/WATER, không 3 lớp SMOKE.

---

### §4 Phương pháp

- **4.1** Tổng quan pipeline → **Hình 1**
- **4.2** Fine-tuned YOLOv8n detector
- **4.3** Scene classifier EfficientNet-B0 (WATER / NEGATIVE)
- **4.4** Fusion + safeguard (3 quy tắc — bám `pollution_classifier._merge_yolo_and_scene`)
- **4.5** Severity từ coverage ratio
- **4.6** Trash subtype (crop + EfficientNet, τ_subtype = 0.40)
- **4.7** HITL mapping → **Bảng III**

---

### §5 Thực nghiệm

- **5.1** Hardware (Kaggle GPU), framework, hyperparameters từ `args.yaml`
- **5.2** Metrics: P, R, mAP@0.5, mAP@0.5:0.95, latency, model size
- **5.3** Detection results → **Bảng IV**, **Hình 2** (learning curve)
- **5.4** Ablation fusion → **Bảng V**
- **5.5** Subtype results → **Bảng VI**, **Hình 3** (confusion matrix)
- **5.6** Qualitative → **Hình 4–5**
- **5.7** Deployment: ms/ảnh, MB

---

### §6 Thảo luận

- WATER khó hơn TRASH — giải thích
- Giới hạn: quy mô test, class imbalance
- Threats to validity

---

### §7 Kết luận & hướng phát triển

---

## 6. Các bảng so sánh — template điền số

> Thay `TBD` bằng số thật từ `yolo val split=test`. Giữ 3 chữ số thập phân (VD: 0.737).

---

### Bảng I — Thống kê dataset (§3.2)

| Lớp | Nguồn Roboflow | Ảnh VN tự chụp | Tổng ảnh | Train | Val | Test | Tổng bbox |
|-----|----------------|----------------|----------|-------|-----|------|-----------|
| TRASH | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| WATER | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| **Total** | TBD | TBD | **TBD** | TBD | TBD | TBD | TBD |

**Ghi chú nguồn:**

| Nguồn | Link | License |
|-------|------|---------|
| Roboflow project 1 | TBD | TBD |
| Ảnh VN | Tự thu thập, TBD–TBD/2025 | Nội bộ / consent |

---

### Bảng II — Dataset subtype (§3.6)

| Lớp subtype | Train | Val | Test | Ghi chú |
|-------------|-------|-----|------|---------|
| RECYCLABLE | TBD | TBD | TBD | Chai, lon, carton |
| ORGANIC | TBD | TBD | TBD | Thức ăn thừa |
| MEDICAL | TBD | TBD | TBD | Khẩu trang, kim |
| ELECTRONIC | TBD | TBD | TBD | |
| CONSTRUCTION | TBD | TBD | TBD | |
| HAZARDOUS | TBD | TBD | TBD | Pin, hóa chất |
| HOUSEHOLD | TBD | TBD | TBD | Túi nilon, hỗn hợp |
| **Total** | TBD | TBD | TBD | |

---

### Bảng III — Confidence → HITL (§4.7)

| Chế độ API | Ngưỡng confidence | Hành vi UI |
|------------|-------------------|------------|
| AUTO_FILL | ≥ 0.80 | Tự điền nhãn |
| SUGGEST | 0.50 – 0.80 | Gợi ý, user xác nhận |
| KEEP_USER_CHOICE | < 0.50 | Giữ lựa chọn user |

---

### Bảng IV — So sánh detection trên TEST (§5.3) ⭐ BẢNG CHÍNH

| Vai trò | Method | Fine-tune | TRASH P | TRASH R | TRASH mAP@0.5 | TRASH mAP@0.5:0.95 | WATER P | WATER R | WATER mAP@0.5 | WATER mAP@0.5:0.95 | **ALL mAP@0.5** | Params (M) | Latency (ms) |
|---------|--------|-----------|---------|---------|---------------|---------------------|---------|---------|---------------|---------------------|-----------------|------------|--------------|
| Baseline | E0 YOLOv8n-COCO | Không | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | 3.2 | — |
| Baseline FT | E1 FT-YOLOv8n | Có | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | **TBD** | 3.2 | TBD |
| Baseline (opt) | E1b FT-YOLOv8s | Có | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | 11.2 | TBD |
| **Ours** | **E2 GreenLens-Det** | Có | TBD | TBD | = E1 | = E1 | TBD | TBD | xem Bảng V | xem Bảng V | = E1 | 3.2+scene | TBD |
| **Ours ★** | **E3 GreenLens-Full** | Có | TBD | TBD | = E1 | = E1 | TBD | TBD | xem Bảng V | xem Bảng V | = E1 | +subtype | TBD |

**★ E3 = model đề xuất của bạn (GreenLens).** E1 = `best.pt` bạn train — detector bên trong E3.

**Cách lấy số:** output terminal của `yolo val` hoặc file `runs/.../results.csv` dòng cuối (val) — **paper dùng test split**.

**Cải thiện E1 vs E0:**

```text
ΔmAP = (E1_ALL - E0_ALL) / E0_ALL × 100% = TBD%
```

---

### Bảng V — Ablation fusion / WATER stability (§5.4)

| Config | WATER FP trên N ảnh hard negative | WATER Recall trên N ảnh test WATER | Ghi chú |
|--------|-----------------------------------|-------------------------------------|---------|
| E1 YOLO-only | TBD / N | TBD | |
| E2 YOLO + scene + safeguard | TBD / N | TBD | FP giảm = fusion có ích |

**Hard negative set:** 30–50 ảnh đường ướt, đất tối, không có nước — label ground truth = không WATER.

**Đếm FP thủ công hoặc script:**

```python
# Gợi ý: loop ảnh trong folder, gọi API classify-upload, đếm primary_class == WATER
```

---

### Bảng VI — Subtype classification (§5.5)

| Lớp | Precision | Recall | F1 |
|-----|-----------|--------|-----|
| RECYCLABLE | TBD | TBD | TBD |
| ORGANIC | TBD | TBD | TBD |
| MEDICAL | TBD | TBD | TBD |
| ELECTRONIC | TBD | TBD | TBD |
| CONSTRUCTION | TBD | TBD | TBD |
| HAZARDOUS | TBD | TBD | TBD |
| HOUSEHOLD | TBD | TBD | TBD |
| **Macro avg** | TBD | TBD | **TBD** |

---

### Bảng VII — Thiết lập thực nghiệm (§5.1) — copy từ args.yaml

| Mục | Giá trị |
|-----|---------|
| GPU | TBD (VD: NVIDIA T4 16GB, Kaggle) |
| Framework | PyTorch X.X, Ultralytics YOLOv8 |
| Backbone | YOLOv8n |
| Epochs | 150 |
| Image size | 1280 |
| Batch | TBD |
| Seed | 42 |
| Train images | TBD |
| Val images | TBD |
| Test images | TBD |

---

## 7. Hình ảnh kết quả — lấy ở đâu, chèn thế nào

### Danh sách hình bắt buộc

| Hình | Nội dung | Nguồn | Cách tạo |
|------|----------|-------|----------|
| **Hình 1** | Kiến trúc pipeline GreenLens | Vẽ tay | draw.io / Excalidraw / PowerPoint — tông xám-xanh, không màu rực |
| **Hình 2** | Learning curve mAP50 theo epoch | `results.csv` | Python matplotlib (code bên dưới) |
| **Hình 3** | Confusion matrix subtype 7×7 | Sau train subtype | Ultralytics classify hoặc sklearn |
| **Hình 4** | Detection thành công (TRASH + bbox) | Inference | YOLO `predict` + save |
| **Hình 5** | Qualitative: success vs failure | Demo / API | Screenshot có bbox + label |
| **Hình 6** (optional) | PR curve | YOLO val | `yolo val ... plots=True` |

---

### Hình 1 — Pipeline (vẽ)

Block diagram §1.2 — export PNG 300 DPI, width ~12cm (IEEE single column ~8.5cm, double ~17cm).

---

### Hình 2 — Learning curve từ `results.csv`

File nằm tại: `runs/greenlens_e1/results.csv` (Kaggle) hoặc `ml/training/runs/web_jobs/.../results.csv`

**Chạy trên Kaggle hoặc local:**

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("/path/to/results.csv")
# Cột thường có: epoch, metrics/mAP50(B), metrics/mAP50-95(B),
#                 metrics/precision(B), metrics/recall(B)

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(df["epoch"], df["metrics/mAP50(B)"], label="mAP@0.5", linewidth=2)
ax.plot(df["epoch"], df["metrics/mAP50-95(B)"], label="mAP@0.5:0.95", linewidth=2)
ax.set_xlabel("Epoch")
ax.set_ylabel("mAP")
ax.set_title("GreenLens YOLOv8n — Training curves (validation)")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("fig2_learning_curve.png", dpi=300)
plt.show()
```

**Caption mẫu:** *Hình 2. Diễn biến mAP@0.5 và mAP@0.5:0.95 trên tập validation trong quá trình fine-tune YOLOv8n (150 epoch, imgsz=1280).*

---

### Hình 3 — Confusion matrix subtype

Sau khi có `trash_subtype_classifier.pt`, eval trên test folder:

```python
# Gợi ý dùng sklearn sau khi collect y_true, y_pred từ inference loop
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt

labels = ["RECYCLABLE","ORGANIC","MEDICAL","ELECTRONIC","CONSTRUCTION","HAZARDOUS","HOUSEHOLD"]
cm = confusion_matrix(y_true, y_pred, labels=labels)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
fig, ax = plt.subplots(figsize=(10, 8))
disp.plot(ax=ax, xticks_rotation=45, cmap="Blues")
plt.tight_layout()
plt.savefig("fig3_subtype_confusion.png", dpi=300)
```

---

### Hình 4 — Ảnh detection có bbox (YOLO predict)

**Cách 1 — Ultralytics CLI:**

```python
from ultralytics import YOLO
model = YOLO("best.pt")
model.predict(
    source="path/to/test_images/",  # folder 3–6 ảnh đẹp
    save=True,
    imgsz=1280,
    conf=0.25,
    project="paper_figs",
    name="det_examples",
)
# Ảnh lưu tại paper_figs/det_examples/
```

**Cách 2 — Dashboard demo:**

`http://localhost:8000/demo/demo_capture_classify.html` — upload ảnh test → chụp màn hình có bbox + primary_class + severity.

**Chọn ảnh cho paper:**

- 2 ảnh TRASH VN (bãi rác, góc điện thoại) — bbox đúng
- 1 ảnh WATER — bbox / scene đúng
- 1 ảnh hard negative — E2 không báo WATER (so với E1 nếu có)

**Caption mẫu:** *Hình 4. Ví dụ phát hiện TRASH (a, b) và WATER (c) bằng YOLOv8n fine-tuned trên ảnh citizen-report tại Việt Nam.*

---

### Hình 5 — Qualitative comparison (2×2 grid)

Layout gợi ý:

```text
┌─────────────────┬─────────────────┐
│ (a) Input       │ (b) E1 YOLO-only│
├─────────────────┼─────────────────┤
│ (c) E2 + fusion │ (d) E3 + subtype│
└─────────────────┴─────────────────┘
```

Cùng 1 ảnh input — 3 cột config `.env` khác nhau → screenshot API JSON hoặc overlay bbox.

**Failure case (tùy chọn):** 1 ảnh WATER model miss — thảo luận §6.

---

### Hình 6 — PR curve (optional)

```python
model = YOLO("best.pt")
model.val(data="data.yaml", split="test", imgsz=1280, plots=True)
# Xem folder runs/detect/val*/ — file PR_curve.png, F1_curve.png
```

Copy `PR_curve.png` → đổi tên `fig6_pr_curve.png`.

---

### YOLO val plots tự động

```python
model.val(data="data.yaml", split="test", imgsz=1280, plots=True, save_json=True)
```

Output thường có:

- `confusion_matrix.png` — detection 2 class
- `PR_curve.png`
- `F1_curve.png`
- `P_curve.png`, `R_curve.png`

→ Dùng `confusion_matrix.png` làm **Hình phụ** cho detection (khác Hình 3 subtype).

---

### Latency đo cho Bảng IV

```python
import time
from ultralytics import YOLO
from PIL import Image

model = YOLO("best.pt")
img = Image.open("test.jpg")
# warmup
for _ in range(5):
    model.predict(img, imgsz=1280, verbose=False)
times = []
for _ in range(50):
    t0 = time.perf_counter()
    model.predict(img, imgsz=1280, verbose=False)
    times.append((time.perf_counter() - t0) * 1000)
print(f"Mean latency: {sum(times)/len(times):.1f} ms")
```

API full pipeline: đo thêm qua `/api/v1/classify-upload` với `best.pt` + scene loaded.

---

### Quy ước chèn hình (IEEE / hội đồng VN)

- Độ phân giải **≥ 300 DPI**
- Font trong hình **≥ 8pt**, đọc được khi in
- Caption **dưới hình**, format: *Hình X. Mô tả ngắn.*
- Ảnh thật VN: che mặt / biển số nếu cần
- Trong Word/Google Docs: **Insert → Image**, width 12–15 cm, căn giữa

---

## 8. Abstract & Keywords mẫu

### Abstract (EN) — điền sau khi có số Bảng IV

> Environmental pollution monitoring in Vietnamese urban areas lacks deployable image-based systems that combine object detection with operational waste-type information. We present **GreenLens**, a hybrid pipeline integrating fine-tuned **YOLOv8n** for **TRASH** and **WATER** detection, an **EfficientNet-B0** scene module with **safeguarded fusion** to reduce false water positives, and a **detect-then-classify** stage that assigns seven fine-grained waste subtypes to **TRASH** regions. We curate a YOLO dataset merging public Roboflow sources with **TBD_N_VN** citizen-captured images from Vietnam, with a locked **70/15/15** split. On the held-out test set, fine-tuned detection achieves **mAP@0.5 = TBD** (vs. **TBD** for COCO-pretrained YOLOv8n without fine-tuning). The full pipeline improves WATER stability with **TBD%** lower false-positive rate on hard negatives compared to detection-only inference, while the subtype module reaches **macro-F1 = TBD**. The system is deployed as a **FastAPI** microservice with severity estimation and human-in-the-loop reporting modes, supporting practical citizen pollution reporting in Vietnam.

### Abstract (VI)

> Giám sát ô nhiễm môi trường tại đô thị Việt Nam còn thiếu hệ thống triển khai được dựa trên ảnh, kết hợp phát hiện đối tượng với thông tin loại rác phục vụ vận hành. Bài báo trình bày **GreenLens** — pipeline lai gồm **YOLOv8n** fine-tune cho **TRASH** và **WATER**, mô-đun cảnh **EfficientNet-B0** với **fusion có safeguard**, và giai đoạn **detect-then-classify** phân **bảy loại rác** trên vùng TRASH. Bộ dữ liệu YOLO được xây dựng từ Roboflow và **TBD** ảnh tự thu tại Việt Nam, phân chia **70/15/15** với tập test khóa. Trên tập test, mAP@0.5 đạt **TBD** (so với **TBD** khi dùng YOLOv8n COCO không fine-tune). Pipeline đầy đủ giảm **TBD%** false positive WATER trên ảnh hard negative so với chỉ dùng detector. Macro-F1 phân loại subtype đạt **TBD**. Hệ thống triển khai qua **FastAPI** với ước lượng mức độ nghiêm trọng và human-in-the-loop.

### Keywords

`Object Detection`, `Fine-Tuning`, `Hybrid Pipeline`, `Water Pollution`, `Waste Classification`, `YOLOv8`, `EfficientNet`, `Vietnamese Dataset`, `Citizen Reporting`

---

## 9. Lộ trình 4 tuần

| Tuần | Việc | Output |
|------|------|--------|
| **1** | Kaggle E0 + E1 train + test eval | Bảng IV (E0, E1), Hình 2 |
| **2** | Scene train → E2, đo FP WATER | Bảng V, cập nhật Bảng IV |
| **3** | Subtype E3, predict figures | Bảng VI, Hình 3–5 |
| **4** | Viết §1–§7, Abstract, polish | Draft submit |

---

## 10. Lỗi reviewer hay bắt

| Lỗi | Cách tránh |
|-----|------------|
| Báo val thay vì test | Chỉ `split=test` cho số cuối |
| Paper 3 class SMOKE, code 2 class | Sửa toàn bộ abstract/bảng |
| Baseline chỉ COCO | Phải có **E1 FT-YOLO** cùng data |
| Không có hình qualitative | Ít nhất Hình 4 + 1 failure case |
| Số không reproducible | Đính kèm `args.yaml`, seed=42 |
| Claim SOTA không cite | So TACO/TrashNet cùng metric, không claim beat all |

---

## 11. File tham chiếu trong repo

| File | Mục đích |
|------|----------|
| `docs/paper/PAPER_FULL_PLAYBOOK_VI.md` | **File này** |
| `docs/paper/GREENLENS_IEEE_FULL_DRAFT_PASTE.txt` | Draft cũ — sửa 2 class trước khi paste |
| `docs/paper/HUONG_DAN_CAP_NHAT_GOOGLE_DOC_PHAN_LOAI_LOAI_RAC.md` | Cập nhật Google Doc subtype |
| `ml/training/kaggle/KAGGLE_TRAIN_GUIDE_VI.md` | Train E1 Kaggle |
| `ml/training/kaggle/run_paper_experiments.py` | **E0+E1+E1b** một lệnh |
| `ml/training/kaggle/train_greenlens_e1.py` | Train E1 đơn (legacy) |
| `app/core/pollution_classifier.py` | Fusion logic — §4.4 |
| `app/core/trash_subtype_classifier.py` | Subtype — §4.6 |
| `static/demo/demo_capture_classify.html` | Screenshot qualitative |

---

## Phụ lục A — Script đếm FP WATER (E1 vs E2)

```python
"""Chạy khi server FastAPI đang bật. Folder chỉ chứa hard-negative images."""
import requests
from pathlib import Path

API = "http://127.0.0.1:8000/api/v1/classify-upload"
folder = Path("hard_negatives/")
fp = 0
n = 0
for img in folder.glob("*.*"):
    if img.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        continue
    n += 1
    with img.open("rb") as f:
        r = requests.post(API, files={"file": (img.name, f, "image/jpeg")})
    data = r.json()
    pred = data.get("primary_class")
    if pred == "WATER":
        fp += 1
print(f"WATER false positives: {fp}/{n} = {100*fp/max(n,1):.1f}%")
```

---

## Phụ lục B — Checklist nộp bài

- [ ] Abstract EN/VI có số TBD đã thay hết
- [ ] Bảng I–VII điền đủ
- [ ] Hình 1–5 (tối thiểu 1–4) + caption
- [ ] Test set methodology §3.5
- [ ] Related work ≥ 15 references
- [ ] Limitations §6 trung thực
- [ ] Artifact: `best.pt` + `results.csv` backup (không cần nộp weight nếu journal không yêu cầu)

---

*Tài liệu nội bộ GreenLens — SU26SE049. Cập nhật số liệu tại `paper_metrics.xlsx` song song với file này.*

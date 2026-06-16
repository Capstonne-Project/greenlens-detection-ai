# GreenLens — Draft bài báo (điền từ source code + số thực nghiệm)

> **Nguồn:** `app/`, `ml/training/`, `app/config.py`, `ml/paper_output/`
> **Cập nhật:** 2026-06-08
> **Trạng thái thí nghiệm:** E0 ✅ · E1 ✅ · Scene ⬜ · Subtype ⬜ · Bảng V/VI ⬜

---

## Trạng thái điền số trong draft này

| Phần | Trạng thái | Ghi chú |
|------|------------|---------|
| §4 Method, API, HITL | ✅ Đầy đủ từ code | |
| Bảng I dataset detection | ✅ Số merged | Roboflow vs VN breakdown chưa tách |
| Bảng IV E0 + E1 | ✅ Test 207 ảnh | Kaggle E1 + local E0 |
| Bảng V FP WATER | ⬜ Chưa đo | Cần scene train + eval |
| Bảng VI subtype F1 | ⬜ Chưa train | Cần dataset + train |
| Abstract E3 số | ⬜ FP%, F1 | Sau Bảng V/VI |

---

## Title

**EN:** GreenLens: A Deployable Hybrid Detection Pipeline for Trash and Water Pollution Reporting with Fine-Grained Waste Classification in Vietnamese Urban Contexts

**VI:** GreenLens: Pipeline phát hiện lai rác thải và ô nhiễm nước kèm phân loại chi tiết loại rác cho báo cáo cộng đồng tại đô thị Việt Nam

**Keywords:** Object Detection, Fine-Tuning, Hybrid Pipeline, YOLOv8, EfficientNet-B0, TRASH, WATER, Scene Fusion, Detect-then-Classify, FastAPI, Human-in-the-Loop, Vietnamese Dataset

---

## Abstract

Environmental pollution reporting in Vietnamese urban areas lacks a **deployable** image-based system that combines **object detection**, **water-scene stabilization**, and **operational waste-type labels in one API**. We present **GreenLens**, a hybrid microservice that runs **YOLOv8n** (2 classes: TRASH, WATER) in parallel with an **EfficientNet-B0** scene module (WATER vs NEGATIVE), applies a **safeguarded fusion** rule so scene cannot assert pollution when the detector sees zero objects, and performs **detect-then-classify** on TRASH crops into **seven subtypes**. We evaluate on a merged Roboflow + Vietnam citizen-report dataset (**1,598 images**, locked **test = 207**). Fine-tuned detection (E1) reaches **mAP@0.5 = 0.684** (TRASH: 0.654, WATER: 0.713; mAP@0.5:0.95 = 0.367) versus near-zero COCO-pretrained YOLOv8n (E0: mAP@0.5 = 0.0001). The full GreenLens pipeline (E3) preserves the E1 detector and is designed to reduce WATER false positives via fusion and provide subtype labels — **quantitative FP reduction and macro-F1 are pending** scene/subtype training (Tables V–VI). The system is exposed via **FastAPI** (`/api/v1/classify-upload`) with severity bands, image-relevance gating, and HITL actions (AUTO_FILL / SUGGEST / KEEP_USER_CHOICE).

### Abstract (VI — tóm tắt)

Báo cáo ô nhiễm qua ảnh tại đô thị Việt Nam thiếu hệ thống AI **triển khai được** kết hợp phát hiện đối tượng, ổn định nhận diện nước ô nhiễm và phân loại rác chi tiết. **GreenLens** là pipeline lai: YOLOv8n (TRASH/WATER) song song EfficientNet-B0 scene (WATER/NEGATIVE), fusion có safeguard, và phân loại **7 loại rác** trên vùng TRASH. Trên tập test khóa **207 ảnh**, fine-tune (E1) đạt mAP@0.5 **0,684** so với baseline COCO (E0: **0,0001**). Pipeline đầy đủ (E3) dùng chung detector E1 và bổ sung fusion + subtype — số FP WATER và F1 subtype sẽ báo sau khi hoàn tất train scene/subtype.

---

## 1. Introduction

### 1.1 Problem

Citizens report pollution via smartphone photos. Practical systems need:

1. Detect **trash** and **water pollution** with bounding boxes.
2. Reduce **false WATER** on wet roads, shadows, non-pollution scenes.
3. Provide **waste subtypes** for operations (recycling, hazardous, medical, etc.).
4. Return **actionable API JSON** for a .NET/mobile backend with audit fields.

### 1.2 Limitations of common Detection-AI approaches (same task family)

| Approach | Limitation (for VN citizen reports) | Evidence in our benchmark |
|----------|-------------------------------------|---------------------------|
| Generic YOLO (COCO) | No TRASH/WATER domain | E0 ALL mAP@0.5 = **0.0001** |
| Fine-tuned detect-only YOLO | Strong mAP; no subtype; WATER bbox hard | E1 mAP@0.5 = **0.684**; no subtype field |
| Scene-only classifier | No bbox / end-to-end report | Code: scene supplements only |
| Classify-only (TrashNet-style) | No spatial evidence | No bbox in API response |

### 1.3 Research gaps (aligned with repo)

| Gap | GreenLens addresses |
|-----|---------------------|
| **G1** Unified VN benchmark TRASH+WATER | Merged YOLO dataset, locked test 207 |
| **G2** WATER instability / FP | Parallel scene + **safeguard fusion** (`_merge_yolo_and_scene`) |
| **G3** Fine-grained waste in pollution flow | 7-class subtype on TRASH crops |
| **G4** Deployability | FastAPI, severity, relevance, HITL, `model_version` audit |

### 1.4 Contributions

- **C1:** Curated **2-class** YOLO dataset (1,598 images; 4,462 bboxes) and fine-tuned **YOLOv8n** (E1: mAP@0.5 **0.684** on test).
- **C2:** **GreenLens-Det (E2):** E1 + EfficientNet-B0 scene with safeguard fusion (τ_scene = 0.45).
- **C3:** **GreenLens-Full (E3):** E2 + detect-then-classify **7 trash subtypes** (τ_subtype = 0.40).
- **C4:** FastAPI microservice with severity (BR-AI-003), image relevance, and HITL thresholds.

### 1.5 Paper structure

Sections 2–7: related work, dataset, method, experiments (E0–E3), discussion, conclusion.

### 1.6 So sánh “model tôi vs Detection-AI bên ngoài”

Trên **cùng benchmark test 207 ảnh**:

| Đối thủ (cách làm phổ biến) | Thí nghiệm | Kết quả / claim |
|-----------------------------|------------|-----------------|
| Generic detector, không fine-tune | **E0** | mAP@0.5 ≈ 0 → cần fine-tune domain |
| Fine-tuned YOLO detect-only | **E1** | mAP@0.5 = **0.684** — baseline mạnh nhất |
| **GreenLens-Full (đề xuất)** | **E3 ★** | Cùng detector E1 + FP WATER ↓ + subtype (pending) |

Related work (TACO, TrashNet…) ở §2 — **bàn luận gap**, không copy mAP khác dataset vào Bảng IV.

---

## 2. Related Work

### 2.1 Object detection for litter and pollution

**TACO** (Trash Annotations in Context) provides instance-level litter annotations in global street scenes, primarily for trash detection and segmentation. **YOLO-based litter detectors** on Roboflow and similar platforms typically target single-class or generic trash boxes. These approaches rarely unify **TRASH and WATER** pollution in one detector tuned for **Vietnamese citizen-report imagery**. Our E0/E1 comparison on the same test set quantifies the domain gap: COCO-pretrained YOLOv8n (E0) fails (mAP@0.5 = 0.0001), while domain fine-tuning (E1) reaches 0.684.

### 2.2 Scene classification for water pollution

Scene-level water pollution classifiers predict whether an image depicts polluted water without object-level localization. Used alone, they lack bounding-box evidence required for operational reporting. GreenLens uses scene probabilities **only as a supplement** to YOLO, with an explicit safeguard: scene cannot add WATER when the detector finds zero objects (`raw_detector_boxes == 0`).

### 2.3 Detect-then-classify for waste

**TrashNet** and similar datasets focus on **image-level** waste classification (e.g., six recycling categories). GreenLens implements **detect-then-classify**: YOLO localizes TRASH regions, then EfficientNet-B0 classifies **cropped bbox patches** (+4 px pad) into seven subtypes, aggregated per image in the API response.

### 2.4 Environmental AI and citizen reporting in Vietnam

Citizen science platforms for environmental monitoring in Vietnam increasingly rely on mobile photo uploads. Few published systems combine **2-class pollution detection**, **fusion-based WATER stabilization**, **fine-grained waste labels**, and a **deployable REST API** with human-in-the-loop policies in one pipeline.

### Bảng IV-B — Literature comparison (qualitative)

| Work | Method | Dataset / context | Metric reported (literature) | vs GreenLens |
|------|--------|-------------------|------------------------------|--------------|
| TACO | Instance seg / detect | Global street litter | mAP (varies by split) | + WATER + VN + API + 7 subtypes |
| TrashNet | Image classification | 6 recycle classes | Accuracy | GreenLens: bbox + pipeline |
| YOLO litter (Roboflow) | Single-class detect | Generic litter | mAP | GreenLens: 2-class TRASH+WATER |
| Generic YOLOv8n-COCO | Pretrained detect | COCO 80 classes | — | E0 on our test: 0.0001 mAP@0.5 |
| **GreenLens-Full (Ours)** | Hybrid YOLO+scene+subtype | VN merged benchmark | mAP@0.5 = **0.684** (detect) | **★ Proposed** |

---

## 3. Dataset

### 3.1 Sources

- **Roboflow** public pollution/litter projects (merged via `POST /api/v1/training/datasets/merge-zips`).
- **Vietnam** self-captured / citizen-style images (self-labeled).
- **Kaggle release:** `pollution-merge-vn-nation` — `/kaggle/input/datasets/hulphc/pollution-merge-vn-nation`.
- **Local path (E0 eval):** `D:\CapsoneProject\DATASETFINAL\TOTAL\datasetfinal`.

### 3.2 Bảng I — Detection dataset statistics

| Item | Train | Val | Test | **Total** |
|------|-------|-----|------|-----------|
| **Images** | 1,147 | 244 | 207 | **1,598** |
| **Share** | 71.8% | 15.3% | 12.9% | 100% |
| **Bboxes (all splits)** | — | — | — | **~4,462** |
| TRASH bboxes | — | — | — | **~3,061** |
| WATER bboxes | — | — | — | **~1,401** |

| Metadata | Value |
|----------|-------|
| Detection classes | **TRASH (id=0), WATER (id=1)** |
| Empty label files | **~43** (~2.7% — background / hard negative) |
| Format | YOLO `images/{split}`, `labels/{split}` |
| Split policy | ~70/15/15 (train/val/test) |
| Test lock | Test **207** chỉ dùng báo số paper — không tune |

*Roboflow vs VN per-source image counts: chưa tách trong repo — điền khi thống kê nguồn.*

### 3.3 Bảng I-b — Test set breakdown (E1 eval log, Ultralytics)

| Split | Images | Instances | Background images |
|-------|--------|-----------|-------------------|
| **Test (all)** | **207** | **240** | **5** |
| Test — TRASH | 101 | 124 | — |
| Test — WATER | 101 | 116 | — |

### 3.4 Labeling & QC

- YOLO normalized bbox format; `0=TRASH`, `1=WATER`.
- Dashboard tools: `inspect`, `preview-labels`, `filter-classes`, `merge-zips`.
- Script: `ml/training/scripts/verify_yolo_dataset.py` (`--nc 2`).

### 3.5 Detection training configuration (E1)

| Parameter | Value |
|-----------|-------|
| Model init | `yolov8n.pt` |
| Epochs | 150 |
| Image size | 1280 |
| Batch | 8 |
| Seed | 42 |
| Patience | 30 |
| AMP | True |
| Optimizer | Ultralytics default |
| Train hardware | Kaggle **Tesla T4** |
| Train wall time | **~2.6 h** (~9,339 s, Commit log) |
| Framework | Ultralytics **8.4.61**, PyTorch 2.10+cu128 |

### 3.6 Bảng II — Scene dataset (E2) — *chưa hoàn tất*

**Runtime (production):** `WATER`, `NEGATIVE` — `app/core/scene_classifier.py`.

**Lần train gần nhất (job `scj_7b29e8f783`):** **thất bại epoch 1** (UnicodeEncodeError Windows); data tạm mất.

| Item | Giá trị ghi nhận | Ghi chú |
|------|------------------|---------|
| Tổng ảnh trước split | **170** (146 train + 24 val auto) | Log dashboard |
| Lớp trong zip cũ | NEGATIVE, SMOKE, WATER (3-class legacy) | Train script cũ |
| **Mục tiêu paper** | WATER + NEGATIVE only | Bỏ SMOKE |
| Val auto-split | 15% | `val_fraction=0.15` |
| Trạng thái weight | **Chưa có** `scene_classifier.pt` hoàn chỉnh | Cần rebuild data + train |

### 3.7 Bảng II-b — Subtype dataset (E3) — *chưa có*

**7 classes** (`TRASH_SUBTYPES`): CONSTRUCTION, ELECTRONIC, HAZARDOUS, HOUSEHOLD, MEDICAL, ORGANIC, RECYCLABLE.

| Class | Train | Val | Test |
|-------|-------|-----|------|
| CONSTRUCTION | — | — | — |
| ELECTRONIC | — | — | — |
| HAZARDOUS | — | — | — |
| HOUSEHOLD | — | — | — |
| MEDICAL | — | — | — |
| ORGANIC | — | — | — |
| RECYCLABLE | — | — | — |

Upload: `POST /api/v1/training/subtype/datasets/merge-zips`. Gợi ý nguồn: TACO, TrashNet/Roboflow, Kaggle garbage classification (`docs/TRASH_SUBTYPE_GUIDE.md`).

---

## 4. Method — GreenLens Pipeline

### 4.1 Overview (Hình 1)

```text
Input image (RGB, max 20 MB)
    │
    ├─► [Parallel] YOLOv8n ──► TRASH / WATER bboxes (imgsz=1280)
    │         │
    │         └─► if TRASH boxes & subtype model loaded:
    │               crop bbox (+4px pad) ──► EfficientNet-B0 ──► 7 subtypes
    │
    └─► [Parallel] EfficientNet-B0 scene ──► P(WATER)
              │
              ▼
         Fusion + Safeguard (_merge_yolo_and_scene)
              │
              ▼
         Severity + Image relevance + HITL action
              │
              ▼
         JSON ClassifyResponse (FastAPI)
```

**Code:** `app/core/pollution_classifier.py` — `PollutionClassifier`.

### 4.2 Stage 1 — YOLOv8n detector (E1)

| Parameter | Value |
|-----------|-------|
| Classes | TRASH, WATER |
| Inference imgsz | 1280 |
| Weights | `ml/weights/best.pt` |
| Synonyms | GARBAGE/WASTE→TRASH; SEWAGE→WATER |
| Coverage ratio | Σ(bbox area) / image area, clamp ≤ 1 |

### 4.3 Stage 2 — Scene classifier (E2)

| Parameter | Value |
|-----------|-------|
| Architecture | EfficientNet-B0 |
| Classes (inference) | WATER, NEGATIVE |
| Transform | Resize 256, CenterCrop 224, ImageNet norm |
| Fusion threshold τ | **0.45** (`SCENE_CLASSIFIER_THRESHOLD`) |
| Train defaults | epochs 15, batch 16, lr 1e-4, AdamW, CosineAnnealing |
| Train aug | RandomResizedCrop, HFlip, ColorJitter |

### 4.4 Fusion & safeguard (vs E1)

1. YOLO bbox predictions take priority per class.
2. Scene adds **WATER only if** `raw_detector_boxes > 0`.
3. Scene WATER requires `P(WATER) ≥ 0.45`.
4. If YOLO finds **zero** boxes → scene **cannot** assert WATER alone.
5. Parallel: `ThreadPoolExecutor(max_workers=2)`.

### 4.5 Stage 3 — Trash subtype (E3)

| Parameter | Value |
|-----------|-------|
| Architecture | EfficientNet-B0 |
| Classes | 7 subtypes (§3.7) |
| Crop pad | +4 px |
| Threshold τ | **0.40** — below → `UNKNOWN` |
| Train defaults | epochs 100, batch 32, lr 1e-3 |

###    (BR-AI-003 v1)

| Coverage ratio r | Severity |
|------------------|----------|
| r < 0.05 | LOW |
| 0.05 ≤ r < 0.15 | MEDIUM |
| 0.15 ≤ r < 0.40 | HIGH |
| r ≥ 0.40 | CRITICAL |

### 4.7 Image relevance

| Condition | Label |
|-----------|-------|
| ≥1 mapped box & max conf ≥ 0.30 | POLLUTION_LIKELY |
| Raw boxes but none mapped | UNCLEAR_NEED_MANUAL_REVIEW |
| No raw boxes | NOT_POLLUTION_OR_UNRELATED |

### 4.8 Bảng III — HITL mapping

| Action | Confidence | UI |
|--------|------------|-----|
| AUTO_FILL | ≥ **0.80** | Tự điền |
| SUGGEST | **0.50** – 0.80 | Gợi ý |
| KEEP_USER_CHOICE | < 0.50 | Giữ lựa chọn user |

Override: `image_relevance ≠ POLLUTION_LIKELY` và không có mapped box → `KEEP_USER_CHOICE`.

### 4.9 API deployment

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health` | GET | Health |
| `/api/v1/ready` | GET | Readiness |
| `/api/v1/classify` | POST | Classify from URL |
| `/api/v1/classify-upload` | POST | Multipart classify |
| `/api/v1/classify-moderation-upload` | POST | Classify + moderation |
| `/api/v1/images/normalize` | POST | Image normalize |
| `/api/v1/training/*` | * | Train orchestration |

| Limit | Value |
|-------|-------|
| Max upload | 20 MB |
| Inference timeout | 4.5 s |
| Service | FastAPI 0.1.0, port 8000 |

**Moderation:** POLLUTION_LIKELY → ACCEPTABLE_REPORT_IMAGE; UNCLEAR → NEED_MANUAL_REVIEW; NOT_POLLUTION → IRRELEVANT_OR_SUSPECTED_ABUSIVE.

**Audit:** `model_version` = `{YOLO_VERSION}|scene:{SCENE_VERSION|off}`.

### 4.10 Graceful degradation

| State | Behavior |
|-------|----------|
| No YOLO weights | stub / `CLASSIFY_DEMO_MODE` |
| No scene | `scene_classifier_active=false` |
| No subtype | `trash_subtype_active=false`, `subtypes=null` |

---

## 5. Experiments

### 5.1 Setup

| Item | Value |
|------|-------|
| E0 eval | Local Windows, `run_paper_experiments.py --mode e0` |
| E1 train+eval | Kaggle **Tesla T4**, Ultralytics 8.4.61 |
| Python | 3.12 |
| Eval split | **test only** (207 images) |
| Reproducibility | seed=42 |

### 5.2 Metrics

- Detection: P, R, mAP@0.5, mAP@0.5:0.95
- Fusion: WATER FP on hard negatives; WATER recall on test
- Subtype: macro-F1, per-class F1
- Deploy: `inference_time_ms`, model size (MB)

### 5.3 Experiment design

| ID | System | Modules | Role |
|----|--------|---------|------|
| **E0** | YOLOv8n-COCO | Pretrained only | Generic baseline |
| **E1** | FT-YOLOv8n | Detector only | Strong detect-only baseline |
| **E2** | GreenLens-Det | E1 + scene fusion | Ablation |
| **E3 ★** | GreenLens-Full | E2 + subtype + API | **Ours** |

### 5.4 Bảng IV — Detection results (TEST, 207 images) ⭐

| Role | Method | FT | TRASH P | TRASH R | TRASH mAP50 | TRASH mAP50-95 | WATER P | WATER R | WATER mAP50 | WATER mAP50-95 | ALL P | ALL R | **ALL mAP50** | **ALL mAP50-95** |
|------|--------|----|---------|---------|-------------|----------------|---------|---------|-------------|----------------|-------|-------|---------------|------------------|
| Baseline | E0 YOLOv8n-COCO | Không | 0.0023 | 0.0081 | 0.0001 | 0.0001 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0012 | 0.004 | **0.0001** | **0.0** |
| Baseline FT | E1 FT-YOLOv8n | Có | 0.628 | 0.685 | **0.654** | **0.319** | 0.658 | 0.729 | **0.713** | **0.414** | 0.643 | 0.707 | **0.684** | **0.367** |
| Ours | E2 GreenLens-Det | Có | = E1 | = E1 | = E1 | = E1 | — | — | Bảng V | = E1 | — | — | = E1 | = E1 |
| **Ours ★** | **E3 GreenLens-Full** | Có | = E1 | = E1 | = E1 | = E1 | — | — | Bảng V | = E1 | — | — | = E1 | = E1 |

**Nguồn số:** E0 — `ml/paper_output/paper_metrics.json` (2026-06-07). E1 — Kaggle Commit val test (2026-06-08).

**ΔmAP@0.5 (E1 − E0):** **+0.6839** absolute (E0 ≈ 0 → % relative không meaningful).

**Claim 1:** Domain fine-tune is **mandatory** for VN pollution detection.

**Claim 2 (pending):** E3 improves WATER stability vs E1 — Table V.

> *GreenLens-Full (E3) reuses E1 detector weights; gains are in fusion stability and subtype labels (Tables V–VI), not a separate detector training run.*

### 5.5 Bảng V — Fusion / WATER stability — *chưa đo*

| Config | Modules | WATER FP / N hard-neg | WATER recall / N test-WATER | Status |
|--------|---------|----------------------|----------------------------|--------|
| E1 | YOLO only | — | — | Chưa chạy eval script |
| E2/E3 | YOLO + scene (τ=0.45) | — | — | Chờ `scene_classifier.pt` |

**Protocol:** N ≈ 30–50 NEGATIVE images; count predictions with WATER primary or WATER in `predictions`. Compare E1 (scene off) vs E3 (scene on).

### 5.6 Bảng VI — Subtype — *chưa train*

| Subtype | P | R | F1 |
|---------|---|---|-----|
| CONSTRUCTION | — | — | — |
| ELECTRONIC | — | — | — |
| HAZARDOUS | — | — | — |
| HOUSEHOLD | — | — | — |
| MEDICAL | — | — | — |
| ORGANIC | — | — | — |
| RECYCLABLE | — | — | — |
| **Macro-F1** | | | **—** |

### 5.7 Bảng VII — Deployment

| Component | Params / size | Latency |
|-----------|---------------|---------|
| YOLOv8n `best.pt` | **~3.0M params**, ~6–7 MB | YOLO val ref: **~10.6 ms/img** infer (T4, E1 log) |
| Scene EfficientNet-B0 | ~5.3M params, ~16 MB (typical) | Parallel with YOLO |
| Subtype EfficientNet-B0 | ~5.3M params | Per TRASH bbox |
| **Full API pipeline** | — | Đo `inference_time_ms` từ `/classify-upload` — *chưa benchmark* |

### 5.8 Figures

| Hình | Trạng thái | Nguồn |
|------|------------|-------|
| Hình 1 Pipeline | ✅ Vẽ được | §4.1 |
| Hình 2 Learning curve | ✅ Có `results.csv` từ E1 Kaggle | matplotlib |
| Hình 3 Confusion subtype | ⬜ | Sau train subtype |
| Hình 4–5 Qualitative bbox | ✅ Có `best.pt` | `/classify-upload` |
| Hình 6 Bar E0 vs E1 mAP50 | ✅ | Bảng IV |

---

## 6. Discussion

### 6.1 E1 vs E0 — domain gap

COCO-pretrained YOLOv8n essentially **fails** on TRASH/WATER in VN citizen imagery (ALL mAP@0.5 = 0.0001). Fine-tuning raises ALL mAP@0.5 to **0.684** — a **6,840×** relative improvement (absolute +0.6839), supporting Contribution C1.

### 6.2 E3 vs E1 — why hybrid pipeline (pending numbers)

E1 already achieves strong detection (WATER mAP@0.5 **0.713** > TRASH **0.654**). GreenLens adds:

- **Safeguarded scene fusion** to reduce false WATER when YOLO sees objects in ambiguous scenes.
- **Seven subtype labels** on TRASH crops for operational routing (recycling, hazardous, medical).
- **API-level** severity, relevance, and HITL — not available in detect-only E1.

Quantitative FP and F1 pending Tables V–VI.

### 6.3 WATER > TRASH mAP on test

WATER mAP@0.5 (0.713) exceeds TRASH (0.654) despite similar test image counts (101 vs 101). Possible factors: bbox size, class appearance, label consistency. Scene fusion in E3 targets **stability** of WATER decisions, not necessarily higher mAP.

### 6.4 Implementation notes

- **Production detection: 2 classes** (TRASH/WATER). Do not cite legacy 3-class SMOKE docs.
- Scene train script lists SMOKE; **inference** uses WATER/NEGATIVE only.
- Set `PYTHONUTF8=1` on Windows when training scene (avoid log encoding crash).

### 6.5 Limitations

- Single internal VN benchmark (1,598 images).
- Scene/subtype experiments incomplete.
- No mobile TFLite benchmark yet.
- Roboflow vs VN source breakdown not tabulated.

---

## 7. Conclusion

We presented **GreenLens**, a deployable hybrid pipeline: fine-tuned **YOLOv8n** (TRASH/WATER), **EfficientNet-B0** scene fusion with safeguards, **seven-class** trash subtyping, and **FastAPI** with severity and HITL. On a locked test set of **207 images**, E1 achieves **mAP@0.5 = 0.684** vs E0 **0.0001**, demonstrating that domain-specific fine-tuning is essential. GreenLens-Full (E3) extends E1 with fusion and subtype capabilities aimed at operational superiority over detect-only baselines — **full quantitative validation of FP reduction and subtype F1 remains future work** upon completing scene and subtype training.

**Next steps:** rebuild scene dataset (WATER/NEGATIVE), train `scene_classifier.pt`, collect subtype data, measure Tables V–VI, profile end-to-end API latency.

---

## Appendix A — Hyperparameters

### A.1 YOLO E1
```
model: yolov8n.pt | epochs: 150 | imgsz: 1280 | batch: 8 | seed: 42 | patience: 30
classes: TRASH, WATER
```

### A.2 Scene
```
epochs: 15 | batch: 16 | lr: 1e-4 | AdamW wd=1e-4 | CosineAnnealing
inference_threshold: 0.45
```

### A.3 Subtype
```
epochs: 100 | batch: 32 | lr: 1e-3 | threshold: 0.40 | crop_pad: 4px
```

### A.4 API
```
AUTO_FILL: ≥0.80 | SUGGEST: ≥0.50 | RELEVANCE_MIN: 0.30 | TIMEOUT: 4.5s | MAX: 20MB
```

---

## Appendix B — Example API response

```json
{
  "predictions": [{
    "class": "TRASH",
    "confidence": 0.87,
    "bbox_count": 2,
    "boxes": [{
      "x1": 100, "y1": 200, "x2": 300, "y2": 400,
      "confidence": 0.87,
      "subtype": "RECYCLABLE",
      "subtype_confidence": 0.92
    }],
    "subtypes": [{ "subtype": "RECYCLABLE", "count": 1, "confidence": 0.92 }]
  }],
  "primary_class": "TRASH",
  "confidence": 0.87,
  "action": "AUTO_FILL",
  "model_version": "v4.0.0-2class-150ep-1280px-kaggle|scene:off",
  "yolo_active": true,
  "scene_classifier_active": false,
  "trash_subtype_active": false,
  "severity": "MEDIUM",
  "pollution_coverage_ratio": 0.12,
  "image_relevance": "POLLUTION_LIKELY",
  "inference_time_ms": 245.3
}
```

---

## Appendix C — Lệnh reproduce

### E0 (local)
```cmd
uv run python ml\training\kaggle\run_paper_experiments.py --mode e0 ^
  --dataset-dir "D:\CapsoneProject\DATASETFINAL\TOTAL\datasetfinal" ^
  --output-dir "ml\paper_output" --imgsz 1280
```

### E1 (Kaggle — 2 cell notebook, đã chạy thành công)
- Cell 1: `pip install ultralytics`
- Cell 2: train YOLOv8n 150ep + val test → `paper_output/E1/best.pt`

### Scene (sau khi có data)
```cmd
set PYTHONUTF8=1
uv run python ml\training\train_scene_classifier.py --data-root ml\training\data\scene --epochs 20
```

### Subtype (sau khi có data)
```cmd
uv run python ml\training\train_trash_subtype_classifier.py --data-root ml\training\data\trash_subtype --epochs 100
```

---

## File liên quan

| File | Nội dung |
|------|----------|
| `ml/paper_output/BANG_IV.md` | Bảng IV tóm tắt |
| `ml/paper_output/paper_metrics.json` | E0 chi tiết |
| `docs/paper/PAPER_FULL_PLAYBOOK_VI.md` | Playbook đầy đủ |
| `docs/paper/CHECKPOINT_E1_KAGGLE_VI.md` | Checkpoint train |
| `app/core/pollution_classifier.py` | Pipeline |

---

_Draft filled from source code + experiments — 2026-06-08_

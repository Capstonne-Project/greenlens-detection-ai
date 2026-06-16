<div align="center">

# BÁO CÁO ĐỒ ÁN / NGHIÊN CỨU

## GREENLENS

### Hệ thống pipeline lai phát hiện rác thải và ô nhiễm nước kèm phân loại chi tiết loại rác cho báo cáo cộng đồng tại đô thị Việt Nam

---

**Tiếng Anh:** *GreenLens: A Deployable Hybrid Detection Pipeline for Trash and Water Pollution Reporting with Fine-Grained Waste Classification in Vietnamese Urban Contexts*

---

| | |
|---|---|
| **Sinh viên thực hiện** | _[Họ và tên]_ |
| **Mã sinh viên** | _[MSSV]_ |
| **Giảng viên hướng dẫn** | _[Họ và tên GVHD]_ |
| **Khoa / Bộ môn** | _[Tên khoa]_ |
| **Trường** | _[Tên trường]_ |
| **Thời gian** | Tháng 06 / 2026 |

</div>

---

> **Nguồn nội dung:** `docs/paper/GREENLENS_PAPER_DRAFT_FROM_CODE_VI.md`
> **Repository:** `greenlens-detection-ai`
> **Phiên bản báo cáo:** 1.0 — 2026-06-08
> **Trạng thái thí nghiệm:** E0 ✅ · E1 ✅ · Scene ⬜ · Subtype ⬜

---

## LỜI CAM ĐOAN

Tôi xin cam đoan đây là công trình nghiên cứu / đồ án do chính tôi thực hiện dưới sự hướng dẫn của giảng viên. Các số liệu thực nghiệm, mã nguồn và kết quả được trình bày trung thực. Các phần tham khảo từ tài liệu khác đều được trích dẫn rõ ràng.

<div align="right">

_[Họ tên sinh viên]_

_[Ngày / tháng / năm]_

</div>

---

## LỜI CẢM ƠN

_[Điền lời cảm ơn giảng viên hướng dẫn, khoa, gia đình, đồng đội dự án GreenLens…]_

---

## TÓM TẮT (ABSTRACT)

Báo cáo ô nhiễm môi trường qua ảnh chụp từ điện thoại tại đô thị Việt Nam đang thiếu một hệ thống trí tuệ nhân tạo **có thể triển khai thực tế**, kết hợp đồng thời **phát hiện đối tượng** (rác thải, nước ô nhiễm), **ổn định nhận diện nước** và **phân loại chi tiết loại rác** trong một API duy nhất.

Đồ án xây dựng **GreenLens** — microservice FastAPI gồm ba tầng: (1) **YOLOv8n** fine-tune hai lớp TRASH/WATER; (2) **EfficientNet-B0** phân loại cảnh WATER/NEGATIVE chạy song song, kết hợp theo quy tắc fusion có **safeguard** (scene không được khẳng định ô nhiễm khi detector không thấy đối tượng); (3) **detect-then-classify** trên vùng TRASH thành **7 loại rác** vận hành (CONSTRUCTION, ELECTRONIC, HAZARDOUS, HOUSEHOLD, MEDICAL, ORGANIC, RECYCLABLE).

Dữ liệu gồm **1.598 ảnh** gộp từ Roboflow và ảnh báo cáo phong cách Việt Nam, chia train/val/test (**207 ảnh test khóa**). Thí nghiệm E0 (YOLOv8n-COCO, không fine-tune) đạt mAP@0.5 = **0,0001**; E1 (fine-tune domain) đạt mAP@0.5 = **0,684** (TRASH: 0,654; WATER: 0,713; mAP@0.5:0.95 = 0,367). Pipeline đầy đủ E3 (GreenLens-Full) tái sử dụng detector E1 và bổ sung fusion + subtype — các chỉ số giảm false positive WATER và macro-F1 subtype sẽ hoàn thiện sau khi train scene/subtype.

**Từ khóa:** Phát hiện đối tượng, Fine-tuning, Pipeline lai, YOLOv8, EfficientNet-B0, TRASH, WATER, Scene Fusion, Detect-then-Classify, FastAPI, Human-in-the-Loop, Dữ liệu Việt Nam

---

## MỤC LỤC

| STT | Nội dung | Trang |
|-----|----------|-------|
| | Lời cam đoan | |
| | Lời cảm ơn | |
| | Tóm tắt | |
| **1** | **Giới thiệu** | |
| 1.1 | Bối cảnh và vấn đề | |
| 1.2 | Mục tiêu đồ án | |
| 1.3 | Phạm vi và đối tượng nghiên cứu | |
| 1.4 | Đóng góp chính | |
| 1.5 | Cấu trúc báo cáo | |
| **2** | **Cơ sở lý thuyết và tổng quan nghiên cứu** | |
| 2.1 | Phát hiện rác và ô nhiễm bằng deep learning | |
| 2.2 | Phân loại cảnh nước ô nhiễm | |
| 2.3 | Detect-then-classify cho phân loại rác | |
| 2.4 | AI môi trường và báo cáo cộng đồng tại Việt Nam | |
| 2.5 | So sánh với các hướng tiếp cận liên quan | |
| **3** | **Dữ liệu và thiết lập thí nghiệm** | |
| 3.1 | Nguồn dữ liệu | |
| 3.2 | Thống kê tập detection | |
| 3.3 | Dữ liệu scene và subtype | |
| 3.4 | Cấu hình huấn luyện E1 | |
| **4** | **Thiết kế và triển khai hệ thống GreenLens** | |
| 4.1 | Kiến trúc tổng quan | |
| 4.2 | Tầng phát hiện YOLOv8n | |
| 4.3 | Tầng scene và fusion | |
| 4.4 | Tầng phân loại subtype | |
| 4.5 | Mức độ nghiêm trọng, relevance, HITL | |
| 4.6 | API và triển khai | |
| **5** | **Thực nghiệm và kết quả** | |
| 5.1 | Thiết kế thí nghiệm E0–E3 | |
| 5.2 | Kết quả phát hiện (Bảng IV) | |
| 5.3 | Kết quả fusion WATER (Bảng V) | |
| 5.4 | Kết quả subtype (Bảng VI) | |
| 5.5 | Triển khai và hiệu năng | |
| **6** | **Thảo luận** | |
| **7** | **Kết luận và hướng phát triển** | |
| | Tài liệu tham khảo | |
| | Phụ lục | |

---

## DANH MỤC KÝ HIỆU VÀ VIẾT TẮT

| Ký hiệu | Ý nghĩa |
|---------|---------|
| TRASH | Rác thải (lớp phát hiện id=0) |
| WATER | Nước / vùng ô nhiễm nước (lớp phát hiện id=1) |
| NEGATIVE | Cảnh không ô nhiễm nước (scene classifier) |
| mAP@0.5 | Mean Average Precision tại IoU = 0,5 |
| mAP@0.5:0.95 | mAP trung bình IoU 0,5–0,95 (COCO metric) |
| FP | False Positive — dự đoán sai dương tính |
| HITL | Human-in-the-Loop — người dùng trong vòng lặp |
| API | Application Programming Interface |
| E0–E3 | Mã thí nghiệm (baseline → pipeline đầy đủ) |
| τ | Ngưỡng (threshold) xác suất |

---

## BẢNG THEO DÕI TIẾN ĐỘ THỰC NGHIỆM

| Bước | Nội dung | Trạng thái | Ghi chú |
|------|----------|------------|---------|
| 0 | Dataset gộp + khóa test 207 ảnh | ✅ | Kaggle `pollution-merge-vn-nation` |
| E0 | YOLOv8n-COCO, không fine-tune | ✅ | mAP@0.5 = 0,0001 |
| E1 | Fine-tune YOLOv8n | ✅ | mAP@0.5 = 0,684; `ml/weights/best.pt` |
| E2 | Train scene + đo FP WATER | ⬜ | Chờ `scene_classifier.pt` |
| E3 | Train subtype + macro-F1 | ⬜ | Chờ dataset + train |
| Docs | Báo cáo + bài báo | 🔄 | File này |

---

# CHƯƠNG 1. GIỚI THIỆU

## 1.1. Bối cảnh và vấn đề

Ứng dụng báo cáo ô nhiễm môi trường cho phép người dân gửi ảnh chụp tại hiện trường. Để hỗ trợ điều phối xử lý, hệ thống AI cần đáp ứng các yêu cầu sau:

1. **Phát hiện rác thải và ô nhiễm nước** kèm hộp giới hạn (bounding box) làm bằng chứng không gian.
2. **Giảm báo nhầm WATER** trên đường ướt, bóng đổ, cảnh không phải ô nhiễm thực sự.
3. **Phân loại chi tiết loại rác** phục vụ vận hành (tái chế, nguy hại, y tế…).
4. **Trả về JSON qua API** để backend .NET/mobile tích hợp, kèm trường audit (`model_version`, mức độ nghiêm trọng, hành động HITL).

Các hướng Detection-AI phổ biến khi áp dụng trực tiếp cho ảnh báo cáo Việt Nam gặp hạn chế:

| Hướng tiếp cận | Hạn chế | Bằng chứng trên benchmark nội bộ |
|----------------|---------|----------------------------------|
| YOLO generic (COCO) | Không có domain TRASH/WATER | E0: mAP@0.5 = **0,0001** |
| YOLO fine-tune detect-only | mAP tốt nhưng không subtype; WATER khó | E1: mAP@0.5 = **0,684**; không có trường subtype |
| Scene-only | Không có bbox / báo cáo end-to-end | Scene chỉ bổ trợ trong code |
| Classify-only (TrashNet…) | Không có bằng chứng không gian | API không trả bbox |

## 1.2. Mục tiêu đồ án

| Mục tiêu | Mô tả |
|----------|-------|
| **MT1** | Xây dựng benchmark nội bộ TRASH + WATER trên ảnh Việt Nam (test khóa 207 ảnh). |
| **MT2** | Fine-tune YOLOv8n đạt mAP phát hiện có ý nghĩa so với baseline COCO. |
| **MT3** | Thiết kế pipeline lai YOLO + scene fusion có safeguard giảm FP WATER. |
| **MT4** | Tích hợp phân loại 7 subtype trên vùng TRASH (detect-then-classify). |
| **MT5** | Triển khai microservice FastAPI sẵn sàng tích hợp backend. |

## 1.3. Phạm vi và đối tượng nghiên cứu

- **Trong phạm vi:** Phát hiện 2 lớp TRASH/WATER; scene WATER/NEGATIVE; 7 subtype; API classify-upload; thí nghiệm E0–E3 trên cùng tập test.
- **Ngoài phạm vi (giai đoạn hiện tại):** Phát hiện khói (SMOKE) ở production; benchmark mobile TFLite; so sánh mAP trực tiếp với paper TACO/TrashNet trên dataset khác.

## 1.4. Đóng góp chính

| Mã | Đóng góp | Chi tiết |
|----|----------|----------|
| **C1** | Dataset và detector | 1.598 ảnh, ~4.462 bbox; YOLOv8n E1 mAP@0.5 = **0,684** |
| **C2** | GreenLens-Det (E2) | E1 + scene EfficientNet-B0, fusion τ = 0,45 |
| **C3** | GreenLens-Full (E3) ★ | E2 + 7 subtype (τ = 0,40) + API đầy đủ |
| **C4** | Triển khai | Severity BR-AI-003, image relevance, HITL, audit |

### So sánh GreenLens với baseline cùng test set

| Đối thủ | Thí nghiệm | Kết quả / vai trò |
|---------|------------|-------------------|
| Detector generic, không fine-tune | **E0** | mAP@0.5 ≈ 0 → bắt buộc fine-tune domain |
| YOLO fine-tune detect-only | **E1** | mAP@0.5 = **0,684** — baseline mạnh |
| **GreenLens-Full (đề xuất)** | **E3 ★** | Cùng detector E1 + fusion + subtype |

> **Quy ước:** Model đề xuất chính trong báo cáo = **E3 GreenLens-Full**. E1 là thành phần detector bên trong E3.

## 1.5. Cấu trúc báo cáo

- **Chương 2:** Cơ sở lý thuyết và tổng quan nghiên cứu liên quan.
- **Chương 3:** Mô tả dữ liệu và thiết lập huấn luyện.
- **Chương 4:** Thiết kế pipeline và triển khai API.
- **Chương 5:** Thực nghiệm E0–E3 và bảng kết quả.
- **Chương 6:** Thảo luận.
- **Chương 7:** Kết luận và hướng phát triển.

---

# CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ TỔNG QUAN NGHIÊN CỨU

## 2.1. Phát hiện rác và ô nhiễm bằng deep learning

**TACO** (Trash Annotations in Context) cung cấp annotation rác ở cấp instance trên cảnh đường phố toàn cầu. Các mô hình **YOLO** trên nền tảng Roboflow thường nhắm vào một lớp rác generic. Ít công trình gộp đồng thời **TRASH và WATER** trong một detector được fine-tune cho **ảnh báo cáo công dân Việt Nam**.

Thí nghiệm E0/E1 của đồ án định lượng khoảng cách domain: YOLOv8n-COCO (E0) thất bại (mAP@0.5 = 0,0001); fine-tune (E1) đạt 0,684 trên cùng tập test 207 ảnh.

## 2.2. Phân loại cảnh nước ô nhiễm

Classifier cấp ảnh dự đoán nước ô nhiễm mà không localize đối tượng. Dùng đơn lẻ, chúng thiếu bbox phục vụ báo cáo vận hành. GreenLens dùng xác suất scene **chỉ để bổ sung** cho YOLO, với safeguard: scene không thêm WATER khi `raw_detector_boxes == 0`.

## 2.3. Detect-then-classify cho phân loại rác

**TrashNet** và các dataset tương tự tập trung **phân loại cấp ảnh** (ví dụ 6 lớp tái chế). GreenLens triển khai **detect-then-classify**: YOLO localize TRASH, EfficientNet-B0 phân loại **patch crop** (+4 px pad) thành 7 subtype, gộp kết quả theo ảnh trong response API.

## 2.4. AI môi trường và báo cáo cộng đồng tại Việt Nam

Nền tảng citizen science tại Việt Nam ngày càng dựa vào ảnh mobile. Hiếm hệ thống công bố kết hợp **detection 2 lớp**, **fusion ổn định WATER**, **nhãn rác chi tiết** và **REST API deployable** với chính sách human-in-the-loop trong một pipeline.

## 2.5. So sánh với các hướng tiếp cận liên quan

**Bảng 2.1 — So sánh định tính với công trình liên quan**

| Công trình | Phương pháp | Bối cảnh / dataset | Metric (literature) | So với GreenLens |
|------------|-------------|-------------------|---------------------|------------------|
| TACO | Instance seg / detect | Rác đường phố toàn cầu | mAP (tùy split) | GreenLens: + WATER + VN + API + 7 subtype |
| TrashNet | Image classification | 6 lớp tái chế | Accuracy | GreenLens: bbox + pipeline end-to-end |
| YOLO litter (Roboflow) | Single-class detect | Rác generic | mAP | GreenLens: 2 lớp TRASH+WATER |
| YOLOv8n-COCO | Pretrained | 80 lớp COCO | — | E0 trên test ta: mAP@0.5 = 0,0001 |
| **GreenLens-Full (Ours)** | Hybrid YOLO+scene+subtype | Benchmark VN merged | mAP@0.5 = **0,684** (detect) | **★ Đề xuất** |

> Số “nổi trội” chính thức lấy từ **cùng test set nội bộ** (E0–E3). Công trình nhóm B dùng cho Related Work, không ép mAP khác dataset vào Bảng IV.

---

# CHƯƠNG 3. DỮ LIỆU VÀ THIẾT LẬP THÍ NGHIỆM

## 3.1. Nguồn dữ liệu

| Nguồn | Mô tả |
|-------|-------|
| **Roboflow** | Dự án pollution/litter công khai, gộp qua API `merge-zips` |
| **Việt Nam** | Ảnh tự chụp / phong cách citizen-report, tự gán nhãn |
| **Kaggle** | `pollution-merge-vn-nation` — `/kaggle/input/datasets/hulphc/pollution-merge-vn-nation` |
| **Local (E0)** | `D:\CapsoneProject\DATASETFINAL\TOTAL\datasetfinal` |

Định dạng: YOLO — `images/{split}`, `labels/{split}`; nhãn chuẩn hóa; `0 = TRASH`, `1 = WATER`.

## 3.2. Thống kê tập detection

**Bảng 3.1 — Thống kê dataset phát hiện (Bảng I paper)**

| Hạng mục | Train | Val | Test | **Tổng** |
|----------|-------|-----|------|----------|
| **Số ảnh** | 1.147 | 244 | 207 | **1.598** |
| **Tỷ lệ** | 71,8% | 15,3% | 12,9% | 100% |
| **Bbox (mọi split)** | — | — | — | **~4.462** |
| Bbox TRASH | — | — | — | **~3.061** |
| Bbox WATER | — | — | — | **~1.401** |

| Metadata | Giá trị |
|----------|---------|
| Lớp detection | **TRASH (0), WATER (1)** |
| File nhãn rỗng | **~43** (~2,7% — background / hard negative) |
| Chính sách split | ~70/15/15 |
| Khóa test | **207 ảnh** — chỉ dùng báo số, không tune |

**Bảng 3.2 — Phân tích tập test (log eval E1, Ultralytics)**

| Phân vùng | Ảnh | Instance | Ảnh nền (background) |
|-----------|-----|----------|----------------------|
| **Test (tổng)** | **207** | **240** | **5** |
| Test — TRASH | 101 | 124 | — |
| Test — WATER | 101 | 116 | — |

### Kiểm soát chất lượng nhãn

- Công cụ dashboard: `inspect`, `preview-labels`, `filter-classes`, `merge-zips`.
- Script xác minh: `ml/training/scripts/verify_yolo_dataset.py` (`--nc 2`).

## 3.3. Dữ liệu scene và subtype

### Scene (E2) — chưa hoàn tất

**Production:** 2 lớp `WATER`, `NEGATIVE` (`app/core/scene_classifier.py`).

| Hạng mục | Giá trị | Ghi chú |
|----------|---------|---------|
| Lần train gần nhất | Job `scj_7b29e8f783` | **Thất bại epoch 1** (UnicodeEncodeError Windows) |
| Ảnh trước split | 170 (146 train + 24 val auto) | Log dashboard |
| Lớp zip cũ | NEGATIVE, SMOKE, WATER | Legacy 3-class |
| **Mục tiêu** | WATER + NEGATIVE | Bỏ SMOKE |
| Weight | **Chưa có** `scene_classifier.pt` | Cần rebuild + train |

### Subtype (E3) — chưa có dataset đầy đủ

**7 lớp:** CONSTRUCTION, ELECTRONIC, HAZARDOUS, HOUSEHOLD, MEDICAL, ORGANIC, RECYCLABLE.

Upload qua `POST /api/v1/training/subtype/datasets/merge-zips`. Gợi ý nguồn: TACO, TrashNet/Roboflow, Kaggle garbage classification (`docs/TRASH_SUBTYPE_GUIDE.md`).

## 3.4. Cấu hình huấn luyện E1

**Bảng 3.3 — Hyperparameter huấn luyện detector**

| Tham số | Giá trị |
|---------|---------|
| Model khởi tạo | `yolov8n.pt` |
| Epochs | 150 |
| Kích thước ảnh | 1280 |
| Batch | 8 |
| Seed | 42 |
| Patience | 30 |
| AMP | True |
| Phần cứng | Kaggle **Tesla T4** |
| Thời gian train | **~2,6 giờ** (~9.339 s) |
| Framework | Ultralytics **8.4.61**, PyTorch 2.10+cu128 |

---

# CHƯƠNG 4. THIẾT KẾ VÀ TRIỂN KHAI HỆ THỐNG GREENLENS

## 4.1. Kiến trúc tổng quan

**Hình 4.1 — Sơ đồ pipeline GreenLens** _(vẽ từ mô tả dưới; chèn ảnh khi export Word)_

```text
Ảnh đầu vào (RGB, tối đa 20 MB)
    │
    ├─► [Song song] YOLOv8n ──► bbox TRASH / WATER (imgsz=1280)
    │         │
    │         └─► Nếu có bbox TRASH & model subtype loaded:
    │               crop (+4px pad) ──► EfficientNet-B0 ──► 7 subtype
    │
    └─► [Song song] EfficientNet-B0 scene ──► P(WATER)
              │
              ▼
         Fusion + Safeguard (_merge_yolo_and_scene)
              │
              ▼
         Severity + Image relevance + HITL
              │
              ▼
         JSON ClassifyResponse (FastAPI)
```

**Mã nguồn chính:** `app/core/pollution_classifier.py` — lớp `PollutionClassifier`.

## 4.2. Tầng phát hiện YOLOv8n (E1)

| Tham số | Giá trị |
|---------|---------|
| Lớp | TRASH, WATER |
| Inference imgsz | 1280 |
| Weights | `ml/weights/best.pt` |
| Đồng nghĩa nhãn | GARBAGE/WASTE→TRASH; SEWAGE→WATER |
| Coverage ratio | Tổng diện tích bbox / diện tích ảnh, clamp ≤ 1 |

## 4.3. Tầng scene và fusion (E2)

| Tham số | Giá trị |
|---------|---------|
| Kiến trúc | EfficientNet-B0 |
| Lớp inference | WATER, NEGATIVE |
| Tiền xử lý | Resize 256, CenterCrop 224, chuẩn hóa ImageNet |
| Ngưỡng fusion τ | **0,45** |
| Huấn luyện mặc định | 15 epochs, batch 16, lr 1e-4, AdamW, CosineAnnealing |

**Quy tắc fusion và safeguard:**

1. Dự đoán bbox YOLO được ưu tiên theo từng lớp.
2. Scene chỉ thêm **WATER** khi `raw_detector_boxes > 0`.
3. Scene WATER yêu cầu `P(WATER) ≥ 0,45`.
4. YOLO **không** thấy box nào → scene **không** được khẳng định WATER một mình.
5. YOLO và scene chạy **song song** (`ThreadPoolExecutor`, max_workers=2).

## 4.4. Tầng phân loại subtype (E3)

| Tham số | Giá trị |
|---------|---------|
| Kiến trúc | EfficientNet-B0 |
| Số lớp | 7 subtype (mục 3.3) |
| Crop pad | +4 px |
| Ngưỡng τ | **0,40** — dưới ngưỡng → `UNKNOWN` |
| Huấn luyện mặc định | 100 epochs, batch 32, lr 1e-3 |

## 4.5. Mức độ nghiêm trọng, relevance và HITL

### Mức độ nghiêm trọng (BR-AI-003 v1)

**Bảng 4.1 — Ánh xạ coverage ratio → severity**

| Tỷ lệ phủ r | Mức độ |
|-------------|--------|
| r < 0,05 | LOW |
| 0,05 ≤ r < 0,15 | MEDIUM |
| 0,15 ≤ r < 0,40 | HIGH |
| r ≥ 0,40 | CRITICAL |

### Image relevance

| Điều kiện | Nhãn |
|-----------|------|
| ≥1 box mapped & max conf ≥ 0,30 | POLLUTION_LIKELY |
| Có raw box nhưng không map được | UNCLEAR_NEED_MANUAL_REVIEW |
| Không có raw box | NOT_POLLUTION_OR_UNRELATED |

### Human-in-the-Loop

**Bảng 4.2 — Ánh xạ confidence → hành động UI (Bảng III paper)**

| Hành động | Confidence | Giao diện |
|-----------|------------|-----------|
| AUTO_FILL | ≥ **0,80** | Tự điền form |
| SUGGEST | **0,50 – 0,80** | Gợi ý |
| KEEP_USER_CHOICE | < 0,50 | Giữ lựa chọn người dùng |

Ghi đè: `image_relevance ≠ POLLUTION_LIKELY` và không có mapped box → `KEEP_USER_CHOICE`.

## 4.6. API và triển khai

**Bảng 4.3 — Endpoint chính**

| Endpoint | Method | Chức năng |
|----------|--------|-----------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/ready` | GET | Readiness |
| `/api/v1/classify` | POST | Phân loại từ URL |
| `/api/v1/classify-upload` | POST | Upload multipart |
| `/api/v1/classify-moderation-upload` | POST | Classify + moderation |
| `/api/v1/images/normalize` | POST | Chuẩn hóa ảnh |
| `/api/v1/training/*` | * | Điều phối train |

| Giới hạn | Giá trị |
|----------|---------|
| Upload tối đa | 20 MB |
| Timeout inference | 4,5 s |
| Service | FastAPI 0.1.0, cổng 8000 |

**Moderation:** POLLUTION_LIKELY → ACCEPTABLE_REPORT_IMAGE; UNCLEAR → NEED_MANUAL_REVIEW; NOT_POLLUTION → IRRELEVANT_OR_SUSPECTED_ABUSIVE.

**Audit:** `model_version` = `{YOLO_VERSION}|scene:{SCENE_VERSION|off}`.

**Graceful degradation:** Thiếu YOLO → stub/demo; thiếu scene → `scene_classifier_active=false`; thiếu subtype → `trash_subtype_active=false`, `subtypes=null`.

---

# CHƯƠNG 5. THỰC NGHIỆM VÀ KẾT QUẢ

## 5.1. Thiết kế thí nghiệm E0–E3

**Bảng 5.1 — Thiết lập môi trường**

| Hạng mục | Giá trị |
|----------|---------|
| E0 eval | Local Windows, `run_paper_experiments.py --mode e0` |
| E1 train+eval | Kaggle Tesla T4, Ultralytics 8.4.61 |
| Python | 3.12 |
| Split đánh giá | **Chỉ test** (207 ảnh) |
| Reproducibility | seed = 42 |

**Bảng 5.2 — Thiết kế thí nghiệm**

| Mã | Hệ thống | Module | Vai trò |
|----|----------|--------|---------|
| **E0** | YOLOv8n-COCO | Pretrained only | Baseline generic |
| **E1** | FT-YOLOv8n | Detector only | Baseline detect-only mạnh |
| **E2** | GreenLens-Det | E1 + scene fusion | Ablation |
| **E3 ★** | GreenLens-Full | E2 + subtype + API | **Đề xuất** |

**Metric sử dụng:**

- Detection: Precision, Recall, mAP@0.5, mAP@0.5:0.95
- Fusion: FP WATER trên hard negative; recall WATER trên test
- Subtype: macro-F1, F1 từng lớp
- Triển khai: `inference_time_ms`, kích thước model (MB)

## 5.2. Kết quả phát hiện (Bảng IV)

**Bảng 5.3 — Kết quả phát hiện trên tập TEST (207 ảnh)** ⭐

| Vai trò | Phương pháp | FT | TRASH P | TRASH R | TRASH mAP50 | TRASH mAP50-95 | WATER P | WATER R | WATER mAP50 | WATER mAP50-95 | ALL P | ALL R | **ALL mAP50** | **ALL mAP50-95** |
|---------|-------------|----|---------|---------|-------------|----------------|---------|---------|-------------|----------------|-------|-------|---------------|------------------|
| Baseline | E0 YOLOv8n-COCO | Không | 0,0023 | 0,0081 | 0,0001 | 0,0001 | 0,0 | 0,0 | 0,0 | 0,0 | 0,0012 | 0,004 | **0,0001** | **0,0** |
| Baseline FT | E1 FT-YOLOv8n | Có | 0,628 | 0,685 | **0,654** | **0,319** | 0,658 | 0,729 | **0,713** | **0,414** | 0,643 | 0,707 | **0,684** | **0,367** |
| Ours | E2 GreenLens-Det | Có | = E1 | = E1 | = E1 | = E1 | — | — | Bảng V | = E1 | — | — | = E1 | = E1 |
| **Ours ★** | **E3 GreenLens-Full** | Có | = E1 | = E1 | = E1 | = E1 | — | — | Bảng V | = E1 | — | — | = E1 | = E1 |

**Nguồn số:** E0 — `ml/paper_output/paper_metrics.json` (2026-06-07). E1 — Kaggle Commit val test (2026-06-08).

**ΔmAP@0.5 (E1 − E0):** **+0,6839** tuyệt đối.

**Kết luận thí nghiệm 5.2:**

1. Fine-tune domain **bắt buộc** cho phát hiện ô nhiễm ảnh VN (E0 ≈ 0 → E1 = 0,684).
2. E3 tái sử dụng weight E1; lợi thế E3 nằm ở fusion và subtype (Bảng V, VI), không phải train detector riêng.

## 5.3. Kết quả fusion WATER (Bảng V) — *đang thực hiện*

**Bảng 5.4 — Ổn định WATER / false positive**

| Cấu hình | Module | FP WATER / N hard-neg | Recall WATER / N test-WATER | Trạng thái |
|----------|--------|----------------------|----------------------------|------------|
| E1 | YOLO only | — | — | Chưa chạy eval |
| E2/E3 | YOLO + scene (τ=0,45) | — | — | Chờ `scene_classifier.pt` |

**Giao thức đề xuất:** N ≈ 30–50 ảnh NEGATIVE; đếm dự đoán WATER; so E1 (scene off) vs E3 (scene on).

## 5.4. Kết quả subtype (Bảng VI) — *đang thực hiện*

**Bảng 5.5 — F1 phân loại subtype**

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

## 5.5. Triển khai và hiệu năng

**Bảng 5.6 — Thông số triển khai (Bảng VII)**

| Thành phần | Tham số / kích thước | Độ trễ |
|------------|---------------------|--------|
| YOLOv8n `best.pt` | ~3,0M params, ~6–7 MB | ~10,6 ms/ảnh infer (T4, log E1) |
| Scene EfficientNet-B0 | ~5,3M params, ~16 MB | Song song với YOLO |
| Subtype EfficientNet-B0 | ~5,3M params | Theo từng bbox TRASH |
| **Pipeline API đầy đủ** | — | Chưa benchmark end-to-end |

**Bảng 5.7 — Trạng thái hình minh họa**

| Hình | Nội dung | Trạng thái |
|------|----------|------------|
| Hình 4.1 | Pipeline tổng quan | ✅ Có sơ đồ text |
| Hình 5.1 | Learning curve E1 | ✅ Có `results.csv` Kaggle |
| Hình 5.2 | Confusion subtype | ⬜ Sau train subtype |
| Hình 5.3–5.4 | Qualitative bbox | ✅ Có `best.pt` |
| Hình 5.5 | Cột E0 vs E1 mAP50 | ✅ Từ Bảng 5.3 |

---

# CHƯƠNG 6. THẢO LUẬN

## 6.1. Khoảng cách domain E0 → E1

YOLOv8n pretrained COCO **gần như thất bại** trên TRASH/WATER ảnh báo cáo VN (ALL mAP@0.5 = 0,0001). Fine-tune nâng lên **0,684** (cải thiện tuyệt đối +0,6839), củng cố đóng góp C1.

## 6.2. Vì sao cần pipeline lai E3 thay vì chỉ E1

E1 đã mạnh (WATER mAP@0.5 **0,713** > TRASH **0,654**). GreenLens bổ sung:

- Fusion scene có safeguard — giảm FP WATER trên cảnh mơ hồ.
- 7 nhãn subtype trên crop TRASH — phục vụ điều phối xử lý.
- Lớp API: severity, relevance, HITL — không có ở detect-only.

Số định lượng FP và F1 chờ Bảng 5.4, 5.5.

## 6.3. WATER mAP cao hơn TRASH trên test

Dù số ảnh test TRASH và WATER cân bằng (101 vs 101), WATER mAP@0.5 (0,713) vượt TRASH (0,654). Nguyên nhân có thể: kích thước bbox, đặc trưng lớp, độ nhất quán nhãn. Fusion E3 nhắm **ổn định** quyết định WATER, không nhất thiết tăng mAP.

## 6.4. Ghi chú triển khai

- Production detection: **2 lớp** TRASH/WATER — không dùng số liệu legacy 3-class SMOKE.
- Script train scene còn liệt kê SMOKE; **inference** chỉ WATER/NEGATIVE.
- Windows: đặt `PYTHONUTF8=1` khi train scene (tránh lỗi encoding log).

## 6.5. Hạn chế

- Một benchmark nội bộ (1.598 ảnh).
- Thí nghiệm scene/subtype chưa hoàn tất.
- Chưa benchmark TFLite mobile.
- Chưa tách thống kê Roboflow vs VN theo nguồn.

---

# CHƯƠNG 7. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

## 7.1. Kết luận

Đồ án đã xây dựng **GreenLens** — pipeline lai có thể triển khai: YOLOv8n fine-tune TRASH/WATER, EfficientNet-B0 scene fusion có safeguard, phân loại 7 subtype trên vùng TRASH, và microservice FastAPI với severity và HITL.

Trên tập test **207 ảnh khóa**, E1 đạt **mAP@0.5 = 0,684** so với E0 **0,0001**, chứng minh fine-tune domain là **thiết yếu**. GreenLens-Full (E3) mở rộng E1 bằng fusion và subtype hướng tới ưu thế vận hành so với baseline detect-only — **xác thực định lượng FP và F1** sẽ hoàn thiện sau train scene/subtype.

## 7.2. Hướng phát triển

1. Rebuild dataset scene (WATER/NEGATIVE) và train `scene_classifier.pt`.
2. Thu thập dataset subtype, train `trash_subtype_classifier.pt`, đo Bảng 5.5.
3. Đo FP WATER (Bảng 5.4) và latency pipeline API đầy đủ.
4. Export TFLite cho inference on-device.
5. Bổ sung thống kê nguồn Roboflow vs VN; hoàn thiện hình qualitative và learning curve cho phụ lục nộp.

---

# TÀI LIỆU THAM KHẢO

_[Điền theo chuẩn trích dẫn của trường — gợi ý:]_

1. TACO Dataset — Trash Annotations in Context.
2. TrashNet — Garbage Classification Dataset.
3. Ultralytics YOLOv8 Documentation.
4. Tan, M. et al. — EfficientNet.
5. FastAPI Documentation.
6. Roboflow — Open pollution/litter datasets.
7. _[Thêm paper scene water pollution, citizen science VN…]_

---

# PHỤ LỤC

## Phụ lục A — Hyperparameter tóm tắt

```
YOLO E1:    yolov8n.pt | epochs=150 | imgsz=1280 | batch=8 | seed=42 | patience=30
Scene:      epochs=15 | batch=16 | lr=1e-4 | AdamW | CosineAnnealing | threshold=0.45
Subtype:    epochs=100 | batch=32 | lr=1e-3 | threshold=0.40 | crop_pad=4px
API:        AUTO_FILL≥0.80 | SUGGEST≥0.50 | RELEVANCE_MIN=0.30 | TIMEOUT=4.5s | MAX=20MB
```

## Phụ lục B — Ví dụ response API

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

## Phụ lục C — Lệnh reproduce thí nghiệm

**E0 (local):**
```cmd
uv run python ml\training\kaggle\run_paper_experiments.py --mode e0 ^
  --dataset-dir "D:\CapsoneProject\DATASETFINAL\TOTAL\datasetfinal" ^
  --output-dir "ml\paper_output" --imgsz 1280
```

**E1 (Kaggle — đã chạy thành công):**
- Cell 1: `pip install ultralytics`
- Cell 2: train YOLOv8n 150 epochs + val test → `paper_output/E1/best.pt`

**Scene (sau khi có data):**
```cmd
set PYTHONUTF8=1
uv run python ml\training\train_scene_classifier.py --data-root ml\training\data\scene --epochs 20
```

**Subtype (sau khi có data):**
```cmd
uv run python ml\training\train_trash_subtype_classifier.py --data-root ml\training\data\trash_subtype --epochs 100
```

## Phụ lục D — Ánh xạ file nguồn

| File trong repo | Vai trò trong báo cáo |
|-----------------|----------------------|
| `docs/paper/GREENLENS_PAPER_DRAFT_FROM_CODE_VI.md` | Draft bài báo / nguồn số |
| `docs/paper/BAO_CAO_DO_AN_GREENLENS_VI.md` | **Báo cáo này** |
| `ml/paper_output/BANG_IV.md` | Bảng IV tóm tắt |
| `ml/paper_output/paper_metrics.json` | Chi tiết E0 |
| `app/core/pollution_classifier.py` | Pipeline inference |
| `docs/TRASH_SUBTYPE_GUIDE.md` | Hướng dẫn subtype |

---

<div align="center">

**— Hết báo cáo —**

_Biên soạn từ source code và thí nghiệm GreenLens · Phiên bản 1.0 · 2026-06-08_

</div>

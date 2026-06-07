# Hướng dẫn cập nhật Google Doc — Phân loại từng loại rác (Trash Subtype)

Tài liệu này **không** sửa Google Doc giúp bạn. Nó chỉ rõ **sửa ở đâu**, **thay/chèn gì**, và cung cấp **đoạn văn dán sẵn** để bổ sung nội dung *fine-grained waste classification* cho bài báo GreenLens, khớp với codebase (`app/core/trash_subtype_classifier.py`, pipeline trong `pollution_classifier.py`).

**Google Doc của bạn:**
https://docs.google.com/document/d/1G0SYeWUOVvyllbMDqOagtoYV7e8yR3DM_5XMX7UXAPg/edit

**Nguyên tắc IEEE:** Mọi số liệu chưa chốt dùng placeholder `TBD_*` — không điền số giả.

**Bảy lớp rác trong hệ thống (mã hóa API):**
`RECYCLABLE` | `ORGANIC` | `MEDICAL` | `ELECTRONIC` | `CONSTRUCTION` | `HAZARDOUS` | `HOUSEHOLD`

**Pipeline (tóm tắt cho paper):**
Ảnh → YOLOv8n (TRASH / WATER / SMOKE) → nếu có bbox TRASH → crop (+4 px padding) → EfficientNet-B0 (subtype) → gộp `subtypes` theo số bbox và confidence cao nhất mỗi lớp. Chưa có file trọng số: API vẫn chạy, `trash_subtype_active=false`.

---

## Bản đồ nhanh — Sửa ở đâu?

| # | Vị trí trong Doc | Hành động | Mục đích |
|---|------------------|-----------|----------|
| 1 | **Abstract** | Thay cả đoạn | Nêu pipeline 2 giai đoạn + 7 lớp rác |
| 2 | **Keywords** | Thêm 2 từ khóa | Fine-grained, two-stage |
| 3 | **§1.2** (sau đoạn Trash detection) | **Chèn** đoạn mới | Bối cảnh classify-waste |
| 4 | **§1.3** | Đổi “bốn”→“năm”; **chèn Gap 5** | Khoảng trống phân loại chi tiết |
| 5 | **§1.4** | Sửa Đóng góp 2; **chèn Đóng góp 5** | Đóng góp subtype |
| 6 | **§1.5** | Sửa 1 câu | Nhắc mục 3.6, 4.6, 5.5 |
| 7 | **§3.1** | Thay `___ ảnh` | Placeholder số ảnh global |
| 8 | **§3.3** | Thay tiêu đề trống / điền nội dung | Quy trình gán nhãn YOLO |
| 9 | **Sau §3.5** | **Thêm mục 3.6** + **Bảng II** | Dataset subtype |
| 10 | **§4** (đầu + §4.1) | Sửa đầu ra + thành phần kiến trúc | Subtype là thành phần thứ 3 |
| 11 | **Sau §4.5** | **Thêm mục 4.6** | Mô tả Trash Subtype Classifier |
| 12 | **§5** | Thêm **5.5** (và đánh số lại nếu cần) | Thí nghiệm + Bảng VI |
| 13 | **§6.2, 6.4, 6.5** | Bổ sung bullet | Hạn chế subtype |
| 14 | **§7** | Sửa kết luận | Năm đóng góp + TBD kết quả |
| 15 | **Hình / bảng** | Thêm Hình pipeline 2 stage | Minh họa |

---

## 1. Abstract

**Tìm:** đoạn Abstract hiện tại (bắt đầu bằng *Vấn đề: thiếu hệ thống giám sát…*).

**Thay toàn bộ bằng:**

```
Vấn đề: thiếu hệ thống giám sát ô nhiễm tự động đa lớp tại Việt Nam trong khi các bộ dữ liệu và mô hình hiện có chủ yếu được xây dựng cho bối cảnh phương Tây; đồng thời hầu hết hệ thống chỉ trả nhãn TRASH chung, thiếu thông tin loại rác cho thu gom và xử lý. Phương pháp: kiến trúc lai kết hợp YOLOv8n cho phát hiện ba lớp ô nhiễm (TRASH, WATER, SMOKE), EfficientNet-B0 cho phân loại cảnh (WATER/SMOKE) có fusion safeguard, và EfficientNet-B0 thứ hai trên vùng cắt TRASH để phân loại bảy loại rác con; fine-tune theo chiến lược hai pha trên dữ liệu toàn cầu và 500 ảnh Việt Nam. Kết quả: mAP@0.5 phát hiện ô nhiễm đạt TBD_mAP50; macro-F1 phân loại loại rác đạt TBD_macroF1 (Bảng VI). Ý nghĩa: nền tảng citizen reporting có thông tin vận hành (loại rác cụ thể) tại đô thị Việt Nam.
```

**Keywords — thêm vào cuối dòng Keywords (nếu chưa có):**

```
Fine-Grained Waste Classification, Two-Stage Pipeline
```

---

## 2. Mục 1.2 — Phân loại chi tiết loại rác

**Vị trí:** Ngay **sau** đoạn *Phát hiện rác thải (Trash detection)* (kết thúc câu về Majchrowska [17]), **trước** *Nhận diện ô nhiễm nước*.

**Chèn đoạn mới (tiêu đề in đậm tùy format Doc):**

```
Phân loại chi tiết loại rác (Fine-grained waste classification). TrashNet [16] và TACO [9] hỗ trợ benchmark classify-waste tách khỏi phát hiện đa ô nhiễm (nước, khói). Huấn luyện một detector gán bbox cho từng subclass đòi hỏi khối lượng nhãn lớn; tiếp cận detect-then-classify — phát hiện TRASH rồi phân loại trên crop — giảm chi phí annotation và phù hợp triển khai API trả về danh sách subtypes theo từng vùng rác trong ảnh.
```

---

## 3. Mục 1.3 — Gap 5

**Bước A:** Đổi câu mở đầu:

- **Tìm:** `bốn khoảng trống chính`
- **Thay:** `năm khoảng trống chính`

**Bước B:** **Sau** đoạn **Gap 4** (Deployment gap), **trước** tiêu đề **1.4 Đóng góp**, chèn:

```
Gap 5 — Khoảng trống phân loại chi tiết rác (Fine-grained waste gap). Các hệ thống giám sát đa lớp thường dừng ở nhãn TRASH chung, không cung cấp thông tin loại rác (y tế, nguy hại, tái chế, xây dựng, v.v.) cần cho điều phối thu gom và xử lý tại Việt Nam. Các benchmark classify-waste [17] hiếm khi được tích hợp end-to-end với phát hiện WATER/SMOKE trong cùng một sản phẩm triển khai.
```

---

## 4. Mục 1.4 — Đóng góp 5 và sửa Đóng góp 2

**Bước A:** Đổi câu mở đầu 1.4: `bốn khoảng trống` → `năm khoảng trống`.

**Bước B:** Trong **Đóng góp 2**, thêm vào cuối câu mô tả kiến trúc lai (sau EfficientNet-B0 scene):

```
; đồng thời tích hợp mô-đun EfficientNet-B0 thứ hai phân loại bảy loại rác trên vùng cắt TRASH sau khi YOLO định vị.
```

**Bước C:** **Sau** **Đóng góp 4**, chèn:

```
Đóng góp 5 (Lấp Gap 5) — Pipeline hai giai đoạn phân loại loại rác. Sau khi YOLOv8n xác định bbox TRASH, mô-đun Trash Subtype Classifier (EfficientNet-B0) phân loại từng crop thành bảy lớp: RECYCLABLE, ORGANIC, MEDICAL, ELECTRONIC, CONSTRUCTION, HAZARDOUS, HOUSEHOLD; kết quả được gộp theo tần suất xuất hiện và confidence cao nhất mỗi lớp (trường subtypes trong API). Hệ thống hỗ trợ graceful degradation: khi chưa có trọng số huấn luyện subtype, API vẫn trả phát hiện TRASH/WATER/SMOKE như trước.
```

---

## 5. Mục 1.5 — Cấu trúc bài báo

**Tìm** câu liệt kê Mục 3, 4, 5. **Thêm** (hoặc thay câu tương ứng):

```
Mục 3 mô tả bộ dữ liệu, gồm Mục 3.6 về dữ liệu phân loại loại rác. Mục 4 trình bày kiến trúc và phương pháp, gồm Mục 4.6 về mô-đun subtype. Mục 5 báo cáo thực nghiệm, gồm Mục 5.5 về metric phân loại loại rác.
```

---

## 6. Mục 3 — Dữ liệu

### 3.1

**Tìm:** `___ ảnh` (Phase 1 — Dữ liệu toàn cầu)
**Thay:** `[TBD_N_global] ảnh`

### 3.3 — Quy trình gán nhãn

Nếu mục 3.3 đang trống hoặc chỉ có tiêu đề, **dán:**

```
3.3 Quy trình gán nhãn
Ảnh ô nhiễm đa lớp được gán nhãn bounding box theo định dạng YOLO (class_id, tọa độ chuẩn hóa). Lớp TRASH gắn với vùng rác rời rạc; WATER và SMOKE theo hướng dẫn thống nhất trong nhóm annotator. Kiểm tra chéo TBD_% mẫu trên tập validation. Xung đột nhãn do annotator cấp cao xử lý.
```

### 3.4 — Ghi chú augmentation (thêm 1 đoạn cuối mục)

**Chèn cuối §3.4:**

```
Đối với bộ dữ liệu phân loại loại rác (Mục 3.6), augmentation gồm RandomHorizontalFlip, RandomRotation (±15°), ColorJitter và RandomResizedCrop; tập validation và test chỉ resize và chuẩn hóa theo thống kê ImageNet.
```

### 3.6 — MỤC MỚI (sau 3.5)

**Chèn toàn bộ mục mới:**

```
3.6 Bộ dữ liệu phân loại loại rác (Trash Subtype Dataset)

Khác với Stage 1 (YOLO), bộ subtype không yêu cầu bounding box: ảnh được tổ chức theo ImageFolder images/{train|val|test}/{class}/.

Bảy lớp (thống nhất với triển khai GreenLens): RECYCLABLE (chai PET, lon, carton), ORGANIC (thức ăn, rau củ), MEDICAL (khẩu trang, kim tiêm — ưu tiên bối cảnh Việt Nam), ELECTRONIC (thiết bị điện tử), CONSTRUCTION (gạch, xi măng), HAZARDOUS (pin, hóa chất), HOUSEHOLD (rác sinh hoạt hỗn hợp, túi nilon).

Nguồn ảnh: TACO [9], TrashNet [16], các tập phân loại công khai (Kaggle/Roboflow), và ảnh tự thu tại Việt Nam. Phân chia train/validation/test theo tỉ lệ 70/15/15, stratified theo lớp; tập test khóa trước khi huấn luyện cuối.

Bảng II. PHÂN BỐ ẢNH THEO LỚP SUBTYPE (ĐIỀN SAU KHI GOM DỮ LIỆU)

Lớp          | Train | Val | Test | Ghi chú
RECYCLABLE    | TBD   | TBD | TBD  |
ORGANIC       | TBD   | TBD | TBD  |
MEDICAL       | TBD   | TBD | TBD  |
ELECTRONIC    | TBD   | TBD | TBD  |
CONSTRUCTION  | TBD   | TBD | TBD  |
HAZARDOUS     | TBD   | TBD | TBD  |
HOUSEHOLD     | TBD   | TBD | TBD  |
TOTAL         | TBD   | TBD | TBD  | Mục tiêu ~2.000–3.000 ảnh
```

*(Trong Google Doc: tạo bảng 4 cột thay vì markdown.)*

---

## 7. Mục 4 — Phương pháp

### Đoạn mở đầu Mục 4

**Tìm** đoạn giới thiệu đầu ra hệ thống. **Bổ sung** đầu ra thứ (v):

```
Hệ thống GreenLens nhận ảnh RGB đầu vào và trả về: (i) lớp ô nhiễm chính (TRASH / WATER / SMOKE), (ii) độ tin cậy, (iii) mức độ nghiêm trọng (severity), (iv) gợi ý Human-in-the-Loop, và (v) danh sách subtypes — chỉ khi phát hiện TRASH và mô hình subtype đã được nạp trọng số.
```

### 4.1 — Tổng quan kiến trúc

**Tìm:** liệt kê “bốn thành phần” → đổi **năm thành phần**, thêm bullet:

```
• Mô-đun phân loại loại rác (Trash Subtype Classifier): EfficientNet-B0 trên crop từng bbox TRASH, đầu ra bảy lớp con.
```

**Gợi ý Hình 1:** Vẽ sơ đồ: Input → YOLO → (TRASH?) → Crop → EfficientNet subtype → Aggregate subtypes; nhánh WATER/SMOKE → EfficientNet scene → Fusion safeguard.

### 4.6 — MỤC MỚI (sau 4.5, trước mục tiếp theo nếu có)

```
4.6 Mô-đun phân loại loại rác (Trash Subtype Classifier)

Mô-đun chỉ kích hoạt khi (1) YOLO trả về ít nhất một bounding box lớp TRASH và (2) file trọng số EfficientNet-B0 subtype đã được nạp (cấu hình triển khai).

Với mỗi bbox TRASH: cắt vùng ảnh có bù đắp 4 pixel quanh hộp (padding) để giữ ngữ cảnh; resize 224×224; chuẩn hóa theo mean/std ImageNet; suy luận EfficientNet-B0; softmax trên bảy lớp. Ngưỡng τ_subtype = 0,40: nếu confidence dưới ngưỡng, gán UNKNOWN cho bbox đó.

Gộp cấp ảnh: đếm số bbox theo từng subtype; với mỗi lớp, lưu confidence cao nhất trong các bbox cùng lớp. API trả trường subtypes dạng [{subtype, count, confidence}, …].

Khi chưa huấn luyện hoặc chưa cấu hình đường dẫn trọng số, trash_subtype_active = false; pipeline Stage 1 và fusion scene vẫn hoạt động bình thường (graceful degradation).

Lý do hai giai đoạn: giảm chi phí gán nhãn bbox cho từng subclass so với huấn luyện YOLO đa lớp thống nhất; tách dataset ImageFolder cho subtype khỏi dataset YOLO đa ô nhiễm.
```

---

## 8. Mục 5 — Thực nghiệm (phần subtype)

Giữ nguyên **5.1–5.4** (YOLO, scene, ablation VN) nếu đã viết. **Thêm** (hoặc đổi số mục cũ “5.5 định tính” thành **5.6** nếu trùng):

```
5.5 Thí nghiệm phân loại loại rác (Trash Subtype)

Thiết lập. Backbone EfficientNet-B0, transfer learning ImageNet; đầu ra 7 lớp (Mục 3.6). Siêu tham số huấn luyện: TBD_epochs epoch, batch TBD_batch, optimizer AdamW, learning rate TBD_lr (điền sau khi chạy script train trong repository).

Metric. Accuracy, macro-F1, weighted-F1 trên tập test khóa; ma trận nhầm lẫn 7×7 (Hình TBD — heatmap). Báo cáo riêng cho lớp MEDICAL và HOUSEHOLD do dễ nhầm với RECYCLABLE/ORGANIC.

Baseline. (a) Chỉ nhãn TRASH từ YOLO, không subtype. (b) Tùy chọn: classify toàn ảnh (không crop bbox) — so sánh để chứng minh lợi ích detect-then-classify.

Kết quả. Macro-F1 = TBD_macroF1; accuracy = TBD_subtype_acc (Bảng VI). Trọng số mô hình subtype: TBD — ghi rõ “đang huấn luyện” nếu chưa có số cuối.

Bảng VI. KẾT QUẢ PHÂN LOẠI LOẠI RÁC TRÊN TẬP TEST

Lớp          | Precision | Recall | F1
RECYCLABLE    | TBD       | TBD    | TBD
ORGANIC       | TBD       | TBD    | TBD
MEDICAL       | TBD       | TBD    | TBD
ELECTRONIC    | TBD       | TBD    | TBD
CONSTRUCTION  | TBD       | TBD    | TBD
HAZARDOUS     | TBD       | TBD    | TBD
HOUSEHOLD     | TBD       | TBD    | TBD
Macro avg     | TBD       | TBD    | TBD_macroF1
```

**Lưu ý:** Trong Abstract, `TBD_mAP50` là cho **YOLO** (Bảng IV / mục 5.3); `TBD_macroF1` là cho **subtype** (Bảng VI).

---

## 9. Mục 6 — Thảo luận

### 6.2 — Hạn chế mô hình

**Thêm 2 bullet:**

```
• Subtype: một bbox có thể chứa hỗn hợp nhiều loại rác — mô hình chỉ dự đoán top-1 trên crop, có thể sai lệch.
• ORGANIC và RECYCLABLE dễ nhầm; HOUSEHOLD chồng lấp đặc trưng với cả hai lớp trên.
```

### 6.4 — Phạm vi lớp

**Sửa / thêm** (nếu có câu “chỉ ba lớp”):

```
Hệ thống hỗ trợ ba lớp ô nhiễm chính (TRASH, WATER, SMOKE) và bảy lớp rác con khi mô-đun subtype được kích hoạt. Lớp hóa chất phân tán (CHEMICAL) chưa nằm trong taxonomy hiện tại.
```

### 6.5 — Hướng phát triển

**Thay hoặc bổ sung** (tránh trùng “mở rộng số lớp rác” chung chung):

```
Hướng tương lai: phân loại multi-label trên crop; mở rộng dữ liệu HOUSEHOLD tại Việt Nam; tích hợp video/stream; đồng bộ nhãn subtype với báo cáo citizen trên app.
```

---

## 10. Mục 7 — Kết luận

**Bổ sung** (cuối đoạn kết luận):

```
Bài báo đóng góp năm hạng mục, trong đó đóng góp mới về pipeline hai giai đoạn phân loại bảy loại rác trên vùng TRASH phục vụ vận hành thu gom. Kết quả định lượng: mAP@0.5 phát hiện TBD_mAP50; macro-F1 subtype TBD_macroF1 — sẽ cập nhật sau khi hoàn tất huấn luyện và đánh giá trên tập test khóa.
```

---

## 11. Bảng và hình — Chú thích IEEE (thống nhất số bảng)

| Bảng | Mục | Nội dung |
|------|-----|----------|
| I | 3.2 | Phân bố ảnh TRASH/WATER/SMOKE (YOLO) |
| II | 3.6 | Phân bố ảnh 7 lớp subtype |
| III | 4.4 | HITL confidence → UI |
| IV | 5.3 | Metric YOLO test |
| V | 5.4.1 | Ablation dữ liệu Việt Nam |
| VI | 5.5 | Metric subtype (Precision/Recall/F1) |

**Hình đề xuất thêm:** Pipeline hai giai đoạn (YOLO + subtype + fusion) — đặt Mục 4.1.

---

## 12. Checklist trước khi nộp

- [ ] Abstract và Keywords đã nhắc 7 lớp + two-stage
- [ ] Gap 5 và Đóng góp 5 có trong §1.3–1.4
- [ ] §3.6 + Bảng II (có thể để TBD)
- [ ] §4.6 (τ_subtype = 0,40; padding 4 px; graceful degradation)
- [ ] §5.5 + Bảng VI (không điền số thật nếu chưa train xong)
- [ ] §6–7 có hạn chế subtype và TBD kết quả
- [ ] Không mâu thuẫn “bốn gap” / “năm gap”
- [ ] Hình pipeline đã cập nhật (nếu Hình 1 cũ chỉ có YOLO + scene)

---

## 13. Tra cứu kỹ thuật trong repo (không cần đưa vào paper)

| Nội dung paper | File tham chiếu |
|----------------|-----------------|
| 7 lớp, crop, threshold | `app/core/trash_subtype_classifier.py` |
| Gộp subtypes, `trash_subtype_active` | `app/core/pollution_classifier.py` |
| API response | `app/models/classify.py` |
| Train subtype, dataset ZIP | `ml/training/train_trash_subtype_classifier.py`, `docs/TRASH_SUBTYPE_GUIDE.md` |
| Trạng thái triển khai | `docs/IMPLEMENTATION_STATUS.md` |

---

## 14. Thứ tự làm việc gợi ý (30–60 phút)

1. Abstract + Keywords
2. §1.2 → §1.3 (Gap 5) → §1.4 (Đóng góp 5) → §1.5
3. §3.6 + Bảng II
4. §4 (đầu + 4.1) → §4.6
5. §5.5 + Bảng VI
6. §6.2, 6.4, 6.5 → §7
7. Cập nhật Hình 1

Dùng **Ctrl+H** trong Google Doc với từng cặp “Tìm / Thay” nhỏ sẽ ít lỗi hơn dán một khối quá dài.

---

*Tài liệu tạo cho dự án greenlens-detection-ai — cập nhật khi taxonomy hoặc số lớp thay đổi trong code.*

# Patch từng mục — dán vào Google Doc (giữ hình/format cũ)

> Tìm đoạn **IN (tìm)** → thay bằng **OUT (thay)**. Placeholder `TBD_*` / `TBD` điền sau; không vượt chuẩn IEEE vì không claim số giả.

---

## Abstract — thay toàn đoạn Abstract

**OUT:**
```
Vấn đề: thiếu hệ thống giám sát ô nhiễm tự động đa lớp tại Việt Nam trong khi các bộ dữ liệu và mô hình hiện có chủ yếu được xây dựng cho bối cảnh phương Tây. Phương pháp: kiến trúc lai kết hợp YOLOv8n, EfficientNet-B0 cho phân loại cảnh (WATER/SMOKE) và EfficientNet-B0 thứ hai cho phân loại bảy loại rác trên vùng cắt TRASH, có fusion safeguard; fine-tune hai pha trên dữ liệu toàn cầu và 500 ảnh Việt Nam. Kết quả: mAP@0.5 đạt TBD_mAP50; macro-F1 phân loại loại rác đạt TBD_macroF1 (Bảng VI). Ý nghĩa: nền tảng citizen reporting có thông tin vận hành loại rác tại đô thị Việt Nam.
```

**Keywords — thêm:** `Fine-Grained Waste Classification, Two-Stage Pipeline`

---

## Sau Gap 4 (1.3) — CHÈN Gap 5

```
Gap 5 — Khoảng trống phân loại chi tiết rác (Fine-grained waste gap). Hệ thống giám sát đa lớp thường chỉ trả nhãn TRASH chung, thiếu thông tin loại rác (y tế, nguy hại, tái chế, v.v.) cho thu gom và xử lý tại Việt Nam.
```

Đổi đầu 1.3: `bốn khoảng trống` → `năm khoảng trống`

---

## Sau Đóng góp 4 (1.4) — CHÈN Đóng góp 5

```
Đóng góp 5 (Gap 5) — Pipeline hai giai đoạn phân loại loại rác. Sau YOLO định vị TRASH, EfficientNet-B0 phân loại crop thành bảy lớp (RECYCLABLE, ORGANIC, MEDICAL, ELECTRONIC, CONSTRUCTION, HAZARDOUS, HOUSEHOLD); gộp subtypes theo tần suất. Graceful degradation khi chưa có trọng số subtype.
```

Sửa Đóng góp 2: thêm `và mô-đun subtype EfficientNet-B0 thứ hai trên crop TRASH`.

---

## 1.2 — CHÈN sau đoạn Trash detection (Majchrowska [17])

```
Phân loại chi tiết loại rác. TrashNet [16] và TACO [9] hỗ trợ classify-waste tách khỏi detect đa ô nhiễm. Tiếp cận detect-then-classify trên crop giảm chi phí gán nhãn bbox cho từng subclass so với YOLO đa lớp thống nhất.
```

---

## 3.1 — thay `___ ảnh`

`[TBD_N_global] ảnh`

---

## 3.3 — thay tiêu đề trống bằng nội dung

```
Ảnh được gán nhãn bbox định dạng YOLO. TRASH: vùng rác rời rạc; WATER/SMOKE: theo guideline nhóm. Kiểm tra chéo TBD_% mẫu. Xung đột do annotator cấp cao xử lý.
```

---

## SAU 3.5 — CHÈN mục 3.6

```
3.6 Bộ dữ liệu phân loại loại rác (Trash Subtype)
Không cần bbox; ImageFolder images/{train|val|test}/{class}/. Bảy lớp: RECYCLABLE, ORGANIC, MEDICAL, ELECTRONIC, CONSTRUCTION, HAZARDOUS, HOUSEHOLD. Nguồn: TACO [9], TrashNet [16], tập công khai, ảnh tự thu VN. Split 70/15/15; test khóa trước train. Bảng II: điền Train/Val/Test khi gom xong (TBD).
```

---

## 4 (đoạn mở đầu) + 4.1

Thêm đầu ra **(v) subtypes** khi TRASH.

4.1 — đổi `bốn` → `năm` thành phần; thêm bullet:
`• Mô-đun phân loại loại rác (EfficientNet-B0 trên crop TRASH, bảy lớp).`

---

## SAU 4.5 — CHÈN 4.6

```
4.6 Mô-đun phân loại loại rác (Trash Subtype Classifier)
Khi YOLO có bbox TRASH và trọng số đã load: crop (padding 4 px) → 224×224 → EfficientNet-B0 → softmax 7 lớp; τ_subtype=0.40 (dưới ngưỡng: UNKNOWN). Gộp subtypes: count + max confidence mỗi lớp. Không có trọng số: trash_subtype_active=false, API vẫn hoạt động. Hai giai đoạn giảm annotation bbox so với detector đa subclass.
```

---

## Mục 5 — thay toàn bộ từ 5.1 đến 5.5 (giữ 5.6 nếu đổi tên từ 5.5 cũ)

Xem file `GREENLENS_IEEE_FULL_DRAFT_PASTE.txt` mục 5.1–5.6 (ngắn gọn, đủ Bảng IV–VI với TBD).

---

## 6.2 — thêm 2 bullet

```
* Subtype: vùng bbox hỗn hợp nhiều loại rác → chỉ top-1; ORGANIC/RECYCLABLE dễ nhầm.
* HOUSEHOLD chồng lấp RECYCLABLE và ORGANIC.
```

## 6.4 — sửa bullet “ba lớp”

`Ba lớp ô nhiễm chính; bảy lớp rác con khi mô hình subtype sẵn sàng. Lớp CHEMICAL chưa hỗ trợ.`

## 6.5 — xóa “Mở rộng số lớp rác” nếu trùng; thay bằng `Multi-label subtype; video.`

## 7 — thêm đóng góp (v) và TBD kết quả

`năm đóng góp`; `mAP@0.5 TBD_mAP50`; `macro-F1 subtype TBD_macroF1`.

---

## Bảng chú thích IEEE

- Bảng I: Dataset ô nhiễm (Mục 3.2)
- Bảng II: Dataset subtype (Mục 3.6)
- Bảng III: HITL (Mục 4.4)
- Bảng IV: YOLO test (Mục 5.3)
- Bảng V: Ablation VN (Mục 5.4.1)
- Bảng VI: Subtype metrics (Mục 5.5)

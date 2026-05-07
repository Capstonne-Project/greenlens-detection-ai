# Dataset ô nhiễm “thật” — combo đủ 4 lớp (không chỉ demo)

Mục tiêu: có **ảnh thật + bbox/nhãn** cho **`TRASH`, `WATER`, `SMOKE`, `CHEMICAL`** theo định dạng YOLO, trùng với `configs/pollution_data.yaml` và `app/core/pollution_classifier.py`.

Đây không phải dữ liệu mẫu kèm repo (dung lượng lớn, bản quyền) mà là **quy trình** để nhóm tự dựng combo production-like.

---

## 1. Khối lượng và chất lượng (tham chiếu `docs/AI_Service_Development_Plan.md`)

| Mức | Gợi ý / class (detection) | Ghi chú |
|-----|---------------------------|--------|
| POC đồ án | ~**200–500** ảnh có object / class (tối thiểu vài chục mỗi lớp vẫn chạy được nhưng dễ sai) | Trình bày rõ hạn chế trong báo cáo |
| Ổn định demo hội đồng | **500–2000+** ảnh / class càng tốt | Nhiều bối cảnh VN, điện thoại, blur, tối |
| Production (mục tiêu xa) | **2000+** / class, theo dõi mAP/recall từng lớp | Active learning sau khi có app |

**Negative images** (ảnh không có 4 lớp ô nhiễm): không bắt buộc cho YOLO detect thuần, nhưng **nên** có vài % để giảm báo động giả (phase sau hoặc pipeline riêng).

---

## 2. Combo 4 lớp — lấy ảnh & nguồn gợi ý (đọc license từng nguồn)

### TRASH (rác thải)

- **TACO — Trash Annotations in Context** ([dataset](https://github.com/pedropro/TACO)): nhiều subclass → map tất cả vào class **`0` TRASH**.
- **Roboflow Universe** (`litter`, `marine debris`, `illegal dumping`): chọn project có **license phù hợp** đồ án.
- **Tự chụp VN:** vỉa hè, khu tập rác, rác sông (chỉ rác → TRASH).

### WATER (nước thải)

- Từ khóa Universe: `wastewater`, `effluent`, `polluted water` — lọc license.
- **Thu thật:** cống, kênh nước đục, bọt (thống nhất khi nào là WATER vs CHEMICAL).

### SMOKE / khói

- `factory smoke`, `vehicle exhaust`, `wildfire smoke` (tránh nhầm mây — QC kỹ).
- Thu thật xa khu công nghiệp khi cho phép.

### CHEMICAL (hóa chất / thùng nguy hiểm / vệt đổ)

- `chemical spill`, `hazard barrel` (open) — thường ít ảnh; cân nhắc **oversample** và eval riêng recall.
- Không dàn cảnh nguy hiểm; dùng ảnh hiện trường hợp lý + nguồn công khai.

Một ảnh có **nhiều lớp** → nhiều dòng trong file `.txt`.

---

## 3. Cấu trúc thư mục (YOLO)

```text
ml/training/data/pollution/
  images/train/  images/val/
  labels/train/  labels/val/
```

Id: `0 TRASH`, `1 WATER`, `2 SMOKE`, `3 CHEMICAL` — xem [`README.md`](README.md).

---

## 4. Quy trình gợi ý

1. Thu ảnh (tự chụp VN + public có license).
2. Gán nhãn (CVAT / Label Studio / Roboflow) → bbox.
3. Export YOLO; nếu chỉ có **COCO instances JSON** → `scripts/coco_instances_to_yolo.py` + file map category → 0–3.
4. QC, chia train/val theo **ảnh**.
5. Kiểm tra tự động:

   ```powershell
   uv run python ml\training\scripts\verify_yolo_dataset.py --root ml\training\data\pollution
   ```

6. `uv run python ml\training\train_yolo.py`

---

## 5. Bản quyền & báo cáo

- Bảng **tên dataset — link — license**.
- Ảnh tự chụp / có người: nêu consent / che mặt.
- Không commit ảnh nhạy cảm lên Git public nếu không được phép — `ml/training/data/` đã trong `.gitignore`.

---

## NOISE (tiếng ồn)

Không train trong 4 lớp ảnh này — user chọn tay trên app; API `noise_supported: false`.

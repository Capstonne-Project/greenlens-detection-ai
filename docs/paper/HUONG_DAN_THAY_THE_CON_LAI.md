# Hoàn tất 2 phút — Ctrl+H trong Google Doc

Đã tự động thay: **Abstract kết quả (TBD)**, **Keywords**, **năm khoảng trống (1.3)**.

Mở Doc → **Ctrl+H** → lần lượt **Thay thế tất cả** (tắt regex nếu bật):

| Tìm | Thay bằng |
|-----|-----------|
| `Để giải quyết bốn khoảng trống nói trên` | `Để giải quyết năm khoảng trống nói trên` |
| `EfficientNet-B0 cho phân loại cảnh quan, có cơ chế fusion` | `EfficientNet-B0 cho phân loại cảnh (WATER/SMOKE) và EfficientNet-B0 thứ hai cho phân loại bảy loại rác trên crop TRASH, có cơ chế fusion` |
| `chưa được thảo luận trong bối cảnh giám sát ô nhiễm tại Việt Nam.` | (giữ câu) + xuống dòng + `Gap 5 — Khoảng trống phân loại chi tiết rác (Fine-grained waste gap). Hệ thống giám sát đa lớp thường chỉ trả nhãn TRASH chung, thiếu thông tin loại rác phục vụ thu gom tại Việt Nam.` |
| `khi triển khai ở các bối cảnh khác.` | (giữ) + xuống dòng + `Phân loại chi tiết loại rác. TrashNet [16] và TACO [9] hỗ trợ classify-waste; detect-then-classify trên crop giảm chi phí gán nhãn bbox.` |
| `EfficientNet-B0 [11] cho phân loại cảnh quan, tận dụng` | `EfficientNet-B0 [11] cho phân loại cảnh và mô-đun subtype trên crop TRASH, tận dụng` |
| `chưa được khám phá trong các hệ thống giám sát ô nhiễm hiện có.` | (giữ) + `Đóng góp 5 (Gap 5) — Pipeline hai giai đoạn phân loại bảy loại rác (RECYCLABLE, ORGANIC, MEDICAL, ELECTRONIC, CONSTRUCTION, HAZARDOUS, HOUSEHOLD); graceful degradation khi chưa có trọng số.` |
| `[SỐ LƯỢNG – sẽ điền sau]` | `[TBD_N_total]` |
| `gồm ___ ảnh` | `gồm [TBD_N_global] ảnh` |
| `Kiến trúc gồm bốn thành phần chính:` | `Kiến trúc gồm năm thành phần chính:` |
| `• Mô-đun ước lượng mức độ dựa trên tỉ lệ che phủ của bounding box.` | `• Mô-đun phân loại loại rác (EfficientNet-B0, bảy lớp).\n• Mô-đun ước lượng mức độ...` |
| `3.3 Quy trình gán nhãn` + dòng trống | thêm đoạn gán nhãn YOLO (xem GREENLENS_IEEE_FULL_DRAFT_PASTE.txt §3.3) |
| Sau `3.5` | chèn **§3.6** (xem file paste §3.6) |
| Sau `CRITICAL` (bảng severity) | chèn **§4.6** (xem file paste) |
| Khối `5.1`–`5.5` trống | thay bằng nội dung §5 trong `GREENLENS_IEEE_FULL_DRAFT_PASTE.txt` |
| `[CHỪA CHỖ: L1` | `Năm đóng góp... mAP@0.5 = TBD_mAP50; macro-F1 = TBD_macroF1` |

**TBD sau này:** `TBD_mAP50`, `TBD_macroF1`, `TBD_N_total`, `TBD_N_global`, `TBD_%`, `TBD_GPU`, `TBD_seed`, `TBD_ms`.

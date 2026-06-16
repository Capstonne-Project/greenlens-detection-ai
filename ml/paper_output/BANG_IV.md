### Bảng IV — KẾT QUẢ THỰC TẾ (auto-generated)

> **GreenLens (Ours)** = E3 full pipeline. Script Kaggle chỉ auto chạy **E0 + E1**; thêm E2/E3 thủ công sau.

| Vai trò | Method | Fine-tune | TRASH mAP50 | WATER mAP50 | ALL mAP50 | ALL mAP50-95 | TRASH P/R | WATER P/R |
|---------|--------|-----------|-------------|-------------|-----------|--------------|-----------|-----------|
| Baseline | E0 YOLOv8n-COCO | Không | 0.0001 | 0.0 | 0.0001 | 0.0 | 0.0023/0.0081 | 0.0/0.0 |
| Baseline FT | E1 FT-YOLOv8n _(detector GreenLens)_ | Có | 0.654 | 0.713 | 0.684 | 0.367 | 0.628/0.685 | 0.658/0.729 |

| **Ours** | E2 GreenLens-Det | Có | = E1 | Bảng V | = E1 | — | — |
| **Ours ★** | **E3 GreenLens-Full** | Có | = E1 | Bảng V | = E1 | — | — |

★ **E3 = model đề xuất chính** (YOLO + scene + subtype + API).

**ΔmAP E1 vs E0:** E0 ≈ 0 → E1 **+0.684** (fine-tune domain bắt buộc; % so E0≈0 không meaningful)

_Source: E0 local 2026-06-07 · E1 Kaggle test 207 images 2026-06-08 · `ml/weights/best.pt` ✅_

_Generated: 2026-06-07 · E0/E1 số cập nhật 2026-06-08_

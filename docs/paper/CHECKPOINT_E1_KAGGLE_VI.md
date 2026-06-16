# GreenLens — Checkpoint train paper (cập nhật 2026-06-08)

> **Tiếp theo:** Train lại E1 trên Kaggle (2 cell) → download `e1_bundle.zip` → scene → subtype.

---

## Trạng thái tổng

| Bước | Trạng thái | Số / file |
|------|------------|-----------|
| Dataset merged | ✅ | Kaggle `pollution-merge-vn-nation` · 1147/244/207 |
| **E0** eval COCO | ✅ **Xong (local)** | ALL mAP50 **0.0001** |
| **E1** train YOLOv8n | ⚠️ **Số có, `best.pt` mất** | ALL mAP50 **0.684** — cần Commit lại |
| E2 scene | ⬜ | |
| E3 subtype | ⬜ | |

---

## E0 — đã chạy (local)

**Ngày:** 2026-06-07
**Máy:** Windows local
**Dataset:** `D:\CapsoneProject\DATASETFINAL\TOTAL\datasetfinal`

```cmd
uv run python ml\training\kaggle\run_paper_experiments.py --mode e0 --dataset-dir "D:\CapsoneProject\DATASETFINAL\TOTAL\datasetfinal" --output-dir "ml\paper_output" --imgsz 1280
```

| Metric | E0 |
|--------|-----|
| TRASH mAP50 | 0.0001 |
| WATER mAP50 | 0.0 |
| ALL mAP50 | 0.0001 |
| TRASH P | 0.0023 |

→ Ghi trong `ml/paper_output/BANG_IV.md` và playbook §0.

---

## E1 — Kaggle (số đã có, weight mất)

**Ngày train:** 2026-06-08
**Dataset path:** `/kaggle/input/datasets/hulphc/pollution-merge-vn-nation`

| Metric | E1 |
|--------|-----|
| TRASH mAP50 | 0.654 |
| WATER mAP50 | 0.713 |
| ALL mAP50 | 0.684 |
| TRASH P / R | 0.628 / 0.685 |
| WATER P / R | 0.658 / 0.729 |

**Vì sao mất `best.pt`:** Cell cuối lỗi `maps50` → Commit **Error** → Kaggle không lưu Output → session tắt → `/kaggle/working/` xóa.

**Train lại:** 2 cell notebook (pip + train inline), **Save & Run All (Commit)**, download `e1_bundle.zip`. Xem chat / playbook §4.

---

## File markdown đã cập nhật

| File | Nội dung |
|------|----------|
| `ml/paper_output/BANG_IV.md` | Bảng IV số E0 + E1 |
| `docs/paper/PAPER_FULL_PLAYBOOK_VI.md` | §0 trạng thái + § Kết quả thực tế |
| `docs/paper/CHECKPOINT_E1_KAGGLE_VI.md` | File này |

---

## Sau khi có `best.pt`

```cmd
copy best.pt D:\CapsoneProject\Detection-AI\greenlens-detection-ai\ml\weights\best.pt
```

`.env`:
```env
MODEL_PATH=ml/weights/best.pt
```

→ Train scene (E2) → subtype (E3) → đo FP WATER / F1.

---

_Last updated: 2026-06-08_

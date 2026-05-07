# GUIDE — Pull về và chạy test

Tài liệu này dành cho dev mới pull repo về và cần chạy test nhanh, đúng chuẩn.

---

## 1) Yêu cầu môi trường

- Python `>= 3.11` (repo đang khai báo `>= 3.14`, nhưng tooling cấu hình theo 3.11).
- `uv` để cài dependencies và chạy lệnh.

Kiểm tra:

```bash
python --version
uv --version
```

Nếu chưa có `uv`: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

---

## 2) Pull repo và cài dependencies

```bash
git clone <repo-url>
cd greenlens-detection-ai
uv sync
```

`uv sync` sẽ cài đầy đủ package theo `pyproject.toml`/`uv.lock`.

---

## 3) Tạo `.env` cho local

Copy file mẫu:

### Windows (PowerShell)

```powershell
copy .env.example .env
```

### Linux/macOS

```bash
cp .env.example .env
```

Thiết lập tối thiểu để chạy test/API:

```env
MODEL_PATH=ml/weights/best.pt
MODEL_VERSION=v1.0.0-local
CLASSIFY_DEMO_MODE=false
```

> Nếu chưa có `ml/weights/best.pt`, có thể tạm dùng:
>
> - `MODEL_PATH=ml/weights/yolov8n.pt`
> - hoặc bật `CLASSIFY_DEMO_MODE=true` để demo flow UI.

---

## 4) Chạy test tự động

### Chạy toàn bộ test

```bash
uv run pytest -q
```

### Chạy test classify API (nhanh nhất)

```bash
uv run pytest -q tests/integration/test_classify_api.py
```

---

## 5) Chạy lint (bắt buộc trước PR)

```bash
uv run ruff check .
```

Nếu cần auto-fix lỗi style/import:

```bash
uv run ruff check . --fix
```

---

## 6) Chạy service local để test tay

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

URL dùng thử:

- Swagger: `http://127.0.0.1:8000/docs`
- Demo upload classify: `http://127.0.0.1:8000/demo/demo_capture_classify.html`
- Readiness: `http://127.0.0.1:8000/api/v1/ready`

---

## 7) Checklist “máy mới pull về”

- [ ] `uv sync` thành công
- [ ] Có `.env`
- [ ] `uv run pytest -q` pass
- [ ] `uv run ruff check .` pass
- [ ] `GET /api/v1/ready` trả `model_loaded` đúng kỳ vọng

---

## 8) Lỗi thường gặp

### `model_loaded: false`

- Sai `MODEL_PATH` hoặc thiếu file `.pt`.
- Chưa restart `uvicorn` sau khi đổi `.env`.

### API trả `predictions: []`

- Model chưa train đủ dữ liệu.
- Dữ liệu class mapping sai (`0 TRASH, 1 WATER, 2 SMOKE, 3 CHEMICAL`).
- Model loaded nhưng confidence thấp cho ảnh test.

### Test fail do môi trường

- Chạy lại `uv sync`.
- Xoá cache cũ: `.pytest_cache`, `.ruff_cache` (nếu cần).

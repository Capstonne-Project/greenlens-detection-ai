# Duplicate Detection — Image Compare API Specification

> **Dự án:** GreenLens (SU26SE049) — Ứng dụng báo cáo ô nhiễm môi trường
> **Mục đích:** Document này mô tả endpoint mới cần thêm vào Python AI Service để hỗ trợ phát hiện trùng lặp báo cáo ô nhiễm.
> **Người đọc:** AI Service developer (Python/FastAPI)

---

## 1. Bối cảnh

### Bài toán

Khi citizen gửi báo cáo ô nhiễm mới, backend .NET cần kiểm tra xem báo cáo đó có trùng với báo cáo đã tồn tại hay không. Hệ thống phát hiện trùng lặp có 2 tầng:

```
Tier 1 (Backend .NET):  GPS ≤ 50m AND cùng loại ô nhiễm AND ≤ 24h
                         → Tìm danh sách "candidates" — SQL query, free, instant
                         
Tier 2 (Python AI):     So sánh ảnh giữa report mới và candidate
                         → Dùng CLIP hoặc DINOv2 image embeddings
                         → Trả về similarity score
```

**Tier 1 đã được backend .NET xử lý.** Python AI Service chỉ cần implement **Tier 2** — so sánh 2 ảnh.

### Tại sao CLIP/DINOv2 thay vì pHash?

| Approach | Khác góc < 45° | Khác góc 45°–90° | Khác góc > 90° |
|---|---|---|---|
| **pHash** | ⚠️ May rủi | ❌ Fail | ❌ Fail |
| **CLIP/DINOv2** | ✅ Tốt | ✅ Khá tốt | ⚠️ Trung bình |

Trong thực tế, 2 citizen thường đứng gần nhau (cùng phía đường) chụp cùng bãi rác, góc chênh lệch 10°–60° → CLIP/DINOv2 xử lý tốt.

---

## 2. Endpoint Specification

### `POST /api/v1/compare-images`

So sánh 2 ảnh để xác định có phải cùng 1 điểm ô nhiễm/bãi rác hay không.

#### Request

**Content-Type:** `application/json`

```json
{
  "image_url_a": "https://storage.example.com/reports/abc123/photo1.jpg",
  "image_url_b": "https://storage.example.com/reports/def456/photo1.jpg"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `image_url_a` | string (URL) | ✅ | URL ảnh của báo cáo **mới** (vừa submit) |
| `image_url_b` | string (URL) | ✅ | URL ảnh của báo cáo **candidate** (đã tồn tại) |

> **Lưu ý:** Cả 2 URL đều trỏ đến Cloudflare R2 (S3-compatible), public-readable.

#### Response — Success (200)

```json
{
  "similarity": 0.87,
  "is_same_scene": true,
  "model": "dinov2-base",
  "processing_time_ms": 142
}
```

| Field | Type | Description |
|---|---|---|
| `similarity` | float (0.0–1.0) | Cosine similarity giữa 2 image embeddings |
| `is_same_scene` | boolean | `true` nếu `similarity >= threshold` (recommend 0.80) |
| `model` | string | Tên model đã dùng (để audit) |
| `processing_time_ms` | integer | Thời gian xử lý (ms) |

#### Response — Error (4xx/5xx)

```json
{
  "error": "Failed to download image_url_a",
  "detail": "HTTP 404 from storage"
}
```

#### Timeout

Backend .NET sẽ gọi endpoint này với **timeout 5 giây**. Nếu không trả kịp, backend sẽ fallback dùng Tier 1 (geo+time+category) mà không có AI score.

---

## 3. Gợi ý Implementation

### Model recommendation

| Model | Size | Speed | Quality | Recommend |
|---|---|---|---|---|
| **DINOv2-small** (ViT-S/14) | ~85MB | ~50ms/ảnh | Tốt | ✅ Nếu cần nhẹ |
| **DINOv2-base** (ViT-B/14) | ~330MB | ~100ms/ảnh | Rất tốt | ✅ **Recommend** |
| **CLIP ViT-B/32** | ~340MB | ~80ms/ảnh | Tốt | ✅ Alternative |
| **DINOv2-large** (ViT-L/14) | ~1.1GB | ~200ms/ảnh | Xuất sắc | ⚠️ Nặng |

> **Recommend: DINOv2-base** — cân bằng tốt giữa accuracy và speed. Tổng 2 ảnh ~200ms, đủ trong timeout 5s.

### Pseudocode

```python
import torch
from transformers import AutoImageProcessor, AutoModel
from PIL import Image
import requests
from io import BytesIO

# ── Load model (1 lần khi startup) ──
processor = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
model = AutoModel.from_pretrained("facebook/dinov2-base")
model.eval()

def get_embedding(image_url: str) -> torch.Tensor:
    """Download ảnh từ URL → extract embedding vector."""
    response = requests.get(image_url, timeout=3)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content)).convert("RGB")
    
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Lấy [CLS] token embedding
    embedding = outputs.last_hidden_state[:, 0, :]
    # Normalize
    embedding = torch.nn.functional.normalize(embedding, dim=-1)
    return embedding

def compare_images(image_url_a: str, image_url_b: str) -> dict:
    """So sánh 2 ảnh, trả về similarity score."""
    emb_a = get_embedding(image_url_a)
    emb_b = get_embedding(image_url_b)
    
    # Cosine similarity
    similarity = torch.nn.functional.cosine_similarity(emb_a, emb_b).item()
    
    return {
        "similarity": round(similarity, 4),
        "is_same_scene": similarity >= 0.80,
        "model": "dinov2-base"
    }
```

### FastAPI endpoint

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import time

app = FastAPI()

class CompareRequest(BaseModel):
    image_url_a: str
    image_url_b: str

class CompareResponse(BaseModel):
    similarity: float
    is_same_scene: bool
    model: str
    processing_time_ms: int

@app.post("/api/v1/compare-images", response_model=CompareResponse)
async def compare_images_endpoint(req: CompareRequest):
    start = time.time()
    try:
        result = compare_images(req.image_url_a, req.image_url_b)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    elapsed_ms = int((time.time() - start) * 1000)
    return CompareResponse(
        similarity=result["similarity"],
        is_same_scene=result["is_same_scene"],
        model=result["model"],
        processing_time_ms=elapsed_ms
    )
```

### Dependencies (thêm vào requirements.txt)

```
torch>=2.0
transformers>=4.30
Pillow>=10.0
```

> **GPU optional:** DINOv2-base chạy tốt trên CPU (~200ms/cặp ảnh). Nếu có GPU (CUDA) sẽ nhanh hơn (~50ms).

---

## 4. Threshold Tuning

Recommend bắt đầu với **threshold = 0.80** cho `is_same_scene`:

| Similarity | Ý nghĩa | Action |
|---|---|---|
| **≥ 0.90** | Rất giống — gần chắc chắn cùng bãi rác | Flag + high confidence |
| **0.80–0.90** | Khá giống — có thể cùng bãi rác | Flag + medium confidence |
| **0.60–0.80** | Mơ hồ — có thể giống, có thể không | Không flag (để Tier 1 quyết) |
| **< 0.60** | Khác nhau | Không flag |

> Threshold này có thể điều chỉnh sau khi test với dữ liệu thực. Recommend tạo 1 config env var `COMPARE_THRESHOLD=0.80` để dễ tune.

---

## 5. Lưu ý quan trọng

### Performance
- **Load model 1 lần** khi server startup, cache trong memory. KHÔNG load lại mỗi request.
- Cần ~330MB RAM cho DINOv2-base + ~200MB cho Python runtime → **tối thiểu 1GB RAM** cho service.
- Nếu concurrent requests cao → consider dùng `asyncio.to_thread()` để không block event loop.

### Error Handling
- URL ảnh không download được → trả 400 với message rõ ràng
- Model chưa load xong → trả 503 (Service Unavailable)
- Timeout nội bộ > 4s → trả kết quả đang có hoặc 504

### Testing
- Tạo test với 2 ảnh giống nhau (cùng góc) → expect similarity > 0.90
- Tạo test với 2 ảnh cùng bãi rác, khác góc ~30° → expect similarity 0.75–0.90
- Tạo test với 2 ảnh hoàn toàn khác nhau → expect similarity < 0.50

### Deployment
- Endpoint này sẽ được backend .NET gọi cùng pattern với `/api/v1/classify-moderation-upload`
- Config URL trong .NET backend: `AiService:BaseUrl` (đã có trong `appsettings.json`)
- Không cần authentication riêng (internal service communication)

---

## 6. Tham khảo

- **DINOv2 Paper:** [DINOv2: Learning Robust Visual Features without Supervision](https://arxiv.org/abs/2304.07193)
- **HuggingFace:** https://huggingface.co/facebook/dinov2-base
- **CLIP Paper:** [Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020)
- **BR-REP-030:** Hai báo cáo trùng nếu: (a) cùng loại ô nhiễm; (b) GPS ≤ 50m; (c) trong 24h
- **BR-AI-002:** AI so khớp GPS + time + image similarity → gợi ý LEO merge

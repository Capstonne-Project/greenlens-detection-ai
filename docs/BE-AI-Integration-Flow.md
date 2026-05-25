# BE .NET ↔ AI Service Integration Flow

> Dành cho team BE .NET — mô tả cách gọi AI Service (Python/FastAPI) để phân tích ảnh báo cáo ô nhiễm.

---

## Tổng quan

User chụp/chọn ảnh → FE gửi lên BE .NET → BE forward sang AI Service → AI trả kết quả → FE hiển thị preview → User xác nhận → BE lưu ảnh + tạo report.

**Ảnh không lưu vĩnh viễn cho đến khi user bấm Submit.**

---

## Flow chi tiết

### STEP 1 — Analyze (chưa tạo report)

```
FE  ──POST /reports/analyze──►  BE .NET
    multipart/form-data
    field: "image" = <file>

BE .NET:
  1. Nhận file từ FE
  2. Lưu file vào temp store (TTL 15 phút) → sinh temp_image_id (GUID)
  3. Forward file sang AI Service (multipart)
  4. Nhận kết quả AI
  5. Trả về FE: temp_image_id + ai_result

AI Service  ◄──multipart: image──  BE .NET
            ──────response──────►  BE .NET
```

**Response trả về FE:**

```json
{
  "temp_image_id": "abc-123-xyz",
  "expires_in_seconds": 900,
  "ai_result": {
    "decision": "ACCEPTABLE_REPORT_IMAGE",
    "reason": "Mapped pollution evidence is strong enough for report workflow.",
    "classify": {
      "primary_class": "TRASH",
      "confidence": 0.87,
      "severity": "HIGH",
      "image_relevance": "POLLUTION_LIKELY",
      "pollution_coverage_ratio": 0.43,
      "predictions": [
        { "class": "TRASH", "confidence": 0.87, "bbox_count": 3 }
      ],
      "inference_time_ms": 120.5,
      "yolo_active": true,
      "scene_classifier_active": true
    }
  }
}
```

---

### STEP 2 — Submit (user xác nhận → tạo report)

```
FE  ──POST /reports/submit──►  BE .NET
Body (JSON):
{
  "temp_image_id": "abc-123-xyz",
  "pollution_type": "TRASH",        ← user có thể giữ hoặc chỉnh lại
  "severity": "HIGH",               ← user có thể giữ hoặc chỉnh lại
  "description": "Rác thải tràn lan tại hẻm 12",
  "location": { "lat": 10.762622, "lng": 106.660172 }
}

BE .NET:
  1. Tìm file theo temp_image_id → nếu không có / hết hạn → 400
  2. Upload file lên S3/Blob → lấy image_url
  3. Tạo Report record trong DB
  4. Xóa temp file
  5. Trả về report đã tạo
```

**Report record lưu DB:**

| Field | Giá trị |
|---|---|
| image_url | URL từ S3/Blob |
| ai_decision | ACCEPTABLE / NEED_MANUAL_REVIEW |
| ai_primary_class | TRASH / WATER / SMOKE / CHEMICAL |
| ai_confidence | 0.0 – 1.0 |
| ai_severity | LOW / MEDIUM / HIGH / CRITICAL |
| pollution_type | Giá trị user chọn (có thể khác AI) |
| status | Xem bảng mapping bên dưới |
| location | lat/lng |
| description | Mô tả của user |

---

## Decision Mapping → Report Status

| AI decision | Report status | Ghi chú |
|---|---|---|
| `ACCEPTABLE_REPORT_IMAGE` | `PENDING` | Vào queue xử lý bình thường |
| `NEED_MANUAL_REVIEW` | `PENDING_REVIEW` | Cần người duyệt trước khi xử lý |
| `IRRELEVANT_OR_SUSPECTED_ABUSIVE` | — | BE chặn, không cho submit, trả 422 |

---

## Sequence Diagram

```
FE              BE .NET           AI Service          S3/DB
│                  │                   │                │
│──POST analyze───►│                   │                │
│  (multipart)     │                   │                │
│                  │──multipart───────►│                │
│                  │◄──ai_result───────│                │
│                  │ save temp file    │                │
│◄──temp_id────────│                   │                │
│   + ai_result    │                   │                │
│                  │                   │                │
│  [user review    │                   │                │
│   & confirm]     │                   │                │
│                  │                   │                │
│──POST submit────►│                   │                │
│  (temp_id+data)  │                   │                │
│                  │──────────────────────────────────►│ upload S3
│                  │◄──────────────────────────────────│ image_url
│                  │──────────────────────────────────►│ create Report
│◄──report_id──────│                   │                │
```

---

## Contract AI Service

### Endpoint

```
POST http://<ai-service-host>/api/v1/classify-moderation-upload
Content-Type: multipart/form-data

field name : "image"   ← bắt buộc đúng tên này
field value: <binary>
```

### Response 200

```json
{
  "decision": "ACCEPTABLE_REPORT_IMAGE | NEED_MANUAL_REVIEW | IRRELEVANT_OR_SUSPECTED_ABUSIVE",
  "reason": "string",
  "classify": {
    "primary_class": "TRASH | WATER | SMOKE | CHEMICAL | null",
    "confidence": 0.0,
    "severity": "LOW | MEDIUM | HIGH | CRITICAL",
    "image_relevance": "POLLUTION_LIKELY | NOT_POLLUTION_OR_UNRELATED | UNCLEAR_NEED_MANUAL_REVIEW",
    "pollution_coverage_ratio": 0.0,
    "predictions": [
      { "class": "string", "confidence": 0.0, "bbox_count": 0 }
    ],
    "inference_time_ms": 0.0,
    "yolo_active": true,
    "scene_classifier_active": true,
    "model_version": "string",
    "noise_supported": false
  }
}
```

### Response errors

| HTTP | Khi nào |
|---|---|
| 400 | File rỗng |
| 413 | File > 20MB |
| 5xx | AI Service lỗi / timeout |

---

## Error Cases BE .NET phải handle

### Step 1 — Analyze

| Tình huống | HTTP trả FE | Ghi chú |
|---|---|---|
| File không phải ảnh (jpg/png) | 400 | Validate trước khi gọi AI |
| File > 20MB | 413 | Validate trước khi gọi AI |
| AI Service timeout / down | 503 | `Service temporarily unavailable` |
| AI trả `IRRELEVANT_OR_SUSPECTED_ABUSIVE` | 200 | Vẫn trả 200 nhưng FE disable nút Submit, hiển thị warning |

### Step 2 — Submit

| Tình huống | HTTP trả FE | Ghi chú |
|---|---|---|
| `temp_image_id` không tồn tại | 400 | `Invalid session` |
| Temp đã hết hạn (> 15 phút) | 400 | `Image session expired, please re-upload` |
| Upload S3 fail | 500 | Rollback, không tạo Report |

---

## Temp Storage (giữa Step 1 và Step 2)

Ảnh được giữ tạm ở BE .NET trong khoảng thời gian user review. Không lưu ở AI Service.

| Option | Phù hợp |
|---|---|
| Temp folder + cleanup job (TTL 15 phút) | Đồ án / MVP |
| `IMemoryCache` + GUID key | Nhanh, nhưng mất khi restart |
| Redis + TTL | Production, scale ngang |

> Cho đồ án: **temp folder + background cleanup job** là đủ.

---

## C# Example — Gọi AI Service (Step 1)

```csharp
[HttpPost("analyze")]
public async Task<IActionResult> Analyze(IFormFile image)
{
    // Validate
    if (image == null || image.Length == 0)
        return BadRequest("No file uploaded.");
    if (image.Length > 20 * 1024 * 1024)
        return StatusCode(413, "File too large.");

    // Lưu temp
    var tempId = Guid.NewGuid().ToString();
    var tempPath = Path.Combine(_tempFolder, tempId);
    using (var fs = System.IO.File.Create(tempPath))
        await image.CopyToAsync(fs);

    // Gọi AI Service
    using var content = new MultipartFormDataContent();
    using var stream = System.IO.File.OpenRead(tempPath);
    content.Add(new StreamContent(stream), "image", image.FileName);

    var resp = await _httpClient.PostAsync(
        "http://ai-service/api/v1/classify-moderation-upload", content);

    if (!resp.IsSuccessStatusCode)
        return StatusCode(503, "AI Service unavailable.");

    var aiResult = await resp.Content.ReadAsStringAsync();

    return Ok(new {
        temp_image_id = tempId,
        expires_in_seconds = 900,
        ai_result = System.Text.Json.JsonSerializer.Deserialize<object>(aiResult)
    });
}
```

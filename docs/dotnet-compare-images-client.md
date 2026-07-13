# Hướng dẫn .NET — Gọi `POST /api/v1/compare-images` (HttpClient)

> **Dành cho:** team `greenlens-service` (.NET)  
> **Liên quan:** [ai-compare-images-spec.md](./ai-compare-images-spec.md), [implementation_plan_compare_ai.md](./implementation_plan_compare_ai.md)  
> **Trạng thái AI Service:** endpoint đã sẵn sàng (DINOv2-base)

---

## 1. Tóm tắt contract

| | |
|---|---|
| **Method / Path** | `POST /api/v1/compare-images` |
| **Content-Type** | `application/json` |
| **Auth** | Không cần (internal service) |
| **Timeout khuyến nghị phía .NET** | **5 giây** (nếu timeout → fallback Tier 1) |
| **Base URL** | `AiService:BaseUrl` trong `appsettings.json` (cùng pattern classify) |

### Request body

```json
{
  "image_url_a": "https://r2.example.com/reports/new/photo1.jpg",
  "image_url_b": "https://r2.example.com/reports/candidate/photo1.jpg"
}
```

| Field | Ý nghĩa |
|---|---|
| `image_url_a` | URL ảnh báo cáo **mới** (public-readable, HTTP/HTTPS) |
| `image_url_b` | URL ảnh báo cáo **candidate** từ Tier 1 |

> AI Service **tự download** 2 ảnh từ URL. .NET chỉ gửi URL, không gửi file multipart.

### Response 200

```json
{
  "similarity": 0.87,
  "is_same_scene": true,
  "model": "dinov2-base",
  "processing_time_ms": 142
}
```

| Field | Type | Dùng thế nào |
|---|---|---|
| `similarity` | `0.0`–`1.0` | Lưu `AiSimilarityScore` |
| `is_same_scene` | `bool` | `false` → **không** flag duplicate (AI nói khác cảnh) |
| `model` | `string` | Audit (optional log) |
| `processing_time_ms` | `int` | Observability |

### Error codes

| HTTP | Khi nào | .NET nên làm gì |
|---|---|---|
| `400` | URL sai / download ảnh thất bại / timeout download | Treat như AI unavailable → **fallback Tier 1** (hoặc skip AI) |
| `503` | Model DINOv2 chưa load | Fallback Tier 1 |
| `500` | Lỗi inference nội bộ | Fallback Tier 1 |
| Timeout / network | HttpClient cancel sau 5s | Catch `OperationCanceledException` / `TaskCanceledException` → Tier 1 |

FastAPI error body (thực tế):

```json
{ "detail": "Failed to download image_url_b: ..." }
```

---

## 2. Config (`appsettings.json`)

```json
{
  "AiService": {
    "BaseUrl": "http://localhost:8000",
    "TimeoutSeconds": 5
  }
}
```

```csharp
public sealed class AiOptions
{
    public const string SectionName = "AiService";

    public string BaseUrl { get; set; } = "http://localhost:8000";
    public int TimeoutSeconds { get; set; } = 5;
}
```

---

## 3. Đăng ký `HttpClient` (DI)

```csharp
// Program.cs / DependencyInjection.cs
services.Configure<AiOptions>(configuration.GetSection(AiOptions.SectionName));

services.AddHttpClient("AiService", (sp, client) =>
{
    var options = sp.GetRequiredService<IOptions<AiOptions>>().Value;
    client.BaseAddress = new Uri(options.BaseUrl.TrimEnd('/') + "/");
    client.Timeout = TimeSpan.FromSeconds(options.TimeoutSeconds);
})
.ConfigurePrimaryHttpMessageHandler(() => new SocketsHttpHandler
{
    PooledConnectionLifetime = TimeSpan.FromMinutes(5),
});

services.AddScoped<IAiImageCompareService, AiImageCompareService>();
```

> Dùng **named client** `"AiService"` để tái sử dụng cùng BaseUrl với classify / moderation.

---

## 4. Interface + DTO

```csharp
public interface IAiImageCompareService
{
    /// <summary>
    /// Returns null when AI is unavailable / timeout / non-success — caller falls back to Tier 1.
    /// </summary>
    Task<ImageCompareResult?> CompareAsync(
        string imageUrlA,
        string imageUrlB,
        CancellationToken cancellationToken = default);
}

public sealed record ImageCompareResult(
    decimal Similarity,
    bool IsSameScene,
    string Model,
    int ProcessingTimeMs);
```

DTO map JSON (snake_case từ Python):

```csharp
internal sealed class CompareImagesResponseDto
{
    [JsonPropertyName("similarity")]
    public decimal Similarity { get; init; }

    [JsonPropertyName("is_same_scene")]
    public bool IsSameScene { get; init; }

    [JsonPropertyName("model")]
    public string Model { get; init; } = "";

    [JsonPropertyName("processing_time_ms")]
    public int ProcessingTimeMs { get; init; }
}
```

---

## 5. Implementation mẫu — `AiImageCompareService`

```csharp
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace Greenlens.Infrastructure.AI;

internal sealed class AiImageCompareService(
    IHttpClientFactory httpClientFactory,
    IOptions<AiOptions> options,
    ILogger<AiImageCompareService> logger) : IAiImageCompareService
{
    public async Task<ImageCompareResult?> CompareAsync(
        string imageUrlA,
        string imageUrlB,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(imageUrlA) || string.IsNullOrWhiteSpace(imageUrlB))
            return null;

        var client = httpClientFactory.CreateClient("AiService");

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(TimeSpan.FromSeconds(options.Value.TimeoutSeconds));

        var payload = new
        {
            image_url_a = imageUrlA,
            image_url_b = imageUrlB,
        };

        try
        {
            using var response = await client.PostAsJsonAsync(
                "api/v1/compare-images",
                payload,
                cts.Token);

            if (!response.IsSuccessStatusCode)
            {
                var body = await response.Content.ReadAsStringAsync(cts.Token);
                logger.LogWarning(
                    "AI compare-images failed: {StatusCode} {Body}",
                    (int)response.StatusCode,
                    body);
                return null; // Tier 1 fallback
            }

            var dto = await response.Content.ReadFromJsonAsync<CompareImagesResponseDto>(
                cancellationToken: cts.Token);

            if (dto is null)
                return null;

            return new ImageCompareResult(
                dto.Similarity,
                dto.IsSameScene,
                dto.Model,
                dto.ProcessingTimeMs);
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            // HttpClient / CancelAfter timeout — not request abort
            logger.LogWarning("AI compare-images timed out after {Seconds}s", options.Value.TimeoutSeconds);
            return null;
        }
        catch (HttpRequestException ex)
        {
            logger.LogWarning(ex, "AI compare-images network error");
            return null;
        }
    }
}
```

### Gọi thử nhanh (console / unit smoke)

```csharp
var result = await aiImageCompare.CompareAsync(
    "https://storage.example.com/reports/new.jpg",
    "https://storage.example.com/reports/old.jpg",
    ct);

if (result is null)
{
    // AI down / timeout → chỉ dùng Tier 1 (geo_time)
}
else if (!result.IsSameScene)
{
    // AI nói khác cảnh → KHÔNG MarkPossibleDuplicate
}
else
{
    // MarkPossibleDuplicate(..., source: "geo_time_ai", aiScore: result.Similarity)
}
```

---

## 6. Cách gắn vào SubmitHandler (Tier 1 → Tier 2)

Khớp [implementation_plan_compare_ai.md](./implementation_plan_compare_ai.md):

```csharp
var candidates = await FindDuplicateCandidatesAsync(report, ct);
if (candidates.Count == 0)
    return; // không trùng

var bestMatch = candidates[0]; // oldest
decimal? aiScore = null;
var source = "geo_time";

try
{
    var reportImage = report.Media.FirstOrDefault()?.Url;
    var candidateImage = bestMatch.Media.FirstOrDefault()?.Url;

    if (reportImage is not null && candidateImage is not null)
    {
        var ai = await aiImageCompare.CompareAsync(reportImage, candidateImage, ct);
        if (ai is not null)
        {
            aiScore = ai.Similarity;
            source = "geo_time_ai";

            if (!ai.IsSameScene)
                return; // AI khác cảnh → bỏ flag
        }
        // ai == null → giữ Tier 1, source = "geo_time"
    }
}
catch (OperationCanceledException) when (ct.IsCancellationRequested)
{
    throw; // request bị abort thật
}

report.MarkPossibleDuplicate(bestMatch.Id, source, aiScore);
await unitOfWork.SaveChangesAsync(ct);
```

**Quy tắc quyết định:**

```
Tier 1 không có candidate     → không flag
Tier 1 có candidate
  ├─ AI timeout / 4xx / 5xx   → flag, source = "geo_time", AiSimilarityScore = null
  ├─ AI is_same_scene = false → KHÔNG flag
  └─ AI is_same_scene = true  → flag, source = "geo_time_ai", AiSimilarityScore = similarity
```

---

## 7. Checklist tích hợp

1. [ ] `AiService:BaseUrl` trỏ đúng AI service (dev / staging / prod).
2. [ ] Named `HttpClient` `"AiService"` timeout = **5s**.
3. [ ] URL ảnh R2 **public-readable** (AI download được trong ~3s/ảnh).
4. [ ] `CompareAsync` trả `null` trên lỗi → không crash SubmitReport.
5. [ ] `is_same_scene == false` → không `MarkPossibleDuplicate`.
6. [ ] Log `similarity`, `model`, `processing_time_ms` khi success (audit BR-AI-005).
7. [ ] Smoke test: cùng 1 URL 2 lần → `similarity` cao, `is_same_scene: true`.

### Curl tham chiếu (để .NET đối chiếu)

```bash
curl -X POST "http://localhost:8000/api/v1/compare-images" \
  -H "Content-Type: application/json" \
  -d "{\"image_url_a\":\"https://.../a.jpg\",\"image_url_b\":\"https://.../b.jpg\"}"
```

Swagger AI Service: `http://<ai-host>:8000/docs` → endpoint **compare**.

---

## 8. Lưu ý vận hành

- Lần gọi đầu sau khi AI restart có thể chậm nếu chưa warmup DINOv2 (~330MB). Prod nên bật `COMPARE_WARMUP_ON_STARTUP=true` phía Python.
- Threshold `is_same_scene` đang mặc định **0.80** (`COMPARE_THRESHOLD`) — chỉnh ở AI service, không hardcode phía .NET (trừ khi muốn override business rule riêng).
- Không cần gửi GPS / category / time vào endpoint này — Tier 1 đã lọc candidate trước.

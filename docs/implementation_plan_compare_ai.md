# BR-REP-030..033 — Duplicate Detection & Merge

## Bối cảnh

Implement phát hiện trùng lặp báo cáo ô nhiễm. Gồm 4 rules:

| BR         | Tên                        | Mô tả                                                     |
| ---------- | -------------------------- | --------------------------------------------------------- |
| BR-REP-030 | Định nghĩa trùng lặp       | Cùng loại ô nhiễm + GPS ≤ 50m + trong 24h                 |
| BR-REP-031 | Cờ nghi ngờ trùng lặp      | AI gán `possible_duplicate`, LEO quyết định cuối          |
| BR-REP-032 | Gộp báo cáo trùng          | Link vào primary, merge ảnh, +50% điểm, +1 reporter count |
| BR-REP-033 | Flag duplicate bởi citizen | ≥ 3 flag khác nhau → notify LEO xem xét                   |

Liên quan: **BR-AI-002** — AI so khớp GPS ≤ 50m + time ≤ 24h + image similarity (CLIP/DINOv2)

---

## Quyết định đã chốt

| #   | Quyết định                                                                      | Lý do                                                                                   |
| --- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 1   | **Tier 1 (geo+time+category)** là tiêu chí chính, đủ để flag possible_duplicate | GPS 50m + cùng category + 24h đã rất tin cậy, free, instant                             |
| 2   | **Tier 2 (CLIP/DINOv2)** qua Python AI service, thay thế pHash                  | pHash fail khi khác góc > 30°. CLIP/DINOv2 hiểu ngữ nghĩa ảnh, xử lý tốt khác góc < 90° |
| 3   | **Duplicate check inline (Option A)** trong SubmitHandler                       | Citizen cần biết ngay "báo cáo có thể trùng"                                            |
| 4   | Python AI service thêm `/api/v1/compare-images`                                 | Cùng pattern với `/classify-moderation-upload`, team AI tự quản, .NET chỉ gọi HTTP      |
| 5   | Tier 2 là **optional** — nếu AI timeout hoặc chưa deploy, Tier 1 vẫn hoạt động  | Resilience, giống BR-AI-006 fallback                                                    |

---

## Luồng tổng thể

```
Citizen submit report
  │
  ├── 1. AI Classification (BR-AI-001) — phân loại ảnh (existing, 5s timeout)
  │
  ├── 2. Save Report to DB (status = Submitted)
  │
  ├── 3. Duplicate Check (inline, AFTER save):
  │     │
  │     ├── Tier 1: SQL Query
  │     │   SELECT * FROM reports
  │     │   WHERE category_id = @categoryId
  │     │     AND Haversine(lat, lng, @lat, @lng) <= 50m
  │     │     AND created_at >= @createdAt - 24h
  │     │     AND status NOT IN (Duplicate, Rejected)
  │     │     AND id != @reportId
  │     │   ORDER BY created_at ASC
  │     │   LIMIT 5
  │     │
  │     ├── Nếu KHÔNG tìm thấy → done, không trùng
  │     │
  │     ├── Nếu TÌM THẤY candidates:
  │     │   ├── Tier 2 (optional): Gọi Python AI Service
  │     │   │   POST /api/v1/compare-images
  │     │   │   Body: { image_url_a: "report_mới.jpg", image_url_b: "candidate.jpg" }
  │     │   │   Response: { similarity: 0.87, is_same_scene: true }
  │     │   │   Timeout: 5s (fallback → dùng Tier 1 result)
  │     │   │
  │     │   └── Set on report:
  │     │       - IsPossibleDuplicate = true
  │     │       - PossibleDuplicateOfReportId = candidate.Id
  │     │       - DuplicateDetectionSource = "geo_time" hoặc "geo_time_ai"
  │     │       - AiSimilarityScore = 0.87 (nếu có Tier 2)
  │     │
  │     └── Save changes
  │
  └── Response to Citizen (kèm possibleDuplicateOfReportId nếu có)
```

---

## Proposed Changes

### Domain Layer

#### [MODIFY] [Report.cs](file:///d:/LEARNING/S9SU26/SEP490/greenlens-service/src/Greenlens.Domain/Entities/Report.cs)

Thêm fields cho duplicate detection:

```csharp
// ── Duplicate detection (BR-REP-030/031) ──
public bool IsPossibleDuplicate { get; private set; }
public Guid? PossibleDuplicateOfReportId { get; private set; }
public string? DuplicateDetectionSource { get; private set; } // "geo_time" | "geo_time_ai"
public decimal? AiSimilarityScore { get; private set; }       // 0.0–1.0 from CLIP/DINOv2

// Methods
public void MarkPossibleDuplicate(Guid primaryReportId, string source, decimal? aiScore = null)
{
    IsPossibleDuplicate = true;
    PossibleDuplicateOfReportId = primaryReportId;
    DuplicateDetectionSource = source;
    AiSimilarityScore = aiScore;
}

public void DismissDuplicate()
{
    IsPossibleDuplicate = false;
    PossibleDuplicateOfReportId = null;
    DuplicateDetectionSource = null;
    AiSimilarityScore = null;
}
```

**Đã có sẵn (giữ nguyên):** `ParentReportId`, `MarkDuplicate()`, `IncrementReporterCount()`, `ReportFlag`, `FlagType.Duplicate`

---

### Application Layer

#### [NEW] `Common/Interfaces/IAiImageCompareService.cs`

```csharp
public interface IAiImageCompareService
{
    Task<ImageCompareResult?> CompareAsync(string imageUrlA, string imageUrlB, CancellationToken ct);
}

public sealed record ImageCompareResult(decimal Similarity, bool IsSameScene);
```

#### [MODIFY] `Features/Reports/SubmitPollutionReport/SubmitPollutionReportCommandHandler.cs`

Thêm duplicate check **inline sau khi save**:

```csharp
// After SaveChanges...

// ── Duplicate detection (BR-REP-030) ──
var candidates = await FindDuplicateCandidatesAsync(report, ct);
if (candidates.Count > 0)
{
    var bestMatch = candidates[0]; // oldest match
    decimal? aiScore = null;
    var source = "geo_time";

    // Tier 2: AI image compare (optional, 5s timeout)
    try
    {
        var reportImage = report.Media.FirstOrDefault()?.Url;
        var candidateImage = bestMatch.Media.FirstOrDefault()?.Url;
        if (reportImage is not null && candidateImage is not null)
        {
            var result = await aiImageCompare.CompareAsync(reportImage, candidateImage, ct);
            if (result is not null)
            {
                aiScore = result.Similarity;
                source = "geo_time_ai";
                if (!result.IsSameScene) goto NoDuplicate; // AI says different → skip
            }
        }
    }
    catch (OperationCanceledException) { /* AI timeout → use Tier 1 only */ }

    report.MarkPossibleDuplicate(bestMatch.Id, source, aiScore);
    await unitOfWork.SaveChangesAsync(ct);

    NoDuplicate:;
}
```

#### [NEW] `Features/Reports/ConfirmDuplicate/ConfirmDuplicateCommand.cs`

LEO xác nhận merge (BR-REP-032):

```
ConfirmDuplicateCommand(Guid ReportId, Guid PrimaryReportId)
→ Handler:
  1. Validate cả 2 report tồn tại
  2. duplicateReport.MarkDuplicate(primaryReportId) → status = Duplicate
  3. primaryReport.IncrementReporterCount()
  4. Award +50% points to duplicate reporter (gamification event)
  5. Save + Notify duplicate reporter
```

#### [NEW] `Features/Reports/DismissDuplicate/DismissDuplicateCommand.cs`

LEO bác bỏ:

```
DismissDuplicateCommand(Guid ReportId)
→ Handler: report.DismissDuplicate()
```

#### [NEW] `Features/Reports/FlagReport/FlagReportCommand.cs`

Citizen flag (BR-REP-033):

```
FlagReportCommand(Guid ReportId, FlagType Type, string? Reason)
→ Handler:
  1. Check: flagger != reporter
  2. Check: unique (reportId, flaggerId, flagType)
  3. Create ReportFlag, add to DbContext
  4. Count flags for this report with this type
  5. If count >= 3 → notify LEO
```

#### [NEW] `Features/Reports/GetDuplicateCandidates/GetDuplicateCandidatesQuery.cs`

LEO review danh sách:

```
GetDuplicateCandidatesQuery(int Page, int PageSize)
→ Query: WHERE IsPossibleDuplicate = true AND Status NOT IN (Duplicate, Rejected)
  Include: PossibleDuplicateOfReport (để LEO so sánh)
```

---

### Infrastructure Layer

#### [NEW] `AI/AiImageCompareService.cs`

```csharp
internal sealed class AiImageCompareService(
    IHttpClientFactory httpClientFactory,
    IOptions<AiOptions> options,
    ILogger<AiImageCompareService> logger) : IAiImageCompareService
{
    public async Task<ImageCompareResult?> CompareAsync(
        string imageUrlA, string imageUrlB, CancellationToken ct)
    {
        using var client = httpClientFactory.CreateClient("AiService");
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(options.Value.TimeoutSeconds));

        var payload = new { image_url_a = imageUrlA, image_url_b = imageUrlB };
        var response = await client.PostAsJsonAsync("/api/v1/compare-images", payload, cts.Token);
        // ... deserialize → ImageCompareResult
    }
}
```

#### [MODIFY] Report EF Configuration

Thêm columns: `is_possible_duplicate`, `possible_duplicate_of_report_id`, `duplicate_detection_source`, `ai_similarity_score`

#### Geo Query Helper

Dùng Haversine trên `decimal Latitude/Longitude`:

```csharp
// Approximate bounding box: 50m ≈ 0.00045 degrees
var latThreshold = 0.00045m;
var lngThreshold = 0.00045m / (decimal)Math.Cos((double)report.Latitude * Math.PI / 180);

var candidates = await reports.QueryAsNoTracking()
    .Where(r => r.CategoryId == report.CategoryId)
    .Where(r => Math.Abs(r.Latitude - report.Latitude) <= latThreshold)
    .Where(r => Math.Abs(r.Longitude - report.Longitude) <= lngThreshold)
    .Where(r => r.CreatedAt >= report.CreatedAt.AddHours(-24))
    .Where(r => r.Status != ReportStatus.Duplicate && r.Status != ReportStatus.Rejected)
    .Where(r => r.Id != report.Id)
    .OrderBy(r => r.CreatedAt)
    .Take(5)
    .Include(r => r.Media)
    .ToListAsync(ct);
```

---

### API Layer

#### [MODIFY] [ReportsController.cs](file:///d:/LEARNING/S9SU26/SEP490/greenlens-service/src/Greenlens.Api/Controllers/ReportsController.cs)

| Endpoint                             | Method | Role    | Mô tả                      |
| ------------------------------------ | ------ | ------- | -------------------------- |
| `/v1/reports/{id}/confirm-duplicate` | POST   | LEO/DEO | BR-REP-032: Xác nhận merge |
| `/v1/reports/{id}/dismiss-duplicate` | POST   | LEO/DEO | Bác bỏ possible duplicate  |
| `/v1/reports/{id}/flag`              | POST   | Citizen | BR-REP-033: Flag report    |
| `/v1/reports/duplicate-candidates`   | GET    | LEO/DEO | Danh sách cần review       |

---

### Migration

`AddDuplicateDetectionFields`:

- `is_possible_duplicate` (bool, default false)
- `possible_duplicate_of_report_id` (uuid, nullable, FK → reports)
- `duplicate_detection_source` (varchar(30), nullable)
- `ai_similarity_score` (numeric(5,4), nullable)

---

## File tổng hợp

| #   | File                                               | Layer          | Action                        |
| --- | -------------------------------------------------- | -------------- | ----------------------------- |
| 1   | `Report.cs`                                        | Domain         | MODIFY (+4 props, +2 methods) |
| 2   | `IAiImageCompareService.cs`                        | Application    | NEW                           |
| 3   | `ConfirmDuplicateCommand.cs` + Handler + Validator | Application    | NEW (3 files)                 |
| 4   | `DismissDuplicateCommand.cs` + Handler             | Application    | NEW (2 files)                 |
| 5   | `FlagReportCommand.cs` + Handler + Validator       | Application    | NEW (3 files)                 |
| 6   | `GetDuplicateCandidatesQuery.cs` + Handler         | Application    | NEW (2 files)                 |
| 7   | `SubmitPollutionReportCommandHandler.cs`           | Application    | MODIFY (+duplicate check)     |
| 8   | `AiImageCompareService.cs`                         | Infrastructure | NEW                           |
| 9   | `ReportConfiguration.cs`                           | Infrastructure | MODIFY (+columns)             |
| 10  | `DependencyInjection.cs`                           | Infrastructure | MODIFY (+DI)                  |
| 11  | `ReportsController.cs`                             | API            | MODIFY (+4 endpoints)         |
| 12  | Migration                                          | Infrastructure | NEW                           |

**Tổng: ~15 files (10 mới, 5 sửa)**

---

## Verification Plan

### Automated Tests

- `dotnet build --no-restore` — 0 errors
- Unit test: `DuplicateCheck_SameCategoryNearby24h_FlagsPossible`
- Unit test: `DuplicateCheck_DifferentCategory_NoFlag`
- Unit test: `DuplicateCheck_Beyond50m_NoFlag`
- Unit test: `DuplicateCheck_AiTimeout_FallbackTier1`
- Unit test: `FlagReport_ThirdFlag_NotifiesLEO`
- Unit test: `ConfirmDuplicate_MergesAndAwardsPoints`
- Unit test: `DismissDuplicate_ClearsFlag`

### Manual Verification

- Swagger: submit 2 reports cùng vị trí + category → verify `IsPossibleDuplicate = true`
- Swagger: LEO confirm-duplicate → verify status = Duplicate + reporter count tăng
- Swagger: citizen flag 3 lần → verify LEO notification

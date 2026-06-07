🗺️ Lộ trình làm Outline 2 — VN-Eval-500 (và train)
Tổng quan cần làm

500 ảnh VN thực tế → Label bằng Roboflow → Tách train/val/test →
Train clean model → Evaluate trên VN-test → So sánh với Roboflow-test →
Viết paper: "Domain Gap Analysis"
PHASE 0 — Hiểu rõ mục tiêu 500 ảnh
Class Số ảnh cần chụp Lý do
TRASH ~200 ảnh Phổ biến ở VN, dễ chụp
WATER ~200 ảnh Khó nhất — cần đa dạng
SMOKE ~100 ảnh Khói đốt rác, xe cũ
Tổng ~500 ảnh
💡 Quan trọng: 500 ảnh này sẽ được chia thành:

~400 ảnh → bổ sung vào train/val set (augment dataset Roboflow)
~100 ảnh → VN-Test-100 giữ lại để evaluate domain gap (KHÔNG dùng để train)
PHASE 1 — Chụp ảnh thực tế (1–2 tuần)
1.1 Thiết bị & Cài đặt chụp
Dùng điện thoại Android/iOS, không chỉnh sửa (không filter, không crop)
Định dạng: JPG, giữ EXIF (GPS + timestamp quan trọng cho paper)
Resolution: để mặc định (3000–4000px) — resize sau
1.2 Hướng dẫn chụp từng class
TRASH — 200 ảnh:

✅ Cần chụp:

- Bãi rác ven đường (chiếm >50% ảnh) — góc ngang
- Rác trước cửa nhà/ngõ hẻm TPHCM
- Xe rác / container rác đầy
- Bãi rác tập kết khu dân cư
- Túi rác vứt bừa trên vỉa hè

❌ Tránh:

- Thùng rác sạch, đóng nắp
- Rác quá nhỏ (<5% diện tích ảnh)
- Ảnh xa quá (không thấy rõ rác)
  WATER — 200 ảnh:

✅ Cần chụp:

- Kênh/mương nước đen/ô nhiễm (kênh Tàu Hủ, kênh Đôi...)
- Nước thải chảy trên đường
- Ao/hồ nước đục, có váng dầu
- Nước ngập có rác nổi
- Cống thoát nước đen

❌ Tránh (sẽ dùng làm hard negative):

- Đường nhựa ướt sau mưa
- Bóng cây/nền đất tối
- Vũng nước nhỏ <2% ảnh
  → Những ảnh này vẫn chụp nhưng label RỖNG (hard negative)
  SMOKE — 100 ảnh:

✅ Cần chụp:

- Xe máy/xe tải cũ xả khói đậm
- Đốt rác ngoài trời (khu vực ngoại ô)
- Khói từ nhà máy/xưởng
- Đốt rơm rạ (nếu đi được vùng ngoại ô)

❌ Tránh:

- Khói mờ/nhạt gần như không thấy
- Khói bếp gas (ít ô nhiễm)
  PHASE 2 — Tổ chức ảnh trước khi label
  2.1 Cấu trúc thư mục

D:\CapsoneProject\VN_DATASET_500\
├── raw\ ← ảnh gốc, chưa label
│ ├── TRASH\ ← ~200 ảnh chụp
│ ├── WATER\ ← ~200 ảnh
│ └── SMOKE\ ← ~100 ảnh
├── hard_negatives\ ← ảnh WATER false positive (label rỗng)
└── labeled\ ← sau khi label xong → export ra đây
2.2 Script đặt tên chuẩn
Đổi tên ảnh thành format VN_TRASH_001.jpg, VN_WATER_001.jpg... để tracking dễ:

# Chạy trong PowerShell

$class = "TRASH"  # đổi thành WATER, SMOKE tương ứng
$i = 1
Get-ChildItem "D:\CapsoneProject\VN*DATASET_500\raw\$class" -File | ForEach-Object {
$newName = "VN*${class}_{0:D3}$($_.Extension)" -f $i
Rename-Item $_.FullName -NewName $newName
$i++
}
PHASE 3 — Label bằng Roboflow (cách nhanh nhất)
3.1 Tạo project mới trên Roboflow
Vào roboflow.com → Create Project
Project Type: Object Detection
Classes: TRASH, WATER, SMOKE (đúng thứ tự, đúng tên)
Upload batch raw/TRASH/ trước
3.2 Labeling workflow

Upload ảnh → Auto-Label (dùng Roboflow AI) → Review + Fix → Approve
💡 Tip tiết kiệm thời gian:

Dùng Roboflow Auto-Label (Model-assisted labeling) — AI label trước, mình chỉ sửa
Nếu có model cũ của mình → upload lên Roboflow làm "labeling assistant"
~500 ảnh nếu tự label thủ công: ~8–12 tiếng; với Auto-Label: ~3–4 tiếng
3.3 Export format

Format: YOLOv8 (NOT OBB — chọn "YOLOv8 Oriented Bounding Boxes" là SAI)
→ Chọn: "YOLOv8" standard (axis-aligned bounding box)
Split: 70% train / 20% val / 10% test
PHASE 4 — Merge dataset VN với Roboflow dataset gốc
4.1 Cấu trúc sau khi merge

ml/training/data/pollution/
├── images/
│ ├── train/ ← Roboflow train + VN train (~400 ảnh VN + 900 ảnh cũ)
│ ├── val/ ← Roboflow val + VN val
│ └── test/ ← VN-Test-100 (KHÔNG lẫn vào train!)
└── labels/
├── train/
├── val/
└── test/
4.2 Dùng Training Dashboard để merge
Mở http://localhost:8000/static/demo/demo_training_dashboard.html
Tab "Gộp Dataset" → upload VN dataset ZIP
Hệ thống tự merge + convert OBB → AABB nếu cần
PHASE 5 — Train clean model
Config đúng (theo RETRAIN_ACTION_PLAN.md):

Tham số Giá trị
Model gốc ml/weights/yolov8n.pt (KHÔNG dùng job cũ)
imgsz 1280
Epochs 150
Batch 8
PHASE 6 — Evaluate Domain Gap (nội dung chính của paper)
Sau khi train xong, chạy 2 evaluation riêng biệt:

# Test 1: Roboflow val set (distribution quen thuộc)

yolo val model=best.pt data=roboflow_only.yaml imgsz=1280

# Test 2: VN-Test-100 (domain mới — key experiment của paper)

yolo val model=best.pt data=vn_test_only.yaml imgsz=1280
Kết quả cần ghi vào paper:

Metric Roboflow-Val VN-Test-100 Gap
mAP50 TRASH ? ? →
mAP50 WATER ? ? →
mAP50 SMOKE ? ? →
Overall mAP50 ? ? Δ%
Gap này chính là đóng góp khoa học của bài báo.

Timeline thực tế
Tuần Việc làm
Tuần 1 Chụp TRASH (200) + WATER (200) ảnh
Tuần 2 Chụp SMOKE (100) + Label bằng Roboflow (3–4 tiếng)
Tuần 2–3 Merge dataset, verify format, chạy clean training job
Tuần 3 Evaluate, fill tables, bắt đầu viết paper
Tuần 4 Hoàn thiện draft + submit
✅ Checklist nhanh để bắt đầu ngay hôm nay
Lập tài khoản Roboflow (free tier là đủ)
Tạo thư mục D:\CapsoneProject\VN_DATASET_500\raw\
 Ra ngoài chụp 50 ảnh TRASH đầu tiên để test workflow label
Upload 50 ảnh lên Roboflow → thử Auto-Label → kiểm tra chất lượng
Nếu ổn → tiếp tục chụp đủ 500

# Vietstock CW Daily Report Bot

Tự động crawl dữ liệu chứng quyền (CW) từ Vietstock, tính Premium/Đòn bẩy/Độ biến
động lịch sử, xuất 2 file Excel, cảnh báo CW sắp ngừng giao dịch, và gửi email tự
động hàng ngày lúc 16:00 (giờ VN), Thứ 2 - Thứ 6.

## Cấu trúc project (10 file)
vietstock-cw-bot/
├── .gitignore
├── requirements.txt
├── README.md
├── main.py                              ← orchestrator chạy toàn bộ pipeline
├── .github/workflows/daily_report.yml   ← cron job GitHub Actions
└── src/
├── scraper.py           ← Bước 1: crawl dữ liệu CW + lịch sử giá CKCS
├── calculator.py        ← Bước 2: tính Premium, Đòn bẩy, Volatility, cờ cảnh báo hết hạn
├── export_excel.py      ← Bước 3: xuất 2 file Excel theo mẫu PDF Yuanta
├── expiry_warning.py    ← Bước 3.5: tổng hợp danh sách CW sắp ngừng giao dịch
└── send_email.py        ← Bước 4: gửi email qua Gmail SMTP, kèm cảnh báo

## Cài đặt local để test trước khi đẩy lên GitHub (tùy chọn)

```bash
pip install -r requirements.txt

export GMAIL_USER="ban@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
export ANALYST_EMAIL="analyst1@company.com,analyst2@company.com"
export YOUR_EMAIL="ban@gmail.com"   # tùy chọn, để CC cho chính bạn

python main.py
```

Kiểm tra thư mục `output/` sẽ có 2 file Excel, và email sẽ được gửi nếu cấu hình đúng.

## Tạo Gmail App Password (bắt buộc, không dùng mật khẩu Gmail thường)

1. Vào [myaccount.google.com/security](https://myaccount.google.com/security)
2. Bật **"Xác minh 2 bước"** (2-Step Verification) — bắt buộc phải bật trước
3. Vào **"Mật khẩu ứng dụng"** (App passwords) → chọn app "Mail" → tạo mới
4. Copy chuỗi 16 ký tự (dạng `xxxx xxxx xxxx xxxx`) — đây là `GMAIL_APP_PASSWORD`

## Cấu hình GitHub Secrets (bắt buộc trước khi cron chạy được)

Vào repo trên GitHub → **Settings → Secrets and variables → Actions → New repository secret**,
thêm 4 secrets sau:

| Secret name           | Giá trị                                                    |
|------------------------|-------------------------------------------------------------|
| `GMAIL_USER`           | Địa chỉ Gmail dùng để gửi (VD: `bot.ysvn@gmail.com`)         |
| `GMAIL_APP_PASSWORD`   | App Password 16 ký tự vừa tạo ở bước trên                    |
| `ANALYST_EMAIL`        | Email bộ phận phân tích, cách nhau bằng dấu phẩy nếu nhiều   |
| `YOUR_EMAIL`           | Email của bạn (tùy chọn, để nhận CC cùng nội dung cảnh báo)  |

## Kiểm tra cron hoạt động

- Cron được cấu hình chạy `0 9 * * 1-5` (UTC) = 16:00 giờ VN, Thứ 2 - Thứ 6.
- Để test ngay không cần đợi tới giờ: vào tab **Actions** trên GitHub → chọn
  workflow "Daily CW Report" → **Run workflow** (nút màu xanh, chạy thủ công).
- File Excel mỗi lần chạy cũng được lưu làm **Artifact** trong 30 ngày,
  xem tại tab Actions → chọn lần chạy → phần "Artifacts" ở cuối trang.

## Lưu ý về độ trễ GitHub Actions cron

GitHub Actions cron có thể trễ 5-15 phút so với giờ đặt (do tải hệ thống chung
của GitHub), đây là giới hạn của nền tảng, không phải lỗi code. Nếu cần độ chính
xác cao hơn, có thể cân nhắc dùng external cron service (VD: cron-job.org) để
gọi `workflow_dispatch` qua GitHub API — nhưng với báo cáo hàng ngày, độ trễ vài
phút thường không ảnh hưởng.

## Cảnh báo CW sắp ngừng giao dịch

Mỗi lần chạy, hệ thống tự động kiểm tra các mã CW có **≤ 2 ngày làm việc** còn lại
trước khi ngừng giao dịch (dựa trên "Ngày giao dịch cuối cùng", không phải ngày
đáo hạn). Danh sách này được:
1. In ra log của GitHub Actions (xem trong tab Actions → chi tiết lần chạy)
2. Chèn vào cuối nội dung email chính (bảng cảnh báo màu đỏ/cam)

Để đổi ngưỡng cảnh báo (VD: 3 ngày thay vì 2), sửa tham số `threshold_sessions`
trong hàm `is_about_to_expire()` tại `src/calculator.py`.

## Troubleshooting

**Email không gửi được, lỗi "SMTPAuthenticationError"**
→ Kiểm tra lại đã dùng App Password (16 ký tự), không phải mật khẩu Gmail thường.

**Crawl bị chặn / trả về ít mã hơn bình thường**
→ Vietstock có thể tạm thời chặn IP của GitHub Actions runner. Giảm `MAX_WORKERS`
trong `src/scraper.py` xuống 5, hoặc thêm delay lớn hơn.

**Workflow không tự chạy đúng giờ**
→ Đảm bảo repo không ở trạng thái "inactive" (GitHub tự tắt cron nếu repo không
có commit nào trong 60 ngày). Thỉnh thoảng commit nhỏ để giữ repo active.

**Cột "Số phiên còn lại" hiện trống dù CW sắp đáo hạn**
→ Đã sửa lỗi này (falsy-zero bug): giá trị 0 phiên (nghĩa là hôm nay là ngày
giao dịch cuối cùng) trước đây bị hiểu nhầm thành "không có dữ liệu". Nếu vẫn
gặp lại, kiểm tra hàm `build_table1_df()` trong `src/export_excel.py` dùng
đúng `is not None` thay vì `or`.

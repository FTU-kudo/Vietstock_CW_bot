# 🌐 Vietstock CW Dashboard

🤖 Tự động crawl dữ liệu chứng quyền (CW) từ Vietstock hàng ngày, tính Premium/Đòn bẩy/Độ biến động lịch sử, phát hiện mã mới niêm yết và mã sắp ngừng giao dịch, rồi publish lên **GitHub Pages** dưới dạng dashboard xem trực tiếp trên trình duyệt.

🔗 **Dashboard:** `https://ftu-kudo.github.io/Vietstock_CW_bot/`

## 📁 Cấu trúc project

```
vietstock-cw-bot/
├── .gitignore
├── requirements.txt
├── README.md
├── main.py                              ← orchestrator chạy toàn bộ pipeline
├── .github/workflows/daily_report.yml   ← cron job GitHub Actions
├── data/
│   └── last_active_codes.json           ← snapshot mã CW (để phát hiện mã mới)
├── docs/                                 ← nguồn của GitHub Pages
│   ├── .nojekyll                         ← BẮT BUỘC, xem mục Troubleshooting
│   ├── index.html
│   ├── style.css
│   ├── app.js                            ← toàn bộ logic dashboard (vanilla JS)
│   ├── data/
│   │   ├── index.json                    ← danh sách các ngày có dữ liệu
│   │   └── daily/
│   │       └── YYYYMMDD.json             ← snapshot đầy đủ 1 ngày (tích lũy dần)
│   └── downloads/
│       ├── KetQuaGiaoDich_latest.xlsx    ← luôn là bản mới nhất, ghi đè mỗi ngày
│       └── ThongTinChungQuyen_latest.xlsx
└── src/
    ├── scraper.py           ← Bước 1: crawl dữ liệu CW + lịch sử giá CKCS
    ├── calculator.py        ← Bước 2: Premium, Đòn bẩy, Volatility, cờ cảnh báo hết hạn
    ├── export_excel.py      ← Bước 3: xuất 2 file Excel theo mẫu PDF Yuanta
    ├── expiry_warning.py    ← Bước 3.5: lọc danh sách CW sắp ngừng giao dịch
    ├── new_listing.py       ← Bước 3.6: phát hiện CW mới niêm yết
    └── export_json.py       ← Bước 3.7: xuất JSON cho dashboard
```
 
## ⚙️ Cách hoạt động

Mỗi lần chạy (python main.py), pipeline thực hiện tuần tự:
1. 🕷️ Crawl toàn bộ mã CW đang giao dịch từ Vietstock (21 cổ phiếu cơ sở × 2 năm × 50 đợt phát hành)
2. 📈 Crawl thêm lịch sử giá 30 phiên gần nhất của các cổ phiếu cơ sở, để tính độ biến động
3. 🧮 Tính Premium, Đòn bẩy, Trạng thái tiền (ITM/OTM/ATM), Độ biến động lịch sử
4. 📊 Xuất 2 file Excel (KetQuaGiaoDich_YYYYMMDD.xlsx, ThongTinChungQuyen_YYYYMMDD.xlsx)
5. ⏰ Lọc ra các mã sắp ngừng giao dịch (≤2 ngày làm việc)
6. 🆕 So sánh với snapshot hôm qua để tìm mã mới niêm yết
7. 📦 Xuất dữ liệu JSON cho dashboard, cập nhật index, publish bản Excel mới nhất vào docs/downloads/

Workflow GitHub Actions sau đó commit toàn bộ dữ liệu mới (data/, docs/data/, docs/downloads/) ngược lại vào repo — GitHub Pages tự động phát hiện commit mới và cập nhật trang trong vài phút.

## 🚀 Cài đặt lần đầu

### 1. Bật GitHub Pages

**Settings → Pages** → Source: **"Deploy from a branch"** → Branch: `main`, thư mục **`/docs`** → Save.

### 2. Không cần cấu hình Secret nào

Khác với phiên bản dùng email trước đây, bản hiện tại **không cần bất kỳ GitHub Secret nào** (đã bỏ Gmail App Password) — pipeline chỉ cần quyền ghi vào repo (`contents: write`, đã khai báo sẵn trong workflow) để tự commit dữ liệu.

### 3. Chạy thử

Vào tab **Actions** → chọn "Daily CW Report" → **Run workflow**. Chạy **2 lần liên tiếp** để tính năng "mã mới niêm yết" hoạt động đầy đủ (lần đầu chỉ tạo baseline, lần 2 mới có để so sánh).

## 🕒 Lịch chạy tự động

Cron: `13 9 * * 1-5` (UTC) = **16:13 giờ Việt Nam, Thứ 2 - Thứ 6**. Phút được cố ý lệch khỏi mốc `:00` để tránh giờ cao điểm của GitHub Actions (đầu mỗi giờ là lúc cron dễ bị trễ nhiều nhất theo công bố của GitHub).

## 📊 Tính năng dashboard

- 📅 **Chọn ngày**: dropdown góc trên phải, xem lại bất kỳ ngày nào đã có dữ liệu
- 🏷️ **Thẻ tóm tắt**: tổng CW, ITM, OTM, mã mới niêm yết, mã sắp ngừng giao dịch
- 🔍 **Tìm kiếm**: theo mã CW hoặc mã cổ phiếu cơ sở
- 🎛️ **Lọc**: ITM/OTM, chỉ mã mới, chỉ mã sắp ngừng giao dịch
- 🔽 **Sắp xếp**: click vào tiêu đề cột bất kỳ
- 📥 **Tải Excel**: 2 link tải bản mới nhất, luôn trỏ đúng ngày gần nhất (không cần sửa link theo ngày)
- 🎨 Dòng **tô xanh** = mã mới niêm yết hôm đó; dòng **tô cam** = sắp ngừng giao dịch

## 📦 Về phạm vi lưu trữ dữ liệu

Dữ liệu **tích lũy dần từ ngày triển khai trở đi** — không backfill lịch sử 2020-2025, vì Vietstock không cung cấp lại đầy đủ giá đóng cửa hàng ngày cho các CW đã đáo hạn từ lâu qua giao diện HTML thông thường (trang "Thống kê giao dịch" chỉ giữ ~30 phiên gần nhất). Theo thời gian, kho dữ liệu trong `docs/data/daily/` sẽ dày dần lên tới mục tiêu lưu trữ nhiều năm.

## 🔧 Troubleshooting

**🖥️ Dashboard báo "Lỗi tải dữ liệu: Không tải được data/index.json"**
→ Kiểm tra file `docs/.nojekyll` (rỗng) có tồn tại chưa. Thiếu file này, GitHub Pages chạy qua Jekyll trước khi publish, có thể xử lý sai hoặc bỏ sót thư mục `docs/data/`.
Đây là nguyên nhân phổ biến nhất — nếu vẫn lỗi sau khi thêm `.nojekyll`, kiểm tra tiếp bước "Commit updated data to repo" trong log Actions có thành công không.

**📎 Link "Tải Excel" không tải được gì**
→ Kiểm tra `.gitignore` không còn dòng `*.xlsx` (dòng này sẽ chặn Git commit file Excel trong `docs/downloads/`, kể cả khi workflow gọi `git add` tường minh — Git luôn tôn trọng `.gitignore`). Sau khi sửa, phải **chạy lại workflow** thì file Excel mới thực sự được tạo và commit — sửa `.gitignore` không tự hồi tố dữ liệu cũ.

**⏳  Cột "Số phiên còn lại" hoặc cờ "sắp ngừng giao dịch" bị bỏ sót**
→ Vietstock đôi khi đổi cấu trúc trang CW ngay sau giờ đóng cửa đối với mã đáo hạn trong ngày, khiến trường "Ngày giao dịch cuối cùng" đọc trượt. `calculator.py` đã có cơ chế dự phòng: dùng "Ngày đáo hạn" làm nguồn thứ 2 nếu nguồn chính không đọc được (xem docstring hàm `is_about_to_expire`).

**📄 Dữ liệu Excel bị dồn chữ lộn xộn (text từ nhiều dòng dính vào 1 ô)**
→ Đã fix trong `scraper.py` (hàm `_clean_cell`) — do HTML của Vietstock không đóng thẻ `<tr>` chuẩn, khiến BeautifulSoup lồng nhầm nội dung dòng sau vào dòng trước.

**⏰ Workflow không tự chạy đúng giờ / cron bị trễ nhiều**
→ GitHub Actions cron là "best-effort", có thể trễ tới hàng chục phút, đặc biệt nếu đặt đúng mốc `:00`. Repo cũng cần có hoạt động (commit) thường xuyên — GitHub tự tắt cron nếu repo không có commit nào trong 60 ngày liên tục.

**🕸️ Crawl trả về 0 mã hoặc rất ít so với bình thường**
→ Khả năng cao Vietstock đã đổi cấu trúc HTML trang CW. Kiểm tra file `chung-khoan-phai-sinh/{ma}/cw-tong-quan.htm` của 1 mã bất kỳ, so sánh với selector đang dùng trong `src/scraper.py` (`h1.h1-title`, `#stockprice`, `.short-doc table`,...).

## 📜 Lịch sử phát triển (tóm tắt)

Dự án ban đầu gửi báo cáo qua email (Gmail SMTP), sau đó chuyển hẳn sang GitHub Pages theo yêu cầu của bộ phận phân tích. Nếu thấy file `src/send_email.py` còn tồn tại trong repo, đó là code cũ không còn được `main.py` gọi tới — có thể xóa an toàn, hoặc giữ lại làm tham khảo nếu muốn khôi phục kênh email trong tương lai.

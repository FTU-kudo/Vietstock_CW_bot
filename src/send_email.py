# ============================================================
# SEND_EMAIL.PY
# Gửi 2 file Excel đính kèm qua Gmail SMTP, dùng App Password.
#
# Yêu cầu cấu hình GitHub Secrets (Settings → Secrets → Actions):
#   GMAIL_USER          : địa chỉ Gmail dùng để gửi (VD: bot@gmail.com)
#   GMAIL_APP_PASSWORD  : App Password 16 ký tự (KHÔNG phải mật khẩu Gmail thường)
#   ANALYST_EMAIL       : 1 hoặc nhiều email người nhận, phân tách bằng dấu phẩy
#   YOUR_EMAIL          : (tùy chọn) email của bạn, nhận CC cùng nội dung
#
# Cách tạo App Password:
#   1. Vào myaccount.google.com/security
#   2. Bật "Xác minh 2 bước" (bắt buộc phải có trước)
#   3. Vào "Mật khẩu ứng dụng" (App passwords) → tạo mới → chọn "Mail"
#   4. Copy 16 ký tự, dán vào GitHub Secret GMAIL_APP_PASSWORD
# ============================================================

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import date


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def build_email_body(report_date: date, total_active: int,
                      total_itm: int, total_otm: int,
                      expiry_warning_html: str = "") -> str:
    """Soạn nội dung email (HTML). expiry_warning_html được chèn vào cuối."""
    date_str = report_date.strftime("%d/%m/%Y")
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px;">
        <p>Kính gửi Bộ phận phân tích,</p>
        <p>Hệ thống tự động đã hoàn thành crawl dữ liệu chứng quyền (CW)
        ngày <b>{date_str}</b>. Vui lòng xem 2 file Excel đính kèm:</p>
        <ul>
            <li><b>KetQuaGiaoDich_{report_date.strftime('%Y%m%d')}.xlsx</b>
                — Kết quả giao dịch và các chỉ số liên quan</li>
            <li><b>ThongTinChungQuyen_{report_date.strftime('%Y%m%d')}.xlsx</b>
                — Thông tin chi tiết các mã CW</li>
        </ul>
        <p><b>Tóm tắt nhanh:</b></p>
        <ul>
            <li>Tổng số CW còn giao dịch: <b>{total_active}</b></li>
            <li>Số CW đang ITM (trong tiền): <b>{total_itm}</b></li>
            <li>Số CW đang OTM (ngoài tiền): <b>{total_otm}</b></li>
        </ul>
        <hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">
        {expiry_warning_html}
        <hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">
        <p style="color:#888;font-size:12px;">
            Email này được gửi tự động bởi GitHub Actions, vui lòng không reply.
        </p>
        <p>Trân trọng.</p>
    </body>
    </html>
    """


def send_report_email(file_paths: list[str], report_date: date | None = None,
                       summary_stats: dict | None = None,
                       expiry_warning_html: str = "") -> bool:
    """
    Gửi email kèm các file Excel.

    file_paths: list đường dẫn file cần đính kèm
    summary_stats: dict {"total_active": int, "total_itm": int, "total_otm": int}
    expiry_warning_html: đoạn HTML cảnh báo CW sắp ngừng giao dịch,
                         được chèn vào cuối email chính (xem src/expiry_warning.py)

    Người nhận chính: ANALYST_EMAIL (bộ phận phân tích)
    CC thêm: YOUR_EMAIL (bạn — người vận hành hệ thống) nếu có khai báo,
             để nhận cùng nội dung cảnh báo trong 1 email duy nhất.

    Trả về True nếu gửi thành công, False nếu lỗi (lỗi sẽ được in ra console,
    không raise exception để không làm fail toàn bộ GitHub Action job).
    """
    if report_date is None:
        report_date = date.today()
    if summary_stats is None:
        summary_stats = {"total_active": 0, "total_itm": 0, "total_otm": 0}

    gmail_user     = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    analyst_emails = os.environ.get("ANALYST_EMAIL", "")
    your_email     = os.environ.get("YOUR_EMAIL", "")  # tùy chọn, để nhận CC

    if not gmail_user or not gmail_password:
        print("✗ Lỗi: Thiếu GMAIL_USER hoặc GMAIL_APP_PASSWORD trong environment variables")
        return False
    if not analyst_emails:
        print("✗ Lỗi: Thiếu ANALYST_EMAIL trong environment variables")
        return False

    to_list = [e.strip() for e in analyst_emails.split(",") if e.strip()]
    if not to_list:
        print("✗ Lỗi: ANALYST_EMAIL rỗng sau khi parse")
        return False

    cc_list = [e.strip() for e in your_email.split(",") if e.strip()]
    all_recipients = to_list + [c for c in cc_list if c not in to_list]

    msg = MIMEMultipart()
    msg["From"]    = gmail_user
    msg["To"]      = ", ".join(to_list)
    if cc_list:
        msg["Cc"]  = ", ".join(cc_list)
    msg["Subject"] = f"[Tự động] Báo cáo Chứng quyền {report_date.strftime('%d/%m/%Y')}"

    body_html = build_email_body(
        report_date,
        summary_stats.get("total_active", 0),
        summary_stats.get("total_itm", 0),
        summary_stats.get("total_otm", 0),
        expiry_warning_html=expiry_warning_html,
    )
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    for path in file_paths:
        if not os.path.exists(path):
            print(f"⚠ File không tồn tại, bỏ qua: {path}")
            continue
        with open(path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
        msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, all_recipients, msg.as_string())
        print(f"✅ Đã gửi email thành công đến: {', '.join(to_list)}"
              + (f" (CC: {', '.join(cc_list)})" if cc_list else ""))
        return True
    except smtplib.SMTPAuthenticationError:
        print("✗ Lỗi xác thực Gmail. Kiểm tra lại GMAIL_USER và GMAIL_APP_PASSWORD.")
        print("  (Nhắc: phải dùng App Password 16 ký tự, không phải mật khẩu Gmail thường)")
        return False
    except Exception as e:
        print(f"✗ Lỗi gửi email: {e}")
        return False


if __name__ == "__main__":
    # Test cục bộ: cần set env var trước khi chạy
    #   export GMAIL_USER="ban@gmail.com"
    #   export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
    #   export ANALYST_EMAIL="analyst1@company.com,analyst2@company.com"
    #   export YOUR_EMAIL="ban@gmail.com"   (tùy chọn, để nhận CC)
    test_files = ["/tmp/KetQuaGiaoDich_20260625.xlsx", "/tmp/ThongTinChungQuyen_20260625.xlsx"]
    fake_warning_html = """
    <p style="color:#c62828;font-weight:bold;">⚠ Có 2 mã CW sắp ngừng giao dịch:</p>
    <p>CACB2510 (còn 1 phiên), CFPT2521 (còn 0 phiên)</p>
    """
    ok = send_report_email(
        test_files,
        summary_stats={"total_active": 246, "total_itm": 58, "total_otm": 188},
        expiry_warning_html=fake_warning_html,
    )
    print("Kết quả gửi:", "Thành công" if ok else "Thất bại")

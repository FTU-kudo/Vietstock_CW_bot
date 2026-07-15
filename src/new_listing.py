# ============================================================
# NEW_LISTING.PY
# Phát hiện CW mới niêm yết bằng cách so sánh danh sách mã CW
# đang active hôm nay với danh sách đã lưu từ lần chạy trước.
#
# Cơ chế lưu trữ: file JSON trong repo (data/last_active_codes.json),
# được commit lại sau mỗi lần chạy để lần chạy kế tiếp có dữ liệu
# so sánh. Xem bước "Commit updated CW codes snapshot" trong
# .github/workflows/daily_report.yml.
# ============================================================

import json
from pathlib import Path
from datetime import date


DEFAULT_HISTORY_FILE = "data/last_active_codes.json"


def load_previous_codes(filepath: str = DEFAULT_HISTORY_FILE) -> set[str] | None:
    """
    Đọc danh sách mã CW active từ lần chạy trước.
    Trả về None nếu file chưa tồn tại (lần chạy đầu tiên) -- để
    main.py biết mà KHÔNG báo "mã mới" tràn lan ở lần chạy đầu.
    """
    path = Path(filepath)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            codes = json.load(f)
        return set(codes)
    except (json.JSONDecodeError, OSError):
        return None


def save_current_codes(records: list[dict], filepath: str = DEFAULT_HISTORY_FILE) -> None:
    """Lưu danh sách mã CW active hôm nay, để lần chạy sau so sánh."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    codes = sorted({r["ma_cw"] for r in records if r.get("ma_cw")})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)


def find_new_listings(current_records: list[dict],
                       previous_codes: set[str] | None) -> list[dict]:
    """
    So sánh danh sách hiện tại với danh sách trước đó.
    Trả về list record của các mã CW MỚI xuất hiện.

    Nếu previous_codes là None (không có dữ liệu lần trước, VD lần
    chạy đầu tiên sau khi triển khai tính năng này), trả về list rỗng
    -- tránh báo toàn bộ danh sách hiện có là "mới".
    """
    if previous_codes is None:
        return []
    new_records = [r for r in current_records
                   if r.get("ma_cw") and r["ma_cw"] not in previous_codes]
    new_records.sort(key=lambda r: r.get("ma_cw", ""))
    return new_records


def build_new_listing_html(new_records: list[dict],
                            report_date: date | None = None) -> str:
    """
    Soạn đoạn HTML liệt kê các mã CW mới niêm yết, để chèn vào email.
    Trả về chuỗi rỗng nếu không có mã mới (không hiện block này trong
    email những ngày bình thường, khác với bảng cảnh báo sắp hết hạn
    luôn hiện dòng "không có mã nào").
    """
    if report_date is None:
        report_date = date.today()

    if not new_records:
        return ""

    rows_html = ""
    for r in new_records:
        ma_cw          = r.get("ma_cw", "-")
        ck_co_so       = r.get("ck_co_so", "-")
        to_chuc        = r.get("to_chuc_ph_cw", "-")
        ngay_niem_yet  = r.get("ngay_niem_yet", "-")
        ngay_gd_dau    = r.get("ngay_gd_dau_tien", "-")
        gia_thuc_hien  = r.get("gia_thuc_hien", "-")
        ty_le          = r.get("ty_le_chuyen_doi", "-")

        rows_html += f"""
        <tr>
            <td style="padding:6px 10px;border:1px solid #ddd;font-weight:bold;">{ma_cw}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;">{ck_co_so}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;">{to_chuc}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;">{ngay_niem_yet}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;">{ngay_gd_dau}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:right;">{gia_thuc_hien}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;">{ty_le}</td>
        </tr>
        """

    return f"""
    <p style="color:#2e7d32;font-weight:bold;">
        🆕 Có {len(new_records)} mã CW mới niêm yết:
    </p>
    <table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px;width:100%;">
        <thead>
            <tr style="background-color:#2e7d32;color:white;">
                <th style="padding:6px 10px;border:1px solid #ddd;">Mã CW</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">CKCS</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">TCPH</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">Ngày niêm yết</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">Ngày GD đầu tiên</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">Giá thực hiện</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">Tỷ lệ chuyển đổi</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """


if __name__ == "__main__":
    previous = {"CACB2510", "CACB2511", "CFPT2518"}
    current_records = [
        {"ma_cw": "CACB2510", "ck_co_so": "ACB"},
        {"ma_cw": "CACB2511", "ck_co_so": "ACB"},
        {"ma_cw": "CFPT2518", "ck_co_so": "FPT"},
        {"ma_cw": "CMSN2620", "ck_co_so": "MSN", "to_chuc_ph_cw": "SSI",
         "ngay_niem_yet": "15/07/2026", "ngay_gd_dau_tien": "17/07/2026",
         "gia_thuc_hien": "95,000", "ty_le_chuyen_doi": "5 : 1"},
        {"ma_cw": "CTPB2610", "ck_co_so": "TPB", "to_chuc_ph_cw": "VND",
         "ngay_niem_yet": "15/07/2026", "ngay_gd_dau_tien": "17/07/2026",
         "gia_thuc_hien": "20,000", "ty_le_chuyen_doi": "3 : 1"},
    ]

    new_ones = find_new_listings(current_records, previous)
    print(f"Số mã mới: {len(new_ones)}")
    for r in new_ones:
        print(f"  {r['ma_cw']}")

    html = build_new_listing_html(new_ones)
    print("\n--- HTML preview ---")
    print(html[:400])

    new_ones_first_run = find_new_listings(current_records, None)
    print(f"\nLần chạy đầu tiên (không có lịch sử): {len(new_ones_first_run)} mã mới (phải = 0)")

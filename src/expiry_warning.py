# ============================================================
# EXPIRY_WARNING.PY
# Tổng hợp danh sách CW sắp ngừng giao dịch (<=2 ngày làm việc)
# để chèn vào cuối email báo cáo chính.
# ============================================================

from datetime import date


def get_expiring_soon_list(enriched_records: list[dict]) -> list[dict]:
    """
    Lọc ra các CW có cờ sap_ngung_gd = True.
    Trả về list đã sắp xếp theo so_phien_con_lai tăng dần
    (mã nào sắp ngừng nhất lên đầu).
    """
    expiring = [r for r in enriched_records if r.get("sap_ngung_gd")]
    expiring.sort(key=lambda r: (r.get("so_phien_con_lai") is None,
                                  r.get("so_phien_con_lai", 999)))
    return expiring


def build_expiry_warning_html(expiring_records: list[dict],
                               report_date: date | None = None) -> str:
    """Soạn đoạn HTML liệt kê các mã sắp ngừng giao dịch, để chèn vào email."""
    if report_date is None:
        report_date = date.today()

    if not expiring_records:
        return """
        <p style="color:#2e7d32;">
            ✅ Không có mã CW nào sắp ngừng giao dịch trong 2 phiên tới.
        </p>
        """

    rows_html = ""
    for r in expiring_records:
        ma_cw       = r.get("ma_cw", "-")
        so_phien    = r.get("so_phien_con_lai", "-")
        ngay_gd     = r.get("ngay_gd_cuoi_cung", "-")
        gia         = r.get("gia_hien_tai", "-")
        trang_thai  = r.get("trang_thai_tien") or r.get("trang_thai_cw") or "-"
        to_chuc     = r.get("to_chuc_ph_cw", "-")

        badge_color = "#c62828" if so_phien == 0 else "#e65100"
        rows_html += f"""
        <tr>
            <td style="padding:6px 10px;border:1px solid #ddd;font-weight:bold;">{ma_cw}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;
                       color:{badge_color};font-weight:bold;">{so_phien}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;">{ngay_gd}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:right;">{gia}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;">{trang_thai}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;">{to_chuc}</td>
        </tr>
        """

    return f"""
    <p style="color:#c62828;font-weight:bold;">
        ⚠ Có {len(expiring_records)} mã CW sắp ngừng giao dịch (≤ 2 ngày làm việc):
    </p>
    <table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px;width:100%;">
        <thead>
            <tr style="background-color:#1F6FB2;color:white;">
                <th style="padding:6px 10px;border:1px solid #ddd;">Mã CW</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">Số phiên còn lại</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">Ngày GD cuối cùng</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">Giá hiện tại</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">Trạng thái</th>
                <th style="padding:6px 10px;border:1px solid #ddd;">TCPH</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """


if __name__ == "__main__":
    sample = [
        {"ma_cw": "CACB2510", "so_phien_con_lai": 1, "ngay_gd_cuoi_cung": "19/06/2026",
         "gia_hien_tai": 1690, "trang_thai_tien": "ITM", "to_chuc_ph_cw": "SSI",
         "sap_ngung_gd": True},
        {"ma_cw": "CFPT2521", "so_phien_con_lai": 0, "ngay_gd_cuoi_cung": "19/06/2026",
         "gia_hien_tai": 150, "trang_thai_tien": "OTM", "to_chuc_ph_cw": "PHS",
         "sap_ngung_gd": True},
        {"ma_cw": "CVHM2523", "so_phien_con_lai": 98, "ngay_gd_cuoi_cung": "14/10/2026",
         "gia_hien_tai": 5140, "trang_thai_tien": "ITM", "to_chuc_ph_cw": "Kafi",
         "sap_ngung_gd": False},
    ]

    expiring = get_expiring_soon_list(sample)
    print(f"Số mã sắp ngừng: {len(expiring)}")
    for r in expiring:
        print(f"  {r['ma_cw']}: còn {r['so_phien_con_lai']} phiên")

    html = build_expiry_warning_html(expiring)
    print("\n--- HTML preview (rút gọn) ---")
    print(html[:300])

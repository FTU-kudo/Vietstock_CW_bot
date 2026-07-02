# ============================================================
# CALCULATOR.PY
# Tính các chỉ số: Premium, Đòn bẩy, Trạng thái tiền,
# Độ biến động lịch sử (historical volatility) của CKCS,
# và cờ cảnh báo CW sắp ngừng giao dịch.
#
# Công thức tham khảo từ "Bản tin chứng quyền" - Yuanta:
#   Premium = (Giá thực hiện + Giá CW x Tỷ lệ chuyển đổi - Giá CKCS)
#             / Giá CKCS
#   Đòn bẩy (Effective Gearing) = (Giá CKCS / Giá CW) x (1 / Tỷ lệ chuyển đổi)
#   Trạng thái tiền (Moneyness):
#       ITM (In the Money)  : Giá CKCS > Giá thực hiện  (với CW mua)
#       OTM (Out of Money)  : Giá CKCS < Giá thực hiện
#       ATM (At the Money)  : Giá CKCS ≈ Giá thực hiện
# ============================================================

import math
import statistics
from datetime import date


# ── PREMIUM ──────────────────────────────────────────────────

def calc_premium(gia_ckcs: float, gia_thuc_hien: float,
                  gia_cw: float, ty_le_chuyen_doi: float) -> float | None:
    """
    Premium (%) = (Giá hòa vốn - Giá CKCS) / Giá CKCS
    Giá hòa vốn = Giá thực hiện + Giá CW x Tỷ lệ chuyển đổi

    Trả về tỷ lệ % (VD: 10.5 nghĩa là 10.5%), hoặc None nếu thiếu dữ liệu.
    """
    if not all([gia_ckcs, gia_thuc_hien, gia_cw, ty_le_chuyen_doi]):
        return None
    if gia_ckcs <= 0 or ty_le_chuyen_doi <= 0:
        return None

    gia_hoa_von = gia_thuc_hien + gia_cw * ty_le_chuyen_doi
    premium = (gia_hoa_von - gia_ckcs) / gia_ckcs * 100
    return round(premium, 2)


# ── ĐÒN BẨY (EFFECTIVE GEARING) ─────────────────────────────

def calc_don_bay(gia_ckcs: float, gia_cw: float,
                  ty_le_chuyen_doi: float) -> float | None:
    """
    Đòn bẩy = (Giá CKCS / Giá CW) / Tỷ lệ chuyển đổi

    Ý nghĩa: Giá CW sẽ biến động bao nhiêu % khi CKCS biến động 1%.
    Đòn bẩy cao = rủi ro/lợi nhuận cao hơn.
    """
    if not all([gia_ckcs, gia_cw, ty_le_chuyen_doi]):
        return None
    if gia_cw <= 0 or ty_le_chuyen_doi <= 0:
        return None

    don_bay = (gia_ckcs / gia_cw) / ty_le_chuyen_doi
    return round(don_bay, 2)


# ── TRẠNG THÁI TIỀN (MONEYNESS) ─────────────────────────────

def calc_trang_thai_tien(gia_ckcs: float, gia_thuc_hien: float,
                          threshold_pct: float = 1.0) -> str | None:
    """
    Trạng thái tiền cho CW MUA (Call Warrant):
        ITM: Giá CKCS > Giá thực hiện x (1 + threshold)
        OTM: Giá CKCS < Giá thực hiện x (1 - threshold)
        ATM: nằm giữa hai mức trên

    threshold_pct: biên độ % coi là "ngang giá" (mặc định 1%)
    """
    if not gia_ckcs or not gia_thuc_hien or gia_thuc_hien <= 0:
        return None

    diff_pct = (gia_ckcs - gia_thuc_hien) / gia_thuc_hien * 100

    if diff_pct > threshold_pct:
        return "ITM"
    elif diff_pct < -threshold_pct:
        return "OTM"
    else:
        return "ATM"


# ── SỐ PHIÊN GIAO DỊCH CÒN LẠI ──────────────────────────────

def calc_so_phien_con_lai(ngay_gd_cuoi_cung: date, today: date) -> int | None:
    """
    Đếm số ngày làm việc (Thứ 2-6) từ hôm nay đến ngày giao dịch cuối cùng.
    Đây là ước tính đơn giản (không trừ ngày lễ).
    """
    if not ngay_gd_cuoi_cung or ngay_gd_cuoi_cung < today:
        return 0

    total_days = (ngay_gd_cuoi_cung - today).days
    if total_days <= 0:
        return 0

    full_weeks, remainder = divmod(total_days, 7)
    business_days = full_weeks * 5

    current_weekday = today.weekday()  # 0=Mon ... 6=Sun
    for i in range(1, remainder + 1):
        wd = (current_weekday + i) % 7
        if wd < 5:  # Mon-Fri
            business_days += 1

    return business_days


# ── CẢNH BÁO CW SẮP NGỪNG GIAO DỊCH ─────────────────────────

def is_about_to_expire(so_phien_con_lai: int | None,
                        threshold_sessions: int = 2) -> bool:
    """
    Đánh dấu CW "sắp ngừng giao dịch" nếu số phiên giao dịch còn lại
    <= threshold_sessions (mặc định 2 ngày làm việc).

    Lưu ý: đây là CẢNH BÁO TRƯỚC đáo hạn, khác với is_active() trong
    scraper.py (lọc CW đã hết hạn hẳn). Một CW có thể vừa active=True
    vừa about_to_expire=True (còn giao dịch nhưng sắp hết).
    """
    if so_phien_con_lai is None:
        return False
    return 0 <= so_phien_con_lai <= threshold_sessions


# ── ĐỘ BIẾN ĐỘNG LỊCH SỬ (HISTORICAL VOLATILITY) ───────────

def calc_historical_volatility(price_series: list[float],
                                trading_days_per_year: int = 252) -> float | None:
    """
    Tính độ biến động lịch sử (annualized) từ dãy giá đóng cửa.

    Công thức:
        1. Tính log-return: r_i = ln(P_i / P_{i-1})
        2. Tính độ lệch chuẩn (sample std) của log-return
        3. Annualize: sigma_year = std_daily * sqrt(252)

    price_series: list giá đóng cửa theo thứ tự thời gian tăng dần,
                  nên có ít nhất 20-30 phiên để kết quả ổn định.

    Trả về % (VD: 35.2 nghĩa là 35.2%/năm), hoặc None nếu không đủ dữ liệu.
    """
    if not price_series or len(price_series) < 10:
        return None

    clean_prices = [p for p in price_series if p and p > 0]
    if len(clean_prices) < 10:
        return None

    log_returns = []
    for i in range(1, len(clean_prices)):
        prev_price = clean_prices[i - 1]
        curr_price = clean_prices[i]
        if prev_price > 0 and curr_price > 0:
            log_returns.append(math.log(curr_price / prev_price))

    if len(log_returns) < 5:
        return None

    daily_std = statistics.stdev(log_returns)
    annualized_vol = daily_std * math.sqrt(trading_days_per_year) * 100
    return round(annualized_vol, 2)


# ── HÀM TỔNG HỢP: TÍNH TẤT CẢ CHỈ SỐ CHO 1 MÃ CW ───────────

def enrich_cw_record(record: dict, ckcs_price_history: list[float] | None,
                      today: date) -> dict:
    """
    Nhận 1 record CW (đã có từ scraper) + lịch sử giá CKCS,
    bổ sung các cột: premium, don_bay, trang_thai_tien,
    so_phien_con_lai, sap_ngung_gd, do_bien_dong_lich_su.
    """
    out = dict(record)  # copy, không sửa record gốc

    gia_cw = _to_float(record.get("gia_hien_tai"))
    gia_ckcs = _to_float(record.get("gia_ck_co_so"))

    gia_thuc_hien = (_to_float(record.get("gia_th_dieu_chinh"))
                      or _to_float(record.get("gia_thuc_hien")))

    ty_le = (_parse_ty_le(record.get("tlcd_dieu_chinh"))
             or _parse_ty_le(record.get("ty_le_chuyen_doi")))

    out["premium"] = calc_premium(gia_ckcs, gia_thuc_hien, gia_cw, ty_le)
    out["don_bay"] = calc_don_bay(gia_ckcs, gia_cw, ty_le)
    out["trang_thai_tien"] = calc_trang_thai_tien(gia_ckcs, gia_thuc_hien)

    ngay_gd_cuoi = record.get("_ngay_gd_cuoi_cung_date")
    out["so_phien_con_lai"] = calc_so_phien_con_lai(ngay_gd_cuoi, today) if ngay_gd_cuoi else None

    # Cờ cảnh báo: CW sắp ngừng giao dịch trong <= 2 ngày làm việc
    out["sap_ngung_gd"] = is_about_to_expire(out["so_phien_con_lai"])

    if ckcs_price_history:
        out["do_bien_dong_lich_su"] = calc_historical_volatility(ckcs_price_history)
    else:
        out["do_bien_dong_lich_su"] = None

    return out


# ── HELPER PARSE ─────────────────────────────────────────────

def _to_float(val) -> float | None:
    """Chuyển giá trị (có thể là str/int/float/None) thành float an toàn."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = str(val).strip().replace(",", "")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_ty_le(val) -> float | None:
    """
    Parse tỷ lệ chuyển đổi dạng "2 : 1" hoặc "1.7245 : 1" → trả về 2.0 hoặc 1.7245.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)

    text = str(val).strip()
    if ":" in text:
        try:
            left = text.split(":")[0].strip().replace(",", "")
            return float(left)
        except (ValueError, IndexError):
            return None
    return _to_float(text)


if __name__ == "__main__":
    sample = {
        "ma_cw": "CACB2510",
        "gia_hien_tai": "1690",
        "gia_ck_co_so": "22400",
        "gia_thuc_hien": "22,500",
        "ty_le_chuyen_doi": "2 : 1",
        "_ngay_gd_cuoi_cung_date": date(2026, 6, 19),
    }
    today = date(2026, 6, 18)

    enriched = enrich_cw_record(sample, ckcs_price_history=None, today=today)
    print("=== TEST enrich_cw_record ===")
    for k, v in enriched.items():
        print(f"  {k:25s} = {v}")

    print("\n=== TEST calc_historical_volatility ===")
    fake_prices = [22000, 22100, 21900, 22300, 22500, 22400, 22600,
                   22200, 22450, 22550, 22300, 22650, 22400, 22500]
    vol = calc_historical_volatility(fake_prices)
    print(f"  Historical volatility (annualized) = {vol}%")

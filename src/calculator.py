# ============================================================
# CALCULATOR.PY
# Tính các chỉ số: Premium, Đòn bẩy, Trạng thái tiền,
# Độ biến động lịch sử (historical volatility) của CKCS,
# và cờ cảnh báo CW sắp ngừng giao dịch.
# ============================================================

import math
import statistics
from datetime import date


def calc_premium(gia_ckcs, gia_thuc_hien, gia_cw, ty_le_chuyen_doi):
    if not all([gia_ckcs, gia_thuc_hien, gia_cw, ty_le_chuyen_doi]):
        return None
    if gia_ckcs <= 0 or ty_le_chuyen_doi <= 0:
        return None
    gia_hoa_von = gia_thuc_hien + gia_cw * ty_le_chuyen_doi
    return round((gia_hoa_von - gia_ckcs) / gia_ckcs * 100, 2)


def calc_don_bay(gia_ckcs, gia_cw, ty_le_chuyen_doi):
    if not all([gia_ckcs, gia_cw, ty_le_chuyen_doi]):
        return None
    if gia_cw <= 0 or ty_le_chuyen_doi <= 0:
        return None
    return round((gia_ckcs / gia_cw) / ty_le_chuyen_doi, 2)


def calc_trang_thai_tien(gia_ckcs, gia_thuc_hien, threshold_pct=1.0):
    if not gia_ckcs or not gia_thuc_hien or gia_thuc_hien <= 0:
        return None
    diff_pct = (gia_ckcs - gia_thuc_hien) / gia_thuc_hien * 100
    if diff_pct > threshold_pct:
        return "ITM"
    elif diff_pct < -threshold_pct:
        return "OTM"
    return "ATM"


def calc_so_phien_con_lai(target_date: date, today: date) -> int | None:
    """
    Đếm số ngày làm việc (Thứ 2-6) từ hôm nay đến target_date.
    Dùng chung cho cả "Ngày giao dịch cuối cùng" và "Ngày đáo hạn"
    (xem is_about_to_expire bên dưới để hiểu vì sao cần cả 2).
    """
    if not target_date or target_date < today:
        return 0
    total_days = (target_date - today).days
    if total_days <= 0:
        return 0
    full_weeks, remainder = divmod(total_days, 7)
    business_days = full_weeks * 5
    current_weekday = today.weekday()
    for i in range(1, remainder + 1):
        wd = (current_weekday + i) % 7
        if wd < 5:
            business_days += 1
    return business_days


def is_about_to_expire(so_phien_con_lai: int | None,
                        so_phien_du_phong: int | None = None,
                        threshold_sessions: int = 2) -> bool:
    """
    Đánh dấu "sắp ngừng giao dịch" nếu MỘT TRONG HAI tín hiệu sau đúng:
      - so_phien_con_lai: dựa vào "Ngày giao dịch cuối cùng" (nguồn chính)
      - so_phien_du_phong: dựa vào "Ngày đáo hạn" (nguồn dự phòng)

    LÝ DO CẦN 2 NGUỒN: Vietstock đôi khi đổi cấu trúc trang CW ngay sau
    giờ đóng cửa đối với các mã đáo hạn trong ngày, khiến trường "Ngày
    giao dịch cuối cùng" đọc trượt (None) ở đúng thời điểm cần cảnh báo
    nhất. Khi đó CW vẫn được đếm là active (nhờ is_active() trong
    scraper.py cũng có fallback tương tự dùng ngày đáo hạn), nhưng nếu
    is_about_to_expire() chỉ nhìn vào so_phien_con_lai (=None lúc đó)
    thì sẽ bỏ sót cảnh báo hoàn toàn -- CW biến mất khỏi danh sách active
    ở lần chạy kế tiếp mà không một lời báo trước.

    Dùng OR (không phải AND): chỉ cần MỘT nguồn cho thấy sắp hết hạn là
    đủ để cảnh báo -- thà cảnh báo hơi sớm còn hơn bỏ sót.
    """
    def _in_range(v):
        return v is not None and 0 <= v <= threshold_sessions
    return _in_range(so_phien_con_lai) or _in_range(so_phien_du_phong)


def calc_historical_volatility(price_series, trading_days_per_year=252):
    if not price_series or len(price_series) < 10:
        return None
    clean_prices = [p for p in price_series if p and p > 0]
    if len(clean_prices) < 10:
        return None
    log_returns = []
    for i in range(1, len(clean_prices)):
        prev, curr = clean_prices[i - 1], clean_prices[i]
        if prev > 0 and curr > 0:
            log_returns.append(math.log(curr / prev))
    if len(log_returns) < 5:
        return None
    daily_std = statistics.stdev(log_returns)
    return round(daily_std * math.sqrt(trading_days_per_year) * 100, 2)


def enrich_cw_record(record: dict, ckcs_price_history, today: date) -> dict:
    out = dict(record)

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

    # Nguồn dự phòng: ngày đáo hạn (xem docstring is_about_to_expire)
    ngay_dao_han = record.get("_ngay_dao_han_date")
    so_phien_du_phong = calc_so_phien_con_lai(ngay_dao_han, today) if ngay_dao_han else None

    out["sap_ngung_gd"] = is_about_to_expire(out["so_phien_con_lai"], so_phien_du_phong)

    out["do_bien_dong_lich_su"] = (calc_historical_volatility(ckcs_price_history)
                                    if ckcs_price_history else None)
    return out


def _to_float(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def _parse_ty_le(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    text = str(val).strip()
    if ":" in text:
        try:
            return float(text.split(":")[0].strip().replace(",", ""))
        except (ValueError, IndexError):
            return None
    return _to_float(text)


if __name__ == "__main__":
    # ── Test cơ bản (như trước) ──
    sample = {
        "ma_cw": "CACB2510", "gia_hien_tai": "1690", "gia_ck_co_so": "22400",
        "gia_thuc_hien": "22,500", "ty_le_chuyen_doi": "2 : 1",
        "_ngay_gd_cuoi_cung_date": date(2026, 6, 19),
        "_ngay_dao_han_date": date(2026, 6, 23),
    }
    today = date(2026, 6, 18)
    enriched = enrich_cw_record(sample, ckcs_price_history=None, today=today)
    assert enriched["sap_ngung_gd"] == True  # còn 1 phiên theo ngày GD cuối
    print("✅ Test cơ bản: sap_ngung_gd đúng khi ngày GD cuối cùng parse thành công")

    # ── Test tình huống lỗi thực tế: ngày GD cuối cùng KHÔNG parse được ──
    # (mô phỏng đúng lỗi 283 -> 281 không cảnh báo)
    sample_bug = {
        "ma_cw": "CMSN2606", "gia_hien_tai": "10", "gia_ck_co_so": "82000",
        "gia_thuc_hien": "82,000", "ty_le_chuyen_doi": "10 : 1",
        "_ngay_gd_cuoi_cung_date": None,  # <- parse lỗi, giống thực tế đã gặp
        "_ngay_dao_han_date": date(2026, 7, 24),  # đáo hạn còn 1 ngày nữa
    }
    today2 = date(2026, 7, 23)
    enriched_bug = enrich_cw_record(sample_bug, ckcs_price_history=None, today=today2)
    assert enriched_bug["so_phien_con_lai"] is None, "Đúng, nguồn chính không đọc được"
    assert enriched_bug["sap_ngung_gd"] == True, "PHẢI vẫn cảnh báo nhờ nguồn dự phòng!"
    print("✅ Test fix quan trọng: khi ngày GD cuối cùng None, "
          "vẫn cảnh báo đúng nhờ dùng ngày đáo hạn làm dự phòng")

    # ── Test: cả 2 nguồn đều None -> không cảnh báo (đúng, không đủ dữ liệu) ──
    sample_no_data = dict(sample_bug)
    sample_no_data["_ngay_dao_han_date"] = None
    enriched_no_data = enrich_cw_record(sample_no_data, ckcs_price_history=None, today=today2)
    assert enriched_no_data["sap_ngung_gd"] == False
    print("✅ Test: cả 2 nguồn đều thiếu -> không cảnh báo (đúng, tránh báo giả)")

    # ── Test: còn hạn dài -> không cảnh báo ──
    sample_far = dict(sample)
    sample_far["_ngay_gd_cuoi_cung_date"] = date(2026, 12, 1)
    sample_far["_ngay_dao_han_date"] = date(2026, 12, 5)
    enriched_far = enrich_cw_record(sample_far, ckcs_price_history=None, today=today)
    assert enriched_far["sap_ngung_gd"] == False
    print("✅ Test: còn hạn dài -> không cảnh báo (không báo giả)")

    print("\n✅ TẤT CẢ TEST PASS")

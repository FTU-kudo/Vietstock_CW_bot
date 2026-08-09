# ============================================================
# EXPORT_JSON.PY
# Xuất dữ liệu CW hàng ngày ra JSON để trang GitHub Pages đọc.
#
# 2 file được ghi/cập nhật mỗi lần chạy:
#   docs/data/daily/YYYYMMDD.json  -- snapshot đầy đủ của ngày hôm đó
#   docs/data/index.json           -- danh sách các ngày đã có dữ liệu
#                                      (để trang web biết có thể xem những
#                                      ngày nào, không cần liệt kê thư mục)
# ============================================================

import json
import shutil
from pathlib import Path
from datetime import date

from export_excel import calc_gtgd  # tái dùng công thức GTGD đã có


DEFAULT_DAILY_DIR   = "docs/data/daily"
DEFAULT_INDEX_FILE  = "docs/data/index.json"
DEFAULT_DOWNLOAD_DIR = "docs/downloads"


def _record_to_json_row(r: dict) -> dict:
    """
    Gộp thông tin từ 1 record đã enrich thành 1 dòng JSON phẳng,
    chứa đủ cột của cả 2 bảng Excel (Kết quả giao dịch + Thông tin CW).
    """
    gia = r.get("gia_hien_tai")
    klgd = r.get("klgd")
    return {
        "ma_cw":               r.get("ma_cw"),
        "ten_cw":              r.get("ten_cw"),
        "pct_thay_doi":        r.get("pct_thay_doi"),
        "gia_hien_tai":        gia,
        "klgd":                klgd,
        "gtgd_ty_vnd":         calc_gtgd(gia, klgd),
        "trang_thai_tien":     r.get("trang_thai_tien") or r.get("trang_thai_cw"),
        "premium":             r.get("premium"),
        "don_bay":             r.get("don_bay"),
        "so_phien_con_lai":    r.get("so_phien_con_lai"),
        "do_bien_dong_lich_su":r.get("do_bien_dong_lich_su"),
        "sap_ngung_gd":        bool(r.get("sap_ngung_gd")),
        "ck_co_so":            r.get("ck_co_so"),
        "to_chuc_ph_cw":       r.get("to_chuc_ph_cw"),
        "thoi_han":            r.get("thoi_han"),
        "ty_le_chuyen_doi":    r.get("ty_le_chuyen_doi"),
        "gia_phat_hanh":       r.get("gia_phat_hanh"),
        "kl_niem_yet":         r.get("kl_niem_yet"),
        "gia_thuc_hien":       r.get("gia_thuc_hien"),
        "ngay_gd_cuoi_cung":   r.get("ngay_gd_cuoi_cung"),
    }


def build_daily_snapshot(enriched_records: list[dict],
                          new_listing_codes: list[str],
                          today: date | None = None) -> dict:
    """
    Gom toàn bộ dữ liệu 1 ngày thành 1 dict sẵn sàng để json.dump().

    new_listing_codes: list mã CW mới niêm yết hôm nay (chỉ cần list mã,
                        không cần record đầy đủ -- dashboard tự tra trong
                        "records" theo mã).
    """
    if today is None:
        today = date.today()

    rows = [_record_to_json_row(r) for r in enriched_records]

    total_itm = sum(1 for r in rows if r["trang_thai_tien"] == "ITM")
    total_otm = sum(1 for r in rows if r["trang_thai_tien"] == "OTM")
    expiring_count = sum(1 for r in rows if r["sap_ngung_gd"])

    return {
        "date": today.isoformat(),
        "summary": {
            "total_active": len(rows),
            "total_itm": total_itm,
            "total_otm": total_otm,
            "new_listings_count": len(new_listing_codes),
            "expiring_soon_count": expiring_count,
        },
        "new_listings": sorted(new_listing_codes),
        "records": rows,
    }


def save_daily_snapshot(snapshot: dict, daily_dir: str = DEFAULT_DAILY_DIR) -> str:
    """Ghi snapshot vào docs/data/daily/YYYYMMDD.json. Trả về đường dẫn file."""
    date_str = snapshot["date"].replace("-", "")
    path = Path(daily_dir)
    path.mkdir(parents=True, exist_ok=True)
    fname = path / f"{date_str}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return str(fname)


def update_history_index(today: date, index_file: str = DEFAULT_INDEX_FILE) -> dict:
    """
    Cập nhật docs/data/index.json: thêm ngày hôm nay vào danh sách
    (nếu chưa có), giữ thứ tự tăng dần, cập nhật "latest".
    Trả về nội dung index mới.
    """
    path = Path(index_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                index = json.load(f)
            dates = set(index.get("dates", []))
        except (json.JSONDecodeError, OSError):
            dates = set()
    else:
        dates = set()

    dates.add(today.isoformat())
    sorted_dates = sorted(dates)

    index = {
        "dates": sorted_dates,
        "latest": sorted_dates[-1],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    return index


def publish_latest_excel(excel_paths: list[str],
                          download_dir: str = DEFAULT_DOWNLOAD_DIR) -> list[str]:
    """
    Copy 2 file Excel của ngày hôm nay vào docs/downloads/, ghi đè bản cũ.
    Đặt tên cố định (không kèm ngày) để link tải trên web luôn ổn định
    -- không cần sửa link mỗi ngày.

    Quy ước đặt tên: "KetQuaGiaoDich_20260723.xlsx" -> "KetQuaGiaoDich_latest.xlsx"
    (giữ nguyên phần tên trước dấu "_" cuối cùng theo ngày).
    """
    path = Path(download_dir)
    path.mkdir(parents=True, exist_ok=True)
    saved = []
    for src in excel_paths:
        src_path = Path(src)
        stem = src_path.stem  # VD: "KetQuaGiaoDich_20260723"
        prefix = stem.rsplit("_", 1)[0]  # VD: "KetQuaGiaoDich"
        dest = path / f"{prefix}_latest.xlsx"
        shutil.copy2(src_path, dest)
        saved.append(str(dest))
    return saved


if __name__ == "__main__":
    import tempfile, os

    fake_records = [
        {
            "ma_cw": "CACB2510", "ten_cw": "Chứng quyền ACB",
            "gia_hien_tai": 1690, "pct_thay_doi": "+7.64%", "klgd": 195200,
            "trang_thai_tien": "ITM", "premium": 15.54, "don_bay": 6.63,
            "so_phien_con_lai": 5, "do_bien_dong_lich_su": None,
            "sap_ngung_gd": False, "ck_co_so": "ACB", "to_chuc_ph_cw": "SSI",
            "thoi_han": "12 tháng", "ty_le_chuyen_doi": "2 : 1",
            "gia_phat_hanh": "1,800", "kl_niem_yet": "1,500,000",
            "gia_thuc_hien": "22,500", "ngay_gd_cuoi_cung": "19/06/2026",
        },
        {
            "ma_cw": "CFPT2521", "ten_cw": "Chứng quyền FPT",
            "gia_hien_tai": 150, "pct_thay_doi": "-12.7%", "klgd": 550,
            "trang_thai_tien": "OTM", "premium": 44.6, "don_bay": 1.17,
            "so_phien_con_lai": 0, "do_bien_dong_lich_su": None,
            "sap_ngung_gd": True, "ck_co_so": "FPT", "to_chuc_ph_cw": "PHS",
            "thoi_han": "11 tháng", "ty_le_chuyen_doi": "18.8 : 1",
            "gia_phat_hanh": "1,190", "kl_niem_yet": "400,000",
            "gia_thuc_hien": "121,238", "ngay_gd_cuoi_cung": "19/06/2026",
        },
    ]

    today = date(2026, 7, 23)

    with tempfile.TemporaryDirectory() as tmpdir:
        daily_dir  = os.path.join(tmpdir, "daily")
        index_file = os.path.join(tmpdir, "index.json")

        snapshot = build_daily_snapshot(fake_records, new_listing_codes=["CMSN2620"], today=today)
        assert snapshot["summary"]["total_active"] == 2
        assert snapshot["summary"]["total_itm"] == 1
        assert snapshot["summary"]["total_otm"] == 1
        assert snapshot["summary"]["expiring_soon_count"] == 1
        assert snapshot["summary"]["new_listings_count"] == 1
        print("✅ build_daily_snapshot: summary đúng")

        path1 = save_daily_snapshot(snapshot, daily_dir=daily_dir)
        assert os.path.basename(path1) == "20260723.json"
        with open(path1, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["records"][0]["ma_cw"] == "CACB2510"
        assert loaded["records"][0]["gtgd_ty_vnd"] is not None
        print(f"✅ save_daily_snapshot: đã lưu {path1}, đọc lại đúng")

        idx1 = update_history_index(today, index_file=index_file)
        assert idx1["latest"] == "2026-07-23"
        assert idx1["dates"] == ["2026-07-23"]
        print("✅ update_history_index (lần 1): đúng")

        # Test thêm ngày thứ 2, đảm bảo không mất ngày cũ
        idx2 = update_history_index(date(2026, 7, 24), index_file=index_file)
        assert idx2["dates"] == ["2026-07-23", "2026-07-24"]
        assert idx2["latest"] == "2026-07-24"
        print("✅ update_history_index (lần 2): giữ nguyên ngày cũ, thêm ngày mới")

        # Test publish_latest_excel
        fake_excel_dir = os.path.join(tmpdir, "output")
        os.makedirs(fake_excel_dir, exist_ok=True)
        fake_xlsx1 = os.path.join(fake_excel_dir, "KetQuaGiaoDich_20260723.xlsx")
        fake_xlsx2 = os.path.join(fake_excel_dir, "ThongTinChungQuyen_20260723.xlsx")
        Path(fake_xlsx1).write_bytes(b"fake excel content 1")
        Path(fake_xlsx2).write_bytes(b"fake excel content 2")

        download_dir = os.path.join(tmpdir, "downloads")
        saved = publish_latest_excel([fake_xlsx1, fake_xlsx2], download_dir=download_dir)
        assert os.path.basename(saved[0]) == "KetQuaGiaoDich_latest.xlsx"
        assert os.path.basename(saved[1]) == "ThongTinChungQuyen_latest.xlsx"
        assert Path(saved[0]).read_bytes() == b"fake excel content 1"
        print("✅ publish_latest_excel: đổi tên và copy đúng, ghi đè được")

    print("\n✅ TẤT CẢ TEST PASS")

# ============================================================
# NEW_LISTING.PY
# Phát hiện CW mới niêm yết bằng cách so sánh danh sách mã CW
# đang active hôm nay với danh sách đã lưu từ lần chạy trước.
# ============================================================

import json
import re
from pathlib import Path
from datetime import date, datetime

DEFAULT_HISTORY_FILE = "data/last_active_codes.json"


def load_previous_codes(filepath: str = DEFAULT_HISTORY_FILE) -> set[str] | None:
    path = Path(filepath)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return None


def save_current_codes(records: list[dict], filepath: str = DEFAULT_HISTORY_FILE) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    codes = sorted({r["ma_cw"] for r in records if r.get("ma_cw")})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)


def _listing_date(rec: dict):
    m = re.search(r"\d{2}/\d{2}/\d{4}", str(rec.get("ngay_niem_yet") or ""))
    if not m:
        return None
    try:
        return datetime.strptime(m.group(), "%d/%m/%Y").date()
    except ValueError:
        return None


def find_new_listings(current_records: list[dict], previous_codes,
                      today: date | None = None, max_age_days: int = 7) -> list[dict]:
    """
    Mã "mới niêm yết" = không có trong snapshot trước VÀ ngày niêm yết nằm trong max_age_days gần nhất.
    Điều kiện thứ 2 chặn dương tính giả khi 1 mã chỉ bị rớt tạm thời lúc crawl rồi quay lại
    (dữ liệu lịch sử có 103 trường hợp như vậy, vd 77 mã ngày 30/09).
    Nếu không đọc được ngày niêm yết thì giữ hành vi cũ (chỉ dựa vào snapshot).
    """
    if previous_codes is None:
        return []
    today = today or date.today()
    new_records = []
    for r in current_records:
        code = r.get("ma_cw")
        if not code or code in previous_codes:
            continue
        d = _listing_date(r)
        if d is not None and (today - d).days > max_age_days:
            continue
        new_records.append(r)
    new_records.sort(key=lambda r: r.get("ma_cw", ""))
    return new_records

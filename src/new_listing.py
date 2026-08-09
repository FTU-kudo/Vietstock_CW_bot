# ============================================================
# NEW_LISTING.PY
# Phát hiện CW mới niêm yết bằng cách so sánh danh sách mã CW
# đang active hôm nay với danh sách đã lưu từ lần chạy trước.
# ============================================================

import json
from pathlib import Path
from datetime import date

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


def find_new_listings(current_records: list[dict], previous_codes) -> list[dict]:
    if previous_codes is None:
        return []
    new_records = [r for r in current_records
                   if r.get("ma_cw") and r["ma_cw"] not in previous_codes]
    new_records.sort(key=lambda r: r.get("ma_cw", ""))
    return new_records

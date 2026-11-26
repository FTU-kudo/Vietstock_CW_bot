"""
Đối soát danh sách CW của Vietstock với snapshot của dashboard và phân loại nguyên nhân thiếu.

Cách dùng:
  python tools/reconcile_cw.py vietstock_codes.txt            # snapshot mới nhất
  python tools/reconcile_cw.py vietstock_codes.txt 2026-11-25  # chọn ngày
vietstock_codes.txt: mỗi dòng 1 mã CW (copy cột "Mã CW" từ trang danh sách chứng quyền Vietstock).
"""
import glob, json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from scraper import BASE_STOCKS, default_years  # noqa: E402

MAX_OLD_CAP = 50  # trần cũ của bản scraper trước khi vá
OLD_STOCKS = [s for s in BASE_STOCKS if s != "CSSI"]   # whitelist trước khi vá (chưa có SSI)
OLD_YEARS = default_years()[:2]                        # trước khi vá: năm trước + năm nay


def load_snapshots():
    snaps = {}
    for f in sorted(glob.glob(str(ROOT / "docs/data/daily/*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        snaps[d["date"]] = {r["ma_cw"] for r in d["records"]}
    return snaps


def classify(code, ever_seen, current):
    m = re.fullmatch(r"(C[A-Z]{3})(\d{2})(\d{2})", code)
    if not m:
        return "A. Mã sai định dạng (không khớp C+XXX+YY+NN) -> parser/regex"
    pre, yy, nn = m.group(1), m.group(2), int(m.group(3))
    if pre not in OLD_STOCKS:
        return f"B. CKCS ngoài whitelist BASE_STOCKS cũ ({pre})"
    if yy not in OLD_YEARS:
        return f"C. Năm phát hành ngoài khoảng quét ({yy})"
    if nn > MAX_OLD_CAP:
        return f"D. Số thứ tự {nn} > trần cũ MAX_ISSUANCE=50"
    if code in ever_seen:
        return "E. Từng xuất hiện trong snapshot cũ -> rớt tạm thời khi crawl (timeout/429/5xx)"
    return "F. Mã mới chưa từng thấy, trong phạm vi quét -> lệch thời điểm (snapshot cũ hơn Vietstock live) hoặc lỗi trang"


def main():
    vs = {l.strip().upper() for l in open(sys.argv[1], encoding="utf-8") if l.strip()}
    snaps = load_snapshots()
    day = sys.argv[2] if len(sys.argv) > 2 else max(snaps)
    cur = snaps[day]
    ever = set().union(*snaps.values())
    missing, extra = sorted(vs - cur), sorted(cur - vs)
    print(f"Vietstock={len(vs)}  dashboard[{day}]={len(cur)}  thiếu={len(missing)}  thừa={len(extra)}")
    by = Counter()
    for c in missing:
        k = classify(c, ever, cur); by[k] += 1
        print(f"  MISSING {c:10s} {k}")
    print("\nTổng hợp nguyên nhân:"); [print(f"  {n:3d}  {k}") for k, n in by.most_common()]
    if extra:
        print("\nMã dashboard có nhưng Vietstock list không có (đã ngừng GD / lọc khác):", extra[:20])


if __name__ == "__main__":
    main()

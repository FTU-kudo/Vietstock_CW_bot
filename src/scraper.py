# ============================================================
# SCRAPER.PY
# Crawl dữ liệu chứng quyền (CW) từ Vietstock.
# Tái sử dụng logic đã kiểm chứng từ vietstock_cw_scraper_v5.py,
# đóng gói lại thành module để main.py import và gọi.
# ============================================================

import requests
import re
import time
import threading
from bs4 import BeautifulSoup
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── CẤU HÌNH ────────────────────────────────────────────────

BASE_URL    = "https://finance.vietstock.vn"
MAX_WORKERS = 10
TIMEOUT     = 12
DELAY       = 0.1

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Referer": f"{BASE_URL}/chung-khoan-phai-sinh/chung-quyen.htm",
}

_thread_local = threading.local()

def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update(HEADERS)
        _thread_local.session = s
    return _thread_local.session


# ── DANH SÁCH MÃ CƠ SỞ ──────────────────────────────────────

BASE_STOCKS = [
    "CACB", "CDGC", "CFPT", "CHDB", "CHPG",
    "CLPB", "CMBB", "CMSN", "CMWG", "CSHB",
    "CSSB", "CSTB", "CTCB", "CTPB", "CVHM",
    "CVIB", "CVIC", "CVJC", "CVNM", "CVPB",
    "CVRE",
]

MAX_ISSUANCE = 50  # mỗi mã quét từ 01 đến 50


def generate_cw_codes(years: list[str] | None = None) -> list[str]:
    """
    Tạo toàn bộ mã CW cần kiểm tra.
    Nếu years không truyền vào, tự động lấy năm hiện tại + năm trước.
    """
    if years is None:
        current_year = datetime.now().year
        years = [str(current_year - 1)[2:], str(current_year)[2:]]

    codes = []
    for stock in BASE_STOCKS:
        for yy in years:
            for n in range(1, MAX_ISSUANCE + 1):
                codes.append(f"{stock}{yy}{n:02d}")
    return codes


# ── HELPER PARSE ─────────────────────────────────────────────

def _parse_number(text: str):
    if not text or text.strip() in ("-", ""):
        return None
    token = text.strip().split()[0].replace(",", "")
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return None

def _parse_date(text: str):
    if not text:
        return None
    m = re.search(r"\d{2}/\d{2}/\d{4}", text)
    if m:
        try:
            return datetime.strptime(m.group(), "%d/%m/%Y").date()
        except ValueError:
            pass
    return None


# ── FIX TEXT BLEEDING (từ v5) ───────────────────────────────

_ALL_TABLE_LABELS = sorted([
    "Tổ chức phát hành CKCS", "Tổ chức phát hành CW",
    "Phương thức thực hiện quyền", "Ngày giao dịch cuối cùng",
    "Ngày giao dịch đầu tiên", "Khối lượng Niêm yết",
    "Khối lượng lưu hành", "Loại chứng quyền", "Kiểu thực hiện",
    "TLCĐ điều chỉnh", "Giá TH điều chỉnh", "Tỷ lệ chuyển đổi",
    "Ngày phát hành", "Ngày niêm yết", "Ngày đáo hạn",
    "Giá phát hành", "Giá thực hiện", "CK cơ sở", "Thời hạn", "Tài liệu",
], key=len, reverse=True)

_LABEL_SPLIT_RE = re.compile(
    r'(' + '|'.join(re.escape(lbl) for lbl in _ALL_TABLE_LABELS) + r')\s*:',
    re.UNICODE
)

def _clean_cell(raw: str) -> str:
    """Tách giá trị thật ra khỏi chuỗi bị dồn (lỗi HTML nesting của Vietstock)."""
    if not raw:
        return raw
    raw = raw.strip()
    m = _LABEL_SPLIT_RE.search(raw)
    if m and m.start() > 0:
        return raw[:m.start()].strip()
    return raw


def _parse_basic_table(soup: BeautifulSoup) -> dict:
    data = {}
    table = soup.select_one(".short-doc table")
    if not table:
        return data

    basic_map = {
        "CK cơ sở":                    "ck_co_so",
        "Tổ chức phát hành CKCS":      "to_chuc_ph_ckcs",
        "Tổ chức phát hành CW":        "to_chuc_ph_cw",
        "Loại chứng quyền":            "loai_cw",
        "Kiểu thực hiện":              "kieu_thuc_hien",
        "Phương thức thực hiện quyền": "phuong_thuc",
        "Thời hạn":                    "thoi_han",
        "Ngày phát hành":              "ngay_phat_hanh",
        "Ngày niêm yết":               "ngay_niem_yet",
        "Ngày giao dịch đầu tiên":     "ngay_gd_dau_tien",
        "Ngày giao dịch cuối cùng":    "ngay_gd_cuoi_cung",
        "Ngày đáo hạn":                "ngay_dao_han",
        "Tỷ lệ chuyển đổi":           "ty_le_chuyen_doi",
        "TLCĐ điều chỉnh":            "tlcd_dieu_chinh",
        "Giá phát hành":               "gia_phat_hanh",
        "Giá thực hiện":               "gia_thuc_hien",
        "Giá TH điều chỉnh":          "gia_th_dieu_chinh",
        "Khối lượng Niêm yết":         "kl_niem_yet",
        "Khối lượng lưu hành":         "kl_luu_hanh",
    }

    for tr in table.find_all("tr"):
        tds = tr.find_all("td", limit=2)
        if len(tds) < 2:
            continue
        b_tag = tds[0].find("b")
        label = (b_tag.get_text(strip=True) if b_tag
                 else tds[0].get_text(strip=True)).replace(":", "").strip()
        raw_val = tds[1].get_text(" ", strip=True)
        clean_val = _clean_cell(raw_val)
        for key, col_name in basic_map.items():
            if key in label:
                data[col_name] = clean_val
                break
    return data


# ── CRAWL 1 MÃ CW ────────────────────────────────────────────

def get_cw_detail(code: str) -> dict:
    """Tải và parse trang chi tiết 1 mã CW."""
    url    = f"{BASE_URL}/chung-khoan-phai-sinh/{code}/cw-tong-quan.htm"
    result = {"ma_cw": code, "status": "unknown"}
    sess   = _get_session()

    try:
        resp = sess.get(url, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as e:
        result["status"] = "error"
        result["loi"]    = str(e)[:80]
        return result

    if resp.status_code == 404:
        result["status"] = "not_found"
        return result
    if resp.status_code != 200:
        result["status"] = f"http_{resp.status_code}"
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    h1 = soup.select_one("h1.h1-title")
    if not h1:
        result["status"] = "not_found"
        return result

    result["status"] = "found"
    b_h1 = h1.find("b")
    result["ten_cw"] = (b_h1.get_text(strip=True) if b_h1
                        else h1.get_text(strip=True))

    price_el = soup.select_one("#stockprice .price")
    result["gia_hien_tai"] = (_parse_number(price_el.get_text(strip=True))
                               if price_el else None)

    change_el = soup.select_one("#stockchange")
    if change_el:
        raw = change_el.get_text(strip=True)
        m = re.match(r"([+-]?\d[\d,.]*)\s*\(([^)]+)\)", raw)
        if m:
            result["thay_doi"]     = _parse_number(m.group(1))
            result["pct_thay_doi"] = m.group(2).strip()

    date_el = soup.select_one("#tradedate")
    result["ngay_cap_nhat"] = (date_el.get_text(strip=True)
                                if date_el else None)

    for sel, key, is_num in [
        ("#basestock",        "gia_ck_co_so",  True),
        ("#moneyness",        "s_x",           True),
        ("#breakeven",        "hoa_von",        True),
        ("#moneyness-status", "trang_thai_cw",  False),
    ]:
        el = soup.select_one(sel)
        if el:
            val = el.get_text(strip=True)
            result[key] = _parse_number(val) if is_num else val

    p8_map = {
        "KLGD":             "klgd",
        "NN mua":           "nn_mua",
        "NN bán":           "nn_ban",
        "KLCPLH":           "klcplh",
        "Số ngày đến hạn":  "so_ngay_den_han",
        "Mở cửa":           "gia_mo_cua",
        "Cao nhất":         "gia_cao_nhat",
        "Thấp nhất":        "gia_thap_nhat",
    }
    for p in soup.select(".bt3 p.p8"):
        lbl_el = p.select_one(".text")
        val_el = p.select_one("b.pull-right")
        if lbl_el and val_el:
            lbl = lbl_el.get_text(strip=True)
            if lbl in p8_map:
                result[p8_map[lbl]] = _parse_number(val_el.get_text(strip=True))

    result.update(_parse_basic_table(soup))

    result["_ngay_dao_han_date"]      = _parse_date(result.get("ngay_dao_han", ""))
    result["_ngay_gd_cuoi_cung_date"] = _parse_date(result.get("ngay_gd_cuoi_cung", ""))
    return result


def is_active(r: dict, today: date) -> bool:
    """CW còn giao dịch nếu ngày GD cuối cùng hoặc ngày đáo hạn >= hôm nay."""
    if r.get("status") != "found":
        return False
    last_gd  = r.get("_ngay_gd_cuoi_cung_date")
    maturity = r.get("_ngay_dao_han_date")
    if last_gd:
        return last_gd >= today
    if maturity:
        return maturity >= today
    so_ngay = r.get("so_ngay_den_han")
    return (so_ngay is not None and so_ngay > 0)


# ── CRAWL TOÀN BỘ (SONG SONG) ───────────────────────────────

def crawl_all_cw(today: date | None = None,
                  max_workers: int = MAX_WORKERS,
                  progress_callback=None) -> tuple[list[dict], list[dict]]:
    """
    Crawl toàn bộ mã CW, trả về (records_active, records_all_found).

    progress_callback(done, total, code, result): gọi sau mỗi mã crawl xong,
    dùng để log tiến độ ra console của GitHub Actions.
    """
    if today is None:
        today = date.today()

    all_codes = generate_cw_codes()
    total     = len(all_codes)
    results   = {}
    lock      = threading.Lock()

    def _crawl_one(code):
        time.sleep(DELAY)
        return code, get_cw_detail(code)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_crawl_one, c): c for c in all_codes}
        for future in as_completed(futures):
            code, result = future.result()
            with lock:
                results[code] = result
                if progress_callback:
                    progress_callback(len(results), total, code, result)

    ordered        = [results[c] for c in all_codes if c in results]
    records_found  = [r for r in ordered if r.get("status") == "found"]
    records_active = [r for r in records_found if is_active(r, today)]

    return records_active, records_found


# ── CRAWL GIÁ LỊCH SỬ CỦA CỔ PHIẾU CƠ SỞ ───────────────────

# Map prefix CW → mã cổ phiếu cơ sở thật (bỏ chữ C đầu)
CW_PREFIX_TO_STOCK = {
    "CACB": "ACB",  "CDGC": "DGC",  "CFPT": "FPT",  "CHDB": "HDB",
    "CHPG": "HPG",  "CLPB": "LPB",  "CMBB": "MBB",  "CMSN": "MSN",
    "CMWG": "MWG",  "CSHB": "SHB",  "CSSB": "SSB",  "CSTB": "STB",
    "CTCB": "TCB",  "CTPB": "TPB",  "CVHM": "VHM",  "CVIB": "VIB",
    "CVIC": "VIC",  "CVJC": "VJC",  "CVNM": "VNM",  "CVPB": "VPB",
    "CVRE": "VRE",
}


def get_stock_code_from_cw(cw_code: str) -> str | None:
    """VD: 'CACB2510' → 'ACB'."""
    for prefix, stock in CW_PREFIX_TO_STOCK.items():
        if cw_code.startswith(prefix):
            return stock
    return None


def get_stock_price_history(stock_code: str, num_sessions: int = 30) -> list[float]:
    """
    Lấy lịch sử giá đóng cửa của 1 cổ phiếu cơ sở (VD: ACB, FPT...)
    từ trang thống kê giao dịch Vietstock, dùng để tính historical volatility.

    Trả về list giá theo thứ tự thời gian TĂNG dần (cũ → mới).
    """
    url  = f"{BASE_URL}/{stock_code}/thong-ke-giao-dich.htm"
    sess = _get_session()

    try:
        resp = sess.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    prices = []

    # Bảng thống kê giao dịch: mỗi <tr> có giá đóng cửa ở cột thứ 2
    rows = soup.select("#stock-transactions tbody tr")
    for tr in rows[:num_sessions]:
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        price_text = tds[1].get_text(strip=True)
        price = _parse_number(price_text)
        if price:
            prices.append(price)

    prices.reverse()  # đảo lại để có thứ tự cũ → mới
    return prices


def crawl_all_stock_histories(stock_codes: set[str],
                               num_sessions: int = 30,
                               max_workers: int = 5) -> dict[str, list[float]]:
    """
    Crawl lịch sử giá cho nhiều mã cổ phiếu cơ sở cùng lúc.
    Trả về dict {mã_cổ_phiếu: [giá1, giá2, ...]}.
    """
    histories = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_stock_price_history, code, num_sessions): code
            for code in stock_codes
        }
        for future in as_completed(futures):
            code = futures[future]
            try:
                histories[code] = future.result()
            except Exception:
                histories[code] = []
    return histories


if __name__ == "__main__":
    # Test nhanh: crawl 1 mã để kiểm tra parser còn hoạt động đúng
    print("=== TEST get_cw_detail('CACB2510') ===")
    detail = get_cw_detail("CACB2510")
    for k, v in detail.items():
        if not k.startswith("_"):
            print(f"  {k:25s} = {v}")

    print("\n=== TEST get_stock_code_from_cw ===")
    print(f"  CACB2613 → {get_stock_code_from_cw('CACB2613')}")
    print(f"  CVRE2602 → {get_stock_code_from_cw('CVRE2602')}")

# ============================================================
# MAIN.PY
# Orchestrator: chạy tuần tự các bước
#   1. Crawl dữ liệu CW từ Vietstock (src/scraper.py)
#   1.5. Crawl lịch sử giá cổ phiếu cơ sở (để tính volatility)
#   2. Tính Premium, Đòn bẩy, Volatility lịch sử (src/calculator.py)
#   3. Xuất 2 file Excel (src/export_excel.py)
#   3.5. Kiểm tra CW sắp ngừng giao dịch (src/expiry_warning.py)
#   3.6. Phát hiện CW mới niêm yết (src/new_listing.py)
#   4. Gửi email cho bộ phận phân tích, kèm cảnh báo (src/send_email.py)
#
# Chạy: python main.py
# (Được GitHub Actions gọi tự động theo cron, xem .github/workflows/daily_report.yml)
# ============================================================

import sys
import time
import traceback
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper import crawl_all_cw, get_stock_code_from_cw, crawl_all_stock_histories
from calculator import enrich_cw_record
from export_excel import export_two_excel_files
from send_email import send_report_email
from expiry_warning import get_expiring_soon_list, build_expiry_warning_html
from new_listing import load_previous_codes, save_current_codes, find_new_listings, build_new_listing_html


OUTPUT_DIR = "output"


def progress_logger(done: int, total: int, code: str, result: dict):
    """In tiến độ ra console (sẽ hiện trong log của GitHub Actions)."""
    if done % 50 == 0 or done == total:
        status = result.get("status", "?")
        print(f"  [{done:>5}/{total}] ... {code} ({status})", flush=True)


def main():
    start_time = time.time()
    today = date.today()

    print("=" * 64)
    print(f"  VIETSTOCK CW DAILY REPORT  |  {today.strftime('%d/%m/%Y')}")
    print("=" * 64)

    Path(OUTPUT_DIR).mkdir(exist_ok=True)

    # ── BƯỚC 1: CRAWL DỮ LIỆU CW ────────────────────────────
    print("\n📥 BƯỚC 1/4: Crawl dữ liệu CW từ Vietstock...")
    records_active, records_all = crawl_all_cw(
        today=today, progress_callback=progress_logger
    )
    print(f"✅ Crawl xong: {len(records_active)} mã còn giao dịch "
          f"(tổng {len(records_all)} mã tồn tại)")

    if not records_active:
        print("✗ Không có dữ liệu CW nào. Dừng chương trình, không gửi email.")
        sys.exit(1)

    # ── BƯỚC 1.5: CRAWL LỊCH SỬ GIÁ CKCS (để tính volatility) ─
    print("\n📥 BƯỚC 1.5/4: Crawl lịch sử giá cổ phiếu cơ sở...")
    stock_codes_needed = set()
    for r in records_active:
        stock = get_stock_code_from_cw(r["ma_cw"])
        if stock:
            stock_codes_needed.add(stock)
    print(f"   Cần crawl lịch sử giá cho {len(stock_codes_needed)} mã cổ phiếu cơ sở")

    stock_histories = crawl_all_stock_histories(stock_codes_needed, num_sessions=30)
    success_histories = sum(1 for v in stock_histories.values() if v)
    print(f"✅ Lấy được lịch sử giá cho {success_histories}/{len(stock_codes_needed)} mã")

    # ── BƯỚC 2: TÍNH TOÁN PREMIUM, ĐÒN BẨY, VOLATILITY ─────
    print("\n🧮 BƯỚC 2/4: Tính Premium, Đòn bẩy, Độ biến động lịch sử...")
    enriched_records = []
    for r in records_active:
        stock_code = get_stock_code_from_cw(r["ma_cw"])
        price_history = stock_histories.get(stock_code, []) if stock_code else []
        enriched = enrich_cw_record(r, ckcs_price_history=price_history, today=today)
        enriched_records.append(enriched)
    print(f"✅ Đã tính toán xong cho {len(enriched_records)} mã CW")

    total_itm = sum(1 for r in enriched_records if r.get("trang_thai_tien") == "ITM")
    total_otm = sum(1 for r in enriched_records if r.get("trang_thai_tien") == "OTM")
    print(f"   ITM: {total_itm}  |  OTM: {total_otm}  |  "
          f"ATM: {len(enriched_records) - total_itm - total_otm}")

    # ── BƯỚC 3: XUẤT 2 FILE EXCEL ───────────────────────────
    print("\n📊 BƯỚC 3/4: Xuất file Excel...")
    try:
        f1, f2 = export_two_excel_files(
            enriched_records, output_dir=OUTPUT_DIR, report_date=today
        )
        print(f"✅ Đã tạo: {f1}")
        print(f"✅ Đã tạo: {f2}")
    except Exception as e:
        print(f"✗ Lỗi khi xuất Excel: {e}")
        traceback.print_exc()
        sys.exit(1)

    # ── BƯỚC 3.5: KIỂM TRA CW SẮP NGỪNG GIAO DỊCH ──────────
    print("\n⚠  BƯỚC 3.5/4: Kiểm tra CW sắp ngừng giao dịch (≤2 ngày làm việc)...")
    expiring_records = get_expiring_soon_list(enriched_records)
    if expiring_records:
        print(f"⚠  Phát hiện {len(expiring_records)} mã sắp ngừng giao dịch:")
        for r in expiring_records:
            print(f"     - {r['ma_cw']}: còn {r.get('so_phien_con_lai')} phiên "
                  f"(GD cuối: {r.get('ngay_gd_cuoi_cung', '-')})")
    else:
        print("✅ Không có mã nào sắp ngừng giao dịch trong 2 phiên tới")

    expiry_html = build_expiry_warning_html(expiring_records, report_date=today)

    # ── BƯỚC 3.6: PHÁT HIỆN CW MỚI NIÊM YẾT ────────────────
    print("\n🆕 BƯỚC 3.6/4: Kiểm tra CW mới niêm yết...")
    previous_codes = load_previous_codes()
    if previous_codes is None:
        print("   Chưa có dữ liệu lần chạy trước (có thể là lần đầu triển khai tính năng "
              "này) -- bỏ qua kiểm tra lần này, sẽ lưu danh sách hôm nay để so sánh lần sau")
        new_listings = []
    else:
        new_listings = find_new_listings(enriched_records, previous_codes)
        if new_listings:
            print(f"🆕 Phát hiện {len(new_listings)} mã CW mới niêm yết:")
            for r in new_listings:
                print(f"     - {r['ma_cw']} (CKCS: {r.get('ck_co_so', '-')})")
        else:
            print("   Không có mã CW mới niêm yết hôm nay")

    new_listing_html = build_new_listing_html(new_listings, report_date=today)

    # Lưu lại danh sách hôm nay để lần chạy sau so sánh
    # (bước "Commit updated CW codes snapshot" trong workflow sẽ push file này lên repo)
    save_current_codes(enriched_records)
    print(f"✅ Đã lưu snapshot {len(enriched_records)} mã CW cho lần chạy tiếp theo")

    # ── BƯỚC 4: GỬI EMAIL ────────────────────────────────────
    print("\n📧 BƯỚC 4/4: Gửi email cho bộ phận phân tích...")
    email_sent = send_report_email(
        file_paths=[f1, f2],
        report_date=today,
        summary_stats={
            "total_active": len(enriched_records),
            "total_itm": total_itm,
            "total_otm": total_otm,
        },
        expiry_warning_html=expiry_html,
        new_listing_html=new_listing_html,
    )

    total_time = time.time() - start_time
    print("\n" + "=" * 64)
    print(f"  HOÀN THÀNH | Thời gian chạy: {total_time:.1f}s ({total_time/60:.1f} phút)")
    print(f"  Email: {'✅ Đã gửi' if email_sent else '✗ Gửi thất bại'}")
    print("=" * 64)

    if not email_sent:
        print("⚠ Lưu ý: file Excel đã tạo thành công, chỉ email thất bại.")
        print("  Kiểm tra GitHub Secrets: GMAIL_USER, GMAIL_APP_PASSWORD, ANALYST_EMAIL")


if __name__ == "__main__":
    main()

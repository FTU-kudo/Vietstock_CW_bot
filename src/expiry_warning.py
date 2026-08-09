# ============================================================
# EXPIRY_WARNING.PY
# Tổng hợp danh sách CW sắp ngừng giao dịch (<=2 ngày làm việc).
# ============================================================

def get_expiring_soon_list(enriched_records: list[dict]) -> list[dict]:
    expiring = [r for r in enriched_records if r.get("sap_ngung_gd")]
    expiring.sort(key=lambda r: (r.get("so_phien_con_lai") is None,
                                  r.get("so_phien_con_lai", 999)))
    return expiring

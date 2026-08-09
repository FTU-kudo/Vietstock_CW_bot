// ============================================================
// APP.JS
// Đọc dữ liệu JSON (docs/data/index.json + docs/data/daily/*.json)
// và render dashboard: bảng CW, thẻ tóm tắt, tìm kiếm, lọc, sắp xếp.
// Không dùng thư viện ngoài -- vanilla JS để chạy trực tiếp trên
// GitHub Pages không cần build step.
// ============================================================

let currentData = null;   // snapshot JSON của ngày đang xem
let sortKey = "ma_cw";
let sortAsc = true;

const dateSelect   = document.getElementById("date-select");
const tableBody    = document.getElementById("table-body");
const searchBox    = document.getElementById("search-box");
const filterItm    = document.getElementById("filter-itm");
const filterOtm    = document.getElementById("filter-otm");
const filterNew    = document.getElementById("filter-new");
const filterExpiring = document.getElementById("filter-expiring");

async function init() {
  try {
    const indexResp = await fetch("data/index.json");
    if (!indexResp.ok) throw new Error("Không tải được data/index.json");
    const index = await indexResp.json();

    if (!index.dates || index.dates.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="11" class="empty">Chưa có dữ liệu. Đợi lần chạy tự động đầu tiên.</td></tr>';
      return;
    }

    // Đổ danh sách ngày vào dropdown, mới nhất lên đầu
    const datesDesc = [...index.dates].reverse();
    dateSelect.innerHTML = datesDesc
      .map(d => `<option value="${d}">${formatDateVN(d)}</option>`)
      .join("");
    dateSelect.value = index.latest;

    await loadDate(index.latest);
  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="11" class="empty">Lỗi tải dữ liệu: ${err.message}</td></tr>`;
    console.error(err);
  }
}

async function loadDate(dateStr) {
  tableBody.innerHTML = '<tr><td colspan="11" class="loading">Đang tải dữ liệu...</td></tr>';
  const fileDate = dateStr.replace(/-/g, "");
  try {
    const resp = await fetch(`data/daily/${fileDate}.json`);
    if (!resp.ok) throw new Error(`Không tìm thấy dữ liệu ngày ${dateStr}`);
    currentData = await resp.json();
    renderSummary();
    renderTable();
    document.getElementById("last-updated").textContent =
      `Dữ liệu ngày ${formatDateVN(currentData.date)}`;
  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="11" class="empty">${err.message}</td></tr>`;
    console.error(err);
  }
}

function formatDateVN(isoDate) {
  const [y, m, d] = isoDate.split("-");
  return `${d}/${m}/${y}`;
}

function renderSummary() {
  const s = currentData.summary;
  document.getElementById("stat-total").textContent = s.total_active;
  document.getElementById("stat-itm").textContent = s.total_itm;
  document.getElementById("stat-otm").textContent = s.total_otm;
  document.getElementById("stat-new").textContent = s.new_listings_count;
  document.getElementById("stat-expiring").textContent = s.expiring_soon_count;
}

function getFilteredSortedRecords() {
  if (!currentData) return [];
  const newSet = new Set(currentData.new_listings || []);
  const query = searchBox.value.trim().toUpperCase();

  let rows = currentData.records.filter(r => {
    if (r.trang_thai_tien === "ITM" && !filterItm.checked) return false;
    if (r.trang_thai_tien === "OTM" && !filterOtm.checked) return false;
    if (filterNew.checked && !newSet.has(r.ma_cw)) return false;
    if (filterExpiring.checked && !r.sap_ngung_gd) return false;
    if (query) {
      const haystack = `${r.ma_cw} ${r.ck_co_so || ""}`.toUpperCase();
      if (!haystack.includes(query)) return false;
    }
    return true;
  });

  rows.sort((a, b) => {
    let va = a[sortKey], vb = b[sortKey];
    if (va === null || va === undefined) va = sortAsc ? Infinity : -Infinity;
    if (vb === null || vb === undefined) vb = sortAsc ? Infinity : -Infinity;
    if (typeof va === "string") va = va.toUpperCase();
    if (typeof vb === "string") vb = vb.toUpperCase();
    if (va < vb) return sortAsc ? -1 : 1;
    if (va > vb) return sortAsc ? 1 : -1;
    return 0;
  });

  return rows;
}

function renderTable() {
  const newSet = new Set(currentData.new_listings || []);
  const rows = getFilteredSortedRecords();

  if (rows.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="11" class="empty">Không có mã CW nào khớp bộ lọc.</td></tr>';
    return;
  }

  tableBody.innerHTML = rows.map(r => {
    const rowClass = r.sap_ngung_gd ? "row-expiring" : (newSet.has(r.ma_cw) ? "row-new" : "");
    const badgeClass = r.trang_thai_tien === "ITM" ? "badge-itm" : "badge-otm";
    return `
      <tr class="${rowClass}">
        <td><b>${r.ma_cw}</b></td>
        <td>${r.pct_thay_doi ?? "-"}</td>
        <td>${fmtNum(r.gia_hien_tai)}</td>
        <td>${fmtNum(r.klgd)}</td>
        <td>${r.gtgd_ty_vnd ?? "-"}</td>
        <td><span class="badge ${badgeClass}">${r.trang_thai_tien ?? "-"}</span></td>
        <td>${r.premium ?? "-"}</td>
        <td>${r.don_bay ?? "-"}</td>
        <td>${r.so_phien_con_lai ?? "-"}</td>
        <td>${r.ck_co_so ?? "-"}</td>
        <td>${r.to_chuc_ph_cw ?? "-"}</td>
      </tr>
    `;
  }).join("");
}

function fmtNum(n) {
  if (n === null || n === undefined) return "-";
  return Number(n).toLocaleString("vi-VN");
}

// ── Event listeners ─────────────────────────────────────────

dateSelect.addEventListener("change", (e) => loadDate(e.target.value));
searchBox.addEventListener("input", renderTable);
filterItm.addEventListener("change", renderTable);
filterOtm.addEventListener("change", renderTable);
filterNew.addEventListener("change", renderTable);
filterExpiring.addEventListener("change", renderTable);

document.querySelectorAll("th[data-key]").forEach(th => {
  th.addEventListener("click", () => {
    const key = th.dataset.key;
    if (sortKey === key) {
      sortAsc = !sortAsc;
    } else {
      sortKey = key;
      sortAsc = true;
    }
    document.querySelectorAll("th[data-key]").forEach(el => {
      el.classList.remove("sorted", "asc");
    });
    th.classList.add("sorted");
    if (sortAsc) th.classList.add("asc");
    renderTable();
  });
});

init();

"""Nạp lãi suất tiền gửi VND của 4 ngân hàng (BIDV, Vietcombank, Vietinbank, SHB)
vào bảng `bank_products` (Lớp C) — dùng cho so sánh lãi suất bằng SQL chính xác,
KHÔNG để LLM tự so sánh số (xem doc/Ontology_Implementation_Proposal.md mục 2.2, 4).

Chạy: cd backend && python -m scripts.ingest_bank_rates
Cần: DB Postgres (DATABASE_URL, mặc định localhost:5434) đang chạy.

Techcombank bị loại khỏi scope (đã chốt với user) — PDF phức tạp nhất trong 5
ngân hàng, không phải ngân hàng chính của đề bài.

Nguồn dữ liệu:
- BIDV: `bank_docs/bidv/pages/lai_suat_ca_nhan_20260713.json` — dict {hanoi,hcm}.
  VND ở 2 vùng giống hệt nhau (đã verify), dùng `hanoi`.
- Vietcombank: `bank_docs/vietcombank/pages/lai_suat_{ca_nhan,doanh_nghiep}_live.json`
  — dict {Data: [{tenorType, tenor, currencyCode, tenorDisplay, rates}]}. Chỉ lấy
  `tenorType in (Savings/Demand, FixedDeposit)` — nhiều tenorType (Savings/
  FixedDeposit/Online) có tenor trùng nhau nên chỉ lấy FixedDeposit (chuẩn tiền
  gửi có kỳ hạn, so sánh được với các bank khác) + Savings/Demand (không kỳ hạn).
- Vietinbank: `bank_docs/vietinbank/pages/lai_suat_ca_nhan_live.json` — list
  [{term_vi, vnd_rate}], term_vi dùng câu chữ dạng khoảng ("Từ X đến dưới Y
  tháng") khác hẳn format BIDV — xem `_parse_range_term` để biết quy tắc chọn
  mốc tháng đại diện cho từng loại câu (tránh trùng mốc giữa 2 khoảng liền kề).
- SHB: KHÔNG có JSON công khai, chỉ có PDF nhiều bảng. Nhập tay từ
  `lai_suat_vnd_ca_nhan.pdf`, bảng "1. Biểu lãi suất tiết kiệm bậc thang" (QĐ
  1223/2026/QĐ-TGĐ, hiệu lực 11/4/2026), hàng "Cuối kỳ, < 2 tỷ" — đã đọc PDF
  thật bằng pymupdf và verify từng giá trị (xem SHB_CUOI_KY_DUOI_2TY bên dưới).
  Cần đối chiếu lại PDF gốc (source_url trong manifest.json) trước khi dùng cho
  demo thật — đây là số liệu nhập tay, không phải parse tự động.

Idempotent: xóa sạch rows theo `bank` trước khi nạp lại.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import unicodedata
import uuid
from pathlib import Path

import structlog

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.logging import configure_logging
from app.models.orm import BankProductModel
from app.repositories.bank_product_store import PgBankProductRepository

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
BANK_DOCS_DIR = REPO_ROOT / "data" / "discovery" / "bank_docs"

_PRODUCT_CATEGORY = "lai_suat_tien_gui"
_SEGMENT_LABEL = {"ca_nhan": "cá nhân", "doanh_nghiep": "doanh nghiệp"}


def _normalize(text: str) -> str:
    """NFC-normalize + collapse \xa0/whitespace — nguồn crawl (Vietinbank) dùng
    Unicode form khác literal trong source file này, so sánh chuỗi trực tiếp
    sẽ luôn False nếu không normalize trước (đã verify: "raw == lit" là False
    dù nhìn giống hệt khi in ra)."""
    return unicodedata.normalize("NFC", text).replace("\xa0", " ")


def _row(
    bank: str,
    term: str,
    term_months: float | None,
    rate: float,
    customer_segment: str,
    source_url: str | None,
) -> BankProductModel:
    segment_label = _SEGMENT_LABEL[customer_segment]
    content = f"{bank} — {term} — {rate:.2f}%/năm (VND, {segment_label})"
    return BankProductModel(
        id=uuid.uuid4(),
        bank=bank,
        product_category=_PRODUCT_CATEGORY,
        term=term,
        term_months=term_months,
        customer_segment=customer_segment,
        currency="VND",
        rate_value=round(rate, 3),
        effective_date=None,
        source_url=source_url,
        content=content,
    )


# ── BIDV ────────────────────────────────────────────────────────────────────


def _parse_bidv_term(title_vi: str) -> tuple[str, float | None]:
    low = _normalize(title_vi).lower()
    if "không kỳ hạn" in low:
        return "Không kỳ hạn", 0.0
    m = re.search(r"(\d+)", title_vi)
    if not m:
        return title_vi, None
    months = int(m.group(1))
    return f"{months} tháng", float(months)


def load_bidv() -> list[BankProductModel]:
    path = BANK_DOCS_DIR / "bidv" / "pages" / "lai_suat_ca_nhan_20260713.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    source_url = "https://bidv.com.vn/vn/tra-cuu-lai-suat/"

    rows: list[BankProductModel] = []
    for entry in data["hanoi"]["data"]:
        vnd = str(entry.get("VND", "")).strip()
        if not vnd:
            continue
        term, term_months = _parse_bidv_term(entry.get("title_vi", ""))
        if term_months is None:
            continue
        rows.append(
            _row("BIDV", term, term_months, float(vnd), "ca_nhan", source_url)
        )
    return rows


# ── Vietinbank ────────────────────────────────────────────────────────────────


def _parse_range_term(term_vi: str) -> tuple[str, float | None]:
    """Vietinbank dùng câu chữ dạng khoảng — chọn mốc tháng đại diện:
    - "Không kỳ hạn" -> 0
    - "Dưới 1 tháng" -> bỏ qua (bucket quá nhỏ, không so sánh được)
    - "Từ N đến dưới M tháng" / "N tháng" (không có "Trên") -> lấy mốc dưới N
      (đúng quy ước "từ N" = tính từ N tháng trở lên)
    - "Trên N đến M tháng" (không có "dưới") -> lấy mốc trên M (vd "Trên 12 đến
      13 tháng" nghĩa là đúng mốc 13 tháng)
    - "Trên N đến dưới M tháng" -> bỏ qua (khoảng mù mờ, không trùng mốc tròn
      nào — tránh trùng term với bucket liền kề)
    """
    low = _normalize(term_vi).lower().strip()
    if "không kỳ hạn" in low:
        return "Không kỳ hạn", 0.0
    if low.startswith("dưới"):
        return term_vi, None
    nums = [int(n) for n in re.findall(r"\d+", term_vi)]
    if not nums:
        return term_vi, None
    if low.startswith("trên"):
        if "dưới" in low:
            return term_vi, None
        months = nums[-1]
    else:
        months = nums[0]
    return f"{months} tháng", float(months)


def load_vietinbank() -> list[BankProductModel]:
    path = BANK_DOCS_DIR / "vietinbank" / "pages" / "lai_suat_ca_nhan_live.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    source_url = "https://www.vietinbank.vn/"

    rows: list[BankProductModel] = []
    seen_terms: set[str] = set()
    for entry in data:
        vnd = str(entry.get("vnd_rate", "")).strip()
        if not vnd:
            continue
        term, term_months = _parse_range_term(entry.get("term_vi", ""))
        if term_months is None or term in seen_terms:
            continue
        seen_terms.add(term)
        rows.append(
            _row("VietinBank", term, term_months, float(vnd), "ca_nhan", source_url)
        )
    return rows


# ── Vietcombank ───────────────────────────────────────────────────────────────

_TENOR_MONTHS_RE = re.compile(r"(\d+)-months")


def _load_vcb_segment(filename: str, customer_segment: str) -> list[BankProductModel]:
    path = BANK_DOCS_DIR / "vietcombank" / "pages" / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    source_url = "https://portal.vietcombank.com.vn/Personal/Deposits/Pages/Interest-rate.aspx"

    rows: list[BankProductModel] = []
    for entry in data["Data"]:
        if entry.get("currencyCode") != "VND":
            continue
        tenor_type = entry.get("tenorType")
        tenor = entry.get("tenor", "")
        if tenor_type == "Savings" and tenor == "Demand":
            term, term_months = "Không kỳ hạn", 0.0
        elif tenor_type == "FixedDeposit":
            m = _TENOR_MONTHS_RE.match(tenor)
            if not m:
                continue
            months = int(m.group(1))
            term, term_months = f"{months} tháng", float(months)
        else:
            # Savings/non-Demand và Online trùng mốc với FixedDeposit -> bỏ qua
            # để tránh vi phạm unique constraint (bank, term, segment, currency).
            continue

        rate = float(entry["rates"]) * 100
        rows.append(
            _row(
                "Vietcombank", term, term_months, rate, customer_segment, source_url
            )
        )
    return rows


def load_vietcombank() -> list[BankProductModel]:
    return _load_vcb_segment(
        "lai_suat_ca_nhan_live.json", "ca_nhan"
    ) + _load_vcb_segment("lai_suat_doanh_nghiep_live.json", "doanh_nghiep")


# ── SHB (nhập tay từ PDF) ─────────────────────────────────────────────────────

# Bảng "1. Biểu lãi suất tiết kiệm bậc thang, Hợp đồng tiền gửi" — hàng "Cuối
# kỳ, < 2 tỷ" (QĐ 1223/2026/QĐ-TGĐ, hiệu lực 11/4/2026). Đọc trực tiếp từ
# lai_suat_vnd_ca_nhan.pdf bằng pymupdf, verify từng giá trị thủ công.
_SHB_CUOI_KY_DUOI_2TY: list[tuple[str, float, float]] = [
    ("Không kỳ hạn", 0.0, 0.10),
    ("1 tháng", 1.0, 4.40),
    ("2 tháng", 2.0, 4.40),
    ("3 tháng", 3.0, 4.50),
    ("4 tháng", 4.0, 4.50),
    ("5 tháng", 5.0, 4.50),
    ("6 tháng", 6.0, 5.80),
    ("7 tháng", 7.0, 5.80),
    ("8 tháng", 8.0, 5.80),
    ("9 tháng", 9.0, 5.80),
    ("10 tháng", 10.0, 5.80),
    ("11 tháng", 11.0, 5.80),
    ("12 tháng", 12.0, 6.20),
    ("13 tháng", 13.0, 6.30),
    ("15 tháng", 15.0, 6.30),
    ("18 tháng", 18.0, 6.30),
    ("24 tháng", 24.0, 6.40),
    ("36 tháng", 36.0, 6.50),
]


def load_shb() -> list[BankProductModel]:
    source_url = "https://www.shb.com.vn/lai-suat/"
    return [
        _row("SHB", term, months, rate, "ca_nhan", source_url)
        for term, months, rate in _SHB_CUOI_KY_DUOI_2TY
    ]


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    configure_logging(settings.LOG_LEVEL)

    loaders = {
        "BIDV": load_bidv,
        "VietinBank": load_vietinbank,
        "Vietcombank": load_vietcombank,
        "SHB": load_shb,
    }

    async with AsyncSessionFactory() as session:
        repo = PgBankProductRepository(session)
        for bank, loader in loaders.items():
            rows = loader()
            await repo.delete_by_bank(bank)
            await repo.bulk_insert(rows)
            print(f"  {bank:<12} {len(rows):>3} dòng lãi suất")
        await session.commit()

    print("\nĐã nạp bank_products cho BIDV, VietinBank, Vietcombank, SHB.")
    print("Techcombank bị loại khỏi scope (đã chốt với user).")


if __name__ == "__main__":
    asyncio.run(main())

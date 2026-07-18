"""
Convert 14 văn bản pháp lý trong data/discovery/base_docs/ sang định dạng
data/raw/<loai>/*.md mà backend/app/repositories/document_loader.py đọc được:

    # <tiêu đề> | doc_id=... | effective_date=YYYY-MM-DD | status=...
    ## Điều 1. ...
    nội dung...

Chạy từ repo root:  py data/discovery/convert_to_raw.py

Loại khỏi scope (giữ ở discovery làm tham khảo, xem data/discovery/README.md mục 4):
  - TT 48/2014 (phát ngôn NHNN), TT 48/2025 (thủ tục hành chính NHNN)
  - VBHN 28/2023 (biểu phí B2B NHNN thu của TCTD, không phải phí khách hàng)

Quy tắc tách Điều:
  - Schema A (48/2018, 48/2024 — markdown 1 blob KHÔNG có xuống dòng): tách bằng
    regex mid-text "Điều N. " + quy tắc đánh số tuần tự. Heading ra chỉ còn
    "## Điều N." trần (tiêu đề gốc vẫn nằm trong content vì blob không cho biết
    tiêu đề kết thúc ở đâu).
  - Schema B (12 file — HTML): strip tag -> tách theo dòng "^Điều N. <tiêu đề>".
  - Quy tắc đánh số tuần tự (mọi file): chỉ chấp nhận Điều có số = số trước + 1.
    Chặn tách nhầm Điều trích dẫn trong văn bản sửa đổi (vd Luật 96/2025 trích
    "Điều 198a/198b/198c" của Luật 32/2024 ở đầu dòng — không phải Điều của 96/2025).
"""

import html as html_lib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
DISCOVERY = ROOT / "data" / "discovery"
RAW = ROOT / "data" / "raw"

STATUS_MAP = {
    "Còn hiệu lực": "hieu_luc",
    "Hết hiệu lực toàn bộ": "het_hieu_luc",
    "Hết hiệu lực một phần": "mot_phan_het_hieu_luc",
}

# (doc_number, folder, base_docs path, schema, override {eff_date, status, title})
# Override cho 2 file schema A vì catalog.json thiếu eff_from/eff_status của chúng;
# ngày lấy từ chính điều khoản thi hành trong văn bản (đã xác minh bằng regex).
SCOPE = [
    ("48/2018/TT-NHNN", "lai_suat", "base_docs/thong_tu/48_2018_TT-NHNN.json", "A",
     {"eff": "2019-07-05", "status": "hieu_luc",
      "title": "Thông tư 48/2018/TT-NHNN Quy định về tiền gửi tiết kiệm"}),
    ("48/2024/TT-NHNN", "lai_suat", "base_docs/thong_tu/48_2024_TT-NHNN.json", "A",
     {"eff": "2024-11-20", "status": "hieu_luc",
      "title": "Thông tư 48/2024/TT-NHNN Quy định về việc áp dụng lãi suất đối với tiền gửi bằng đồng Việt Nam của tổ chức, cá nhân tại tổ chức tín dụng, chi nhánh ngân hàng nước ngoài"}),
    ("49/2018/TT-NHNN", "lai_suat", "base_docs/thong_tu/49_2018_TT-NHNN.json", "B", {}),
    ("04/2022/TT-NHNN", "rut_truoc_han", "base_docs/thong_tu/04_2022_TT-NHNN.json", "B", {}),
    ("06/2012/QH13", "bao_hiem", "base_docs/luat/06_2012_QH13.json", "B", {}),
    ("111/2025/QH15", "bao_hiem", "base_docs/luat/111_2025_QH15.json", "B", {}),
    ("68/2013/NĐ-CP", "bao_hiem", "base_docs/nghi_dinh/68_2013_ND-CP.json", "B", {}),
    ("32/2021/QĐ-TTg", "bao_hiem", "base_docs/quyet_dinh/32_2021_QD-TTg.json", "B", {}),
    ("24/2014/TT-NHNN", "bao_hiem", "base_docs/thong_tu/24_2014_TT-NHNN.json", "B", {}),
    ("04/2026/TT-NHNN", "bao_hiem", "base_docs/thong_tu/04_2026_TT-NHNN.json", "B", {}),
    ("32/2024/QH15", "to_chuc_tin_dung", "base_docs/luat/32_2024_QH15.json", "B", {}),
    ("96/2025/QH15", "to_chuc_tin_dung", "base_docs/luat/96_2025_QH15.json", "B", {}),
    ("28/2005/PL-UBTVQH11", "ngoai_hoi", "base_docs/phap_lenh/28_2005_PL-UBTVQH11.json", "B", {}),
    ("70/2014/NĐ-CP", "ngoai_hoi", "base_docs/nghi_dinh/70_2014_ND-CP.json", "B", {}),
]

DIEU_MID_RE = re.compile(r"Điều\s+(\d+)\.\s")
DIEU_LINE_RE = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")


def strip_html(raw: str) -> str:
    text = re.sub(r"<(script|style)[\s\S]*?</\1>", "", raw, flags=re.I)
    text = re.sub(r"</(p|div|tr|h\d|li)>", "\n", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def split_articles_blob(blob: str) -> list[tuple[str, str, str]]:
    """Schema A: blob không xuống dòng. Trả về [(heading, so_dieu, content)]."""
    hits = []
    expected = 1
    for m in DIEU_MID_RE.finditer(blob):
        if int(m.group(1)) == expected:
            hits.append((m.start(), m.end(), m.group(1)))
            expected += 1
    articles = []
    for i, (start, end, num) in enumerate(hits):
        stop = hits[i + 1][0] if i + 1 < len(hits) else len(blob)
        articles.append((f"Điều {num}.", num, blob[end:stop].strip()))
    return articles


def split_articles_lines(text: str) -> list[tuple[str, str, str]]:
    """Schema B: text đã có xuống dòng. Trả về [(heading, so_dieu, content)]."""
    lines = text.split("\n")
    hits = []  # (line_idx, num, heading)
    expected = 1
    for idx, ln in enumerate(lines):
        m = DIEU_LINE_RE.match(ln)
        if m and int(m.group(1)) == expected:
            heading = f"Điều {m.group(1)}. {m.group(2)}".strip().rstrip(".") \
                if m.group(2) else f"Điều {m.group(1)}."
            hits.append((idx, m.group(1), heading))
            expected += 1
    articles = []
    for i, (idx, num, heading) in enumerate(hits):
        stop = hits[i + 1][0] if i + 1 < len(hits) else len(lines)
        body = "\n".join(lines[idx + 1: stop]).strip()
        articles.append((heading, num, body))
    return articles


def trim_signature_tail(content: str) -> str:
    """Cắt phần chữ ký/nơi nhận sau './.' ở Điều cuối."""
    pos = content.find("./.")
    if pos != -1:
        return content[: pos + 3].strip()
    for marker in ("\nNơi nhận", "\nTM. ", "\nKT. THỐNG ĐỐC", "\nXÁC THỰC",
                   "\nCHỦ TỊCH QUỐC HỘI", "\nCHỦ TỊCH NƯỚC", "\nTHỦ TƯỚNG", "\nTHỐNG ĐỐC"):
        pos = content.find(marker)
        if pos != -1:
            return content[:pos].strip()
    return content


def convert():
    RAW.mkdir(parents=True, exist_ok=True)
    report = []
    for doc_number, folder, rel_path, schema, override in SCOPE:
        payload = json.loads((DISCOVERY / rel_path).read_text(encoding="utf-8"))

        if schema == "A":
            title = override["title"]
            eff = override["eff"]
            status = override["status"]
            articles = split_articles_blob(payload["markdown"])
        else:
            data = payload["data"]
            # title có thể chứa xuống dòng (vd 04/2022) — phải gộp về 1 dòng,
            # nếu không HEADER_RE của document_loader sẽ không match và bỏ cả file
            title = re.sub(r"\s+", " ", data["title"]).strip()
            eff = data["effFrom"][:10]
            status = STATUS_MAP[data["effStatus"]["name"]]
            articles = split_articles_lines(strip_html(data["documentContent"]["content"]))

        if not articles:
            report.append((doc_number, folder, 0, "LOI: khong tach duoc Dieu nao"))
            continue

        heading_last, num_last, body_last = articles[-1]
        articles[-1] = (heading_last, num_last, trim_signature_tail(body_last))

        out = [f"# {title} | doc_id={doc_number} | effective_date={eff} | status={status}", ""]
        for heading, _num, body in articles:
            out.append(f"## {heading}")
            out.append(body)
            out.append("")

        out_dir = RAW / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        fname = doc_number.replace("/", "_") + ".md"
        (out_dir / fname).write_text("\n".join(out), encoding="utf-8", newline="\n")
        report.append((doc_number, folder, len(articles), "ok"))

    print(f"{'doc_number':<22} {'folder':<18} {'so_dieu':>7}  ghi_chu")
    for doc_number, folder, n, note in report:
        print(f"{doc_number:<22} {folder:<18} {n:>7}  {note}")


if __name__ == "__main__":
    convert()

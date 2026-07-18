"""
Nạp văn bản pháp lý/nội bộ (biểu lãi suất, quy định rút trước hạn, KYC,
bảo hiểm tiền gửi) đã được chuẩn hóa (Huy bàn giao) và chia nhỏ theo
điều/khoản — KHÔNG theo cấp file (brief mục 3, việc 1).

Định dạng input mong đợi trong data/raw/<loai>/*.md:
  # <tiêu đề văn bản> | doc_id=... | effective_date=YYYY-MM-DD | status=hieu_luc
  ## Điều 1. ...
  nội dung...
  ## Điều 2. ...
  nội dung...
"""
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field

HEADER_RE = re.compile(
    r"^#\s+(?P<title>.+?)\s*\|\s*doc_id=(?P<doc_id>\S+)\s*\|\s*effective_date=(?P<effective_date>\S+)\s*\|\s*status=(?P<status>\S+)",
    re.MULTILINE,
)
CLAUSE_RE = re.compile(r"^##\s+(?P<clause>Điều\s+\d+[^\n]*)\n(?P<body>.*?)(?=^##\s+Điều|\Z)", re.MULTILINE | re.DOTALL)


@dataclass
class Clause:
    doc_id: str
    title: str
    effective_date: str
    status: str
    clause: str
    content: str
    related_doc_ids: list[str] = field(default_factory=list)


def load_documents(data_dir: str) -> list[Clause]:
    clauses: list[Clause] = []
    for root, _, files in os.walk(data_dir):
        for fname in files:
            if not fname.endswith((".md", ".txt")):
                continue
            path = os.path.join(root, fname)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            clauses.extend(_parse_document(text))
    return clauses


def _parse_document(text: str) -> list[Clause]:
    header = HEADER_RE.search(text)
    if not header:
        return []

    doc_id = header.group("doc_id")
    title = header.group("title")
    effective_date = header.group("effective_date")
    status = header.group("status")

    clauses = []
    for m in CLAUSE_RE.finditer(text):
        clauses.append(
            Clause(
                doc_id=doc_id,
                title=title,
                effective_date=effective_date,
                status=status,
                clause=m.group("clause").strip(),
                content=m.group("body").strip(),
            )
        )
    return clauses


# ── Khoản/Điểm splitter ────────────────────────────────────────────────────────
#
# Nội dung 1 Điều là 1 đoạn văn bản phẳng, Khoản ("1. ...2. ...") và Điểm
# ("a) ...b) ...") nằm lẫn trong câu. Để tránh tách nhầm số cuối câu (vd
# "...trong 30 ngày. Tổ chức...") hoặc tham chiếu chéo (vd "khỏan 1, 2, 3 và 4
# Điều này"), chỉ chấp nhận tách khi tìm được ÍT NHẤT 2 mốc tạo thành dãy tăng
# dần liên tục bắt đầu từ 1 (Khoản) / 'a' (Điểm). Nếu không, giữ nguyên văn bản
# làm 1 chunk — an toàn, tương thích ngược với hành vi hiện tại.

_KHOAN_CANDIDATE_RE = re.compile(r"(?:^|(?<=\s))(\d{1,2})\.\s+")
_DIEM_CANDIDATE_RE = re.compile(r"(?:^|(?<=\s))([a-z])\)\s+")


def _find_sequential_boundaries(
    text: str, pattern: re.Pattern[str], first: str, next_label: Callable[[str], str]
) -> list[tuple[int, str]]:
    """Return [(start_offset, label), ...] for markers forming a strict
    increasing sequence starting at `first`; empty if fewer than 2 found."""
    accepted: list[tuple[int, str]] = []
    expected = first
    for m in pattern.finditer(text):
        if m.group(1) == expected:
            accepted.append((m.start(), expected))
            expected = next_label(expected)
    return accepted if len(accepted) >= 2 else []


def _next_number(label: str) -> str:
    return str(int(label) + 1)


def _next_letter(label: str) -> str:
    return chr(ord(label) + 1)


def _split_by_boundaries(text: str, boundaries: list[tuple[int, str]]) -> list[tuple[str, str]]:
    """Slice `text` at boundary offsets; merge any preamble before the first
    boundary into the first segment so no content is dropped."""
    segments: list[tuple[str, str]] = []
    for i, (start, label) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        segment = text[start:end].strip()
        if i == 0:
            preamble = text[:start].strip()
            if preamble:
                segment = f"{preamble} {segment}"
        if segment:
            segments.append((label, segment))
    return segments


def split_khoan_diem(content: str) -> list[tuple[str | None, str | None, str]]:
    """Split Điều content into (khoan, diem, text) tuples.

    Falls back to a single `(None, None, content)` tuple when no reliable
    Khoản structure is found — callers should treat that as "keep as 1 chunk".
    """
    khoan_boundaries = _find_sequential_boundaries(
        content, _KHOAN_CANDIDATE_RE, "1", _next_number
    )
    if not khoan_boundaries:
        return [(None, None, content)]

    results: list[tuple[str | None, str | None, str]] = []
    for khoan_num, khoan_text in _split_by_boundaries(content, khoan_boundaries):
        diem_boundaries = _find_sequential_boundaries(
            khoan_text, _DIEM_CANDIDATE_RE, "a", _next_letter
        )
        if not diem_boundaries:
            results.append((khoan_num, None, khoan_text))
            continue
        for diem_letter, diem_text in _split_by_boundaries(khoan_text, diem_boundaries):
            results.append((khoan_num, diem_letter, diem_text))
    return results

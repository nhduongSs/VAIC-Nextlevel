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
from dataclasses import dataclass, field
from pathlib import Path

HEADER_RE = re.compile(
    r"^#\s+(?P<title>.+?)\s*\|\s*doc_id=(?P<doc_id>\S+)\s*\|\s*effective_date=(?P<effective_date>\S+)\s*\|\s*status=(?P<status>\S+)"
    r"(?:\s*\|\s*bank=(?P<bank>\S+))?"
    r"(?:\s*\|\s*category=(?P<category>\S+))?",
    re.MULTILINE,
)
CLAUSE_RE = re.compile(
    r"^##\s+(?P<clause>Điều\s+\d+[^\n]*)\n(?P<body>.*?)(?=^##\s+Điều|\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class Clause:
    doc_id: str
    title: str
    effective_date: str
    status: str
    clause: str
    content: str
    bank: str | None = None
    category: str | None = None
    related_doc_ids: list[str] = field(default_factory=list)


def load_documents(data_dir: str) -> list[Clause]:
    clauses: list[Clause] = []
    for root, _, files in os.walk(data_dir):
        for fname in files:
            if not fname.endswith((".md", ".txt")):
                continue
            path = Path(root) / fname
            with Path(path).open(encoding="utf-8") as f:
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
    bank = header.group("bank")
    category = header.group("category")

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
                bank=bank,
                category=category,
            )
        )
    return clauses

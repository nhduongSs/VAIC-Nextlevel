from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.authority_level import AuthorityLevel
from app.domain.value_objects.document_type import DocumentType

_DOC_TYPE_KEYWORDS: list[tuple[DocumentType, list[str]]] = [
    (DocumentType.CIRCULAR, ["thông tư", "tt-nhnn", "tt-btc", "tt-bct"]),
    (DocumentType.LAW, ["luật ", "bộ luật", "law"]),
    (DocumentType.DECREE, ["nghị định", "nđ-cp"]),
    (DocumentType.DECISION, ["quyết định", "qđ-nhnn", "qđ-ttg"]),
    (DocumentType.FAQ, ["câu hỏi thường gặp", "hỏi đáp", "faq"]),
    (DocumentType.SOP, ["quy trình", "hướng dẫn thực hiện", "sop"]),
    (DocumentType.POLICY, ["quy định nội bộ", "chính sách", "policy"]),
    (DocumentType.MANUAL, ["hướng dẫn sử dụng", "manual", "tài liệu hướng dẫn"]),
    (DocumentType.PRODUCT_DOC, ["sản phẩm", "product"]),
]

_AUTHORITY_MAP: dict[tuple[DocumentType, str | None], AuthorityLevel] = {
    (DocumentType.LAW, "quốc hội"): AuthorityLevel.NATIONAL_LAW,
    (DocumentType.DECREE, "chính phủ"): AuthorityLevel.NATIONAL_LAW,
    (DocumentType.CIRCULAR, "ngân hàng nhà nước"): AuthorityLevel.NHNN_CIRCULAR,
    (DocumentType.DECISION, "ngân hàng nhà nước"): AuthorityLevel.NHNN_DECISION,
    (DocumentType.SOP, None): AuthorityLevel.DEPARTMENT_SOP,
    (DocumentType.POLICY, None): AuthorityLevel.INTERNAL_POLICY,
    (DocumentType.FAQ, None): AuthorityLevel.FAQ,
    (DocumentType.MANUAL, None): AuthorityLevel.INTERNAL_POLICY,
    (DocumentType.PRODUCT_DOC, None): AuthorityLevel.INTERNAL_POLICY,
}


@dataclass
class ClassificationResult:
    doc_type: DocumentType
    authority_level: AuthorityLevel
    confidence: float


class DocumentClassifier:
    """Rule-based classifier for Vietnamese banking documents."""

    def classify(
        self,
        raw_text: str,
        doc_number: str | None = None,
        issuing_body: str | None = None,
    ) -> ClassificationResult:
        lower = raw_text[:3000].lower()
        doc_type, confidence = self._infer_doc_type(lower, doc_number)
        authority_level = self._infer_authority(doc_type, issuing_body)
        return ClassificationResult(
            doc_type=doc_type,
            authority_level=authority_level,
            confidence=confidence,
        )

    def _infer_doc_type(
        self, lower_text: str, doc_number: str | None
    ) -> tuple[DocumentType, float]:
        # doc_number suffix is a strong, unambiguous signal → high confidence
        if doc_number:
            dn = doc_number.lower()
            if "tt-" in dn:
                return DocumentType.CIRCULAR, 0.95
            if "qd-" in dn or "qđ-" in dn:
                return DocumentType.DECISION, 0.95
            if "nd-" in dn or "nđ-" in dn:
                return DocumentType.DECREE, 0.95

        for doc_type, keywords in _DOC_TYPE_KEYWORDS:
            if any(kw in lower_text for kw in keywords):
                return doc_type, 0.80

        return DocumentType.POLICY, 0.50

    def _infer_authority(self, doc_type: DocumentType, issuing_body: str | None) -> AuthorityLevel:
        if issuing_body:
            body_lower = issuing_body.lower()
            for (dt, body), level in _AUTHORITY_MAP.items():
                if dt == doc_type and body is not None and body in body_lower:
                    return level

        default = _AUTHORITY_MAP.get((doc_type, None))
        if default:
            return default

        return AuthorityLevel.INTERNAL_POLICY

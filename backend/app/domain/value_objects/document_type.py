from enum import StrEnum


class DocumentType(StrEnum):
    LAW = "LAW"
    CIRCULAR = "CIRCULAR"
    DECREE = "DECREE"
    DECISION = "DECISION"
    POLICY = "POLICY"
    SOP = "SOP"
    FAQ = "FAQ"
    PRODUCT_DOC = "PRODUCT_DOC"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"

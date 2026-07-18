from enum import Enum

from pydantic import BaseModel, Field


class BlockReason(str, Enum):
    NONE = "none"
    OUT_OF_SCOPE = "out_of_scope"
    PII_DETECTED = "pii_detected"
    UNSAFE_ADVICE_REQUEST = "unsafe_advice_request"
    PROMPT_INJECTION = "prompt_injection"
    INPUT_TOO_LONG = "input_too_long"
    LOW_CONFIDENCE_ANSWER = "low_confidence_answer"


class DocStatus(str, Enum):
    HIEU_LUC = "hieu_luc"
    HET_HIEU_LUC = "het_hieu_luc"
    MOT_PHAN_HET_HIEU_LUC = "mot_phan_het_hieu_luc"


class RetrievedChunk(BaseModel):
    content: str
    doc_id: str
    title: str
    clause: str
    effective_date: str
    status: DocStatus
    score: float


class Source(BaseModel):
    doc_id: str
    title: str
    clause: str
    effective_date: str


class ConflictInfo(BaseModel):
    description: str
    conflicting_sources: list[str]


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., max_length=4000)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[Source] = []
    conflicts: list[ConflictInfo] = []
    blocked: bool = False
    block_reason: BlockReason = BlockReason.NONE

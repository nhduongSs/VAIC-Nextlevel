"""Nạp 1 case mâu thuẫn (`CONFLICTS_WITH`) được curate thủ công cho mục đích
demo — corpus 14 văn bản pháp lý không có mâu thuẫn thật nào giữa 2 văn bản
cùng hiệu lực (đã rà soát kỹ 4 khu vực nhiều khả năng nhất: lãi suất rút
trước hạn, phí bảo hiểm tiền gửi, hạn mức bảo hiểm, thu giữ tài sản bảo đảm
— không tìm được, hợp lý vì hệ thống pháp luật VN được thiết kế để tránh 2
văn bản cùng hiệu lực nhưng trái nhau). Đúng như brief cho phép: "nếu không
đủ, phối hợp tạo case giả lập".

Case chọn: TT 48/2018/TT-NHNN Điều 17 Khoản 1 (rút trước hạn "theo thỏa
thuận giữa tổ chức tín dụng và người gửi tiền") đọc riêng lẻ dễ hiểu nhầm là
được tự do thỏa thuận bất kỳ mức lãi suất nào, trong khi TT 04/2022/TT-NHNN
Điều 5 lại ấn định trần cụ thể (tối đa bằng lãi suất không kỳ hạn thấp
nhất). Đây là nuance pháp lý CÓ THẬT (không bịa số liệu) — chỉ là mức độ
"mâu thuẫn" (cần đọc kết hợp để không hiểu sai) được đánh giá thấp hơn một
mâu thuẫn tuyệt đối, nên dùng confidence=0.6 thay vì 1.0. Hai văn bản này đã
verify co-retrieve tốt trong top-k cho câu hỏi kiểu "quy định rút trước hạn
tiền gửi" (xem lịch sử), nên demo query sẽ trigger được.

Chạy: cd backend && python -m scripts.ingest_demo_conflict_case
Idempotent: xóa relation cũ cùng metadata_extra["import_source"] trước khi
nạp lại. Cần chạy LẠI sau mỗi lần `scripts.ingest` re-ingest corpus (document
+ chunk id đổi mới mỗi lần — xem docstring `scripts/ingest.py`).

Gắn `source_chunk_id`/`target_chunk_id` cụ thể (không chỉ document_id) vào
metadata_extra: `ConflictDetectionProcessor` dùng 2 field này để chỉ flag
conflict khi CHÍNH 2 Khoản liên quan thật sự nằm trong context đang trả lời
— tránh việc 48/2018 và 04/2022 tình cờ cùng được retrieve cho một câu hỏi
không liên quan (vd hỏi về độ tuổi người gửi tiền) rồi vẫn hiện cảnh báo mâu
thuẫn về rút trước hạn, không ăn nhập gì với câu hỏi.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.logging import configure_logging
from app.models.entities import DocumentRelation
from app.models.enums import RelationType
from app.models.orm import ChunkModel, DocumentModel, DocumentRelationModel
from app.repositories.relation_store import PgDocumentRelationRepository

_IMPORT_TAG = "manual_demo_case"

_SOURCE_DOC_NUMBER = "48/2018/TT-NHNN"
_SOURCE_SECTION_TITLE = "Điều 17."
_SOURCE_SECTION_NUMBER = "Khoản 1"

_TARGET_DOC_NUMBER = "04/2022/TT-NHNN"
_TARGET_SECTION_TITLE = "Điều 5. Lãi suất rút trước hạn tiền gửi"
_TARGET_SECTION_NUMBER = "Khoản 1"
_DESCRIPTION = (
    "TT 48/2018/TT-NHNN Điều 17 Khoản 1 quy định rút trước hạn tiền gửi tiết "
    "kiệm 'theo thỏa thuận giữa tổ chức tín dụng và người gửi tiền', dễ hiểu "
    "nhầm là được tự do thỏa thuận mọi mức lãi suất. Trong khi đó TT "
    "04/2022/TT-NHNN Điều 5 ấn định mức trần cụ thể (tối đa bằng lãi suất "
    "không kỳ hạn thấp nhất của tổ chức tín dụng tại thời điểm rút trước "
    "hạn) — cần đọc kết hợp cả hai văn bản để tránh áp dụng sai."
)


async def _find_chunk_id(
    session, document_id: uuid.UUID, section_title: str, section_number: str
) -> uuid.UUID | None:
    result = await session.execute(
        select(ChunkModel.id).where(
            ChunkModel.document_id == document_id,
            ChunkModel.section_title == section_title,
            ChunkModel.section_number == section_number,
        )
    )
    return result.scalar_one_or_none()


async def main() -> None:
    if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    configure_logging(settings.LOG_LEVEL)

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(DocumentModel.doc_number, DocumentModel.id).where(
                DocumentModel.doc_number.in_([_SOURCE_DOC_NUMBER, _TARGET_DOC_NUMBER]),
                DocumentModel.deleted_at.is_(None),
            )
        )
        doc_map = dict(result.all())

        missing = {_SOURCE_DOC_NUMBER, _TARGET_DOC_NUMBER} - doc_map.keys()
        if missing:
            print(f"Không tìm thấy document cho doc_number: {missing}. Bỏ qua.")
            return

        source_chunk_id = await _find_chunk_id(
            session, doc_map[_SOURCE_DOC_NUMBER], _SOURCE_SECTION_TITLE, _SOURCE_SECTION_NUMBER
        )
        target_chunk_id = await _find_chunk_id(
            session, doc_map[_TARGET_DOC_NUMBER], _TARGET_SECTION_TITLE, _TARGET_SECTION_NUMBER
        )
        if source_chunk_id is None or target_chunk_id is None:
            print(
                "Không tìm thấy chunk cụ thể cho case demo "
                f"(source={source_chunk_id}, target={target_chunk_id}). Bỏ qua — "
                "kiểm tra lại section_title/section_number có đổi sau re-ingest không."
            )
            return

        await session.execute(
            delete(DocumentRelationModel).where(
                DocumentRelationModel.metadata_extra["import_source"].astext
                == _IMPORT_TAG
            )
        )

        relation = DocumentRelation(
            id=uuid.uuid4(),
            source_doc_id=doc_map[_SOURCE_DOC_NUMBER],
            target_doc_id=doc_map[_TARGET_DOC_NUMBER],
            relation_type=RelationType.CONFLICTS_WITH,
            confidence=0.6,
            description=_DESCRIPTION,
            metadata_extra={
                "import_source": _IMPORT_TAG,
                # Bắt buộc để ConflictDetectionProcessor chỉ flag đúng lúc —
                # xem docstring class đó trong document_relation_service.py.
                "source_chunk_id": str(source_chunk_id),
                "target_chunk_id": str(target_chunk_id),
                "note": (
                    "Case demo được curate thủ công — không phải mâu thuẫn "
                    "pháp lý tuyệt đối, mà là nuance dễ hiểu nhầm nếu chỉ đọc "
                    "1 trong 2 văn bản. Dùng để trình diễn tính năng Conflict "
                    "Detection khi corpus không có case mâu thuẫn thật nào "
                    "giữa 2 văn bản cùng hiệu lực (đã rà soát, xem "
                    "conversation history / doc review). Chỉ trigger khi cả "
                    "2 chunk cụ thể (source_chunk_id/target_chunk_id) nằm "
                    "trong context đang trả lời, không phải chỉ cần 2 văn "
                    "bản cùng được retrieve."
                ),
            },
        )

        repo = PgDocumentRelationRepository(session)
        await repo.bulk_insert([relation])
        await session.commit()

    print(
        f"Đã nạp 1 CONFLICTS_WITH: {_SOURCE_DOC_NUMBER} <-> {_TARGET_DOC_NUMBER} "
        f"(confidence=0.6, import_source={_IMPORT_TAG})"
    )


if __name__ == "__main__":
    asyncio.run(main())

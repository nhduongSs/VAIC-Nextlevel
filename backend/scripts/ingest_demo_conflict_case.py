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
nạp lại.
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
from app.models.orm import DocumentModel, DocumentRelationModel
from app.repositories.relation_store import PgDocumentRelationRepository

_IMPORT_TAG = "manual_demo_case"

_SOURCE_DOC_NUMBER = "48/2018/TT-NHNN"
_TARGET_DOC_NUMBER = "04/2022/TT-NHNN"
_DESCRIPTION = (
    "TT 48/2018/TT-NHNN Điều 17 Khoản 1 quy định rút trước hạn tiền gửi tiết "
    "kiệm 'theo thỏa thuận giữa tổ chức tín dụng và người gửi tiền', dễ hiểu "
    "nhầm là được tự do thỏa thuận mọi mức lãi suất. Trong khi đó TT "
    "04/2022/TT-NHNN Điều 5 ấn định mức trần cụ thể (tối đa bằng lãi suất "
    "không kỳ hạn thấp nhất của tổ chức tín dụng tại thời điểm rút trước "
    "hạn) — cần đọc kết hợp cả hai văn bản để tránh áp dụng sai."
)


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
                "note": (
                    "Case demo được curate thủ công — không phải mâu thuẫn "
                    "pháp lý tuyệt đối, mà là nuance dễ hiểu nhầm nếu chỉ đọc "
                    "1 trong 2 văn bản. Dùng để trình diễn tính năng Conflict "
                    "Detection khi corpus không có case mâu thuẫn thật nào "
                    "giữa 2 văn bản cùng hiệu lực (đã rà soát, xem "
                    "conversation history / doc review)."
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

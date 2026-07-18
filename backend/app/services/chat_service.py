from app.core.logging import log_conversation
from app.models.schemas import BlockReason, ChatResponse, Source
from app.services.document_relation_service import DocumentRelationService
from app.services.guardrail_service import GuardrailService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService


class ChatService:
    def __init__(self):
        self.guardrail = GuardrailService()
        self.rag = RAGService()
        self.relations = DocumentRelationService()
        self.llm = LLMService()

    def handle_message(self, session_id: str, message: str) -> ChatResponse:
        log_conversation(session_id, "user", message)

        # 1. Input guard
        input_check = self.guardrail.check_input(session_id, message)
        if not input_check.allowed:
            return self._respond_blocked(session_id, input_check.reason, input_check.message)

        # 2. RAG retrieval
        chunks = self.rag.retrieve(message)

        # 3. Cross-reference: mở rộng thêm chunk liên quan (việc 7)
        chunks = self.relations.apply_cross_reference(chunks)

        # 4. Amendment: chỉ giữ bản có hiệu lực mới nhất (việc 5)
        chunks = self.relations.apply_amendment(chunks)

        # 5. Partial supersession: loại đúng phần đã bị thay thế (việc 6)
        chunks = self.relations.apply_partial_supersession(chunks)

        # 6. Retrieval guard — tránh LLM tự bịa khi không có context phù hợp
        retrieval_check = self.guardrail.check_retrieval(chunks)
        if not retrieval_check.allowed:
            return self._respond_blocked(session_id, retrieval_check.reason, retrieval_check.message)

        # 7. Conflict detection (việc 8)
        conflicts = self.relations.detect_conflicts(chunks)
        conflict_block = "\n".join(c.description for c in conflicts)

        # 8. Generate answer (việc 9)
        context_block = self.rag.build_context_block(chunks)
        raw_answer = self.llm.generate_answer(message, context_block, conflict_block)

        # 9. Output guard
        final_answer = self.guardrail.check_output(raw_answer)

        log_conversation(session_id, "assistant", final_answer)

        return ChatResponse(
            session_id=session_id,
            answer=final_answer,
            sources=[
                Source(doc_id=c.doc_id, title=c.title, clause=c.clause, effective_date=c.effective_date) for c in chunks
            ],
            conflicts=conflicts,
            blocked=False,
        )

    def _respond_blocked(self, session_id: str, reason: BlockReason, message: str) -> ChatResponse:
        log_conversation(session_id, "assistant_blocked", message, meta={"reason": reason})
        return ChatResponse(
            session_id=session_id,
            answer=message,
            sources=[],
            conflicts=[],
            blocked=True,
            block_reason=reason,
        )

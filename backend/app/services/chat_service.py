from app.models.schemas import ChatResponse, ConflictInfo, Source
from app.services.document_relation_service import DocumentRelationService
from app.services.guardrail_service import GuardrailService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService


class ChatService:
    def __init__(
        self,
        rag: RAGService,
        relations: DocumentRelationService,
        guardrail: GuardrailService,
        llm: LLMService,
    ):
        self.rag = rag
        self.relations = relations
        self.guardrail = guardrail
        self.llm = llm

    async def handle_message(self, session_id: str, message: str) -> ChatResponse:
        # 1. Input guard
        input_check = self.guardrail.check_input(message)
        if not input_check.allowed:
            return ChatResponse(
                session_id=session_id,
                answer=input_check.message,
                blocked=True,
                block_reason=input_check.reason,
            )

        # 2. RAG retrieval
        chunks = await self.rag.retrieve(message)

        # 3. KI pipeline (version resolution, conflict detection, timeline)
        context_package = await self.relations.process(message, chunks)

        # 4. Retrieval guard
        retrieval_check = self.guardrail.check_retrieval(context_package.ranked_chunks)
        if not retrieval_check.allowed:
            return ChatResponse(
                session_id=session_id,
                answer=retrieval_check.message,
                blocked=True,
                block_reason=retrieval_check.reason,
            )

        # 5. Build context block for LLM
        context_block = self.rag.build_context_block(context_package)
        conflict_block = "\n".join(
            f"{c.source_title} xung đột với {c.target_title}: {c.description}"
            for c in context_package.conflicts
        )

        # 6. Generate answer
        raw_answer = await self.llm.generate_answer(
            message, context_block, conflict_block
        )
        final_answer = self.guardrail.check_output(raw_answer)

        return ChatResponse(
            session_id=session_id,
            answer=final_answer,
            sources=[
                Source(
                    doc_id=str(c.document_id),
                    title=cit.document_title,
                    clause=cit.section_title or "",
                    effective_date=str(cit.effective_date)
                    if cit.effective_date
                    else None,
                    bank=c.bank,
                )
                for cit in context_package.citations[:5]
                for c in [
                    next(
                        (
                            ch
                            for ch in context_package.ranked_chunks
                            if str(ch.chunk_id) == str(cit.chunk_id)
                        ),
                        None,
                    )
                ]
                if c is not None
            ],
            conflicts=[
                ConflictInfo(
                    description=cf.description or "",
                    conflicting_sources=[str(cf.source_doc_id), str(cf.target_doc_id)],
                )
                for cf in context_package.conflicts
            ],
            blocked=False,
        )

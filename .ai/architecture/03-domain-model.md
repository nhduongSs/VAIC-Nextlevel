# 03 — Domain Model

## Purpose

Định nghĩa các domain entity, value object, aggregate và quan hệ giữa chúng. Domain model phản ánh nghiệp vụ pháp lý ngân hàng, không phụ thuộc vào bất kỳ framework hay database nào.

---

## Bounded Contexts

```mermaid
graph LR
    subgraph KnowledgeContext["Knowledge Context"]
        DOC[Document]
        CHUNK[Chunk]
        REL[DocumentRelation]
    end

    subgraph RetrievalContext["Retrieval Context"]
        QUERY[Query]
        RESULT[RetrievalResult]
        CITATION[Citation]
    end

    subgraph IngestionContext["Ingestion Context"]
        RAWDOC[RawDocument]
        PARSED[ParsedDocument]
        PIPELINE[IngestionJob]
    end

    subgraph UserContext["User Context"]
        USER[User]
        PERM[Permission]
    end

    KnowledgeContext --> RetrievalContext
    IngestionContext --> KnowledgeContext
    UserContext --> RetrievalContext
```

---

## Core Entities

### Document (Aggregate Root)

```mermaid
classDiagram
    class Document {
        +UUID id
        +String title
        +String doc_number
        +DocumentType doc_type
        +AuthorityLevel authority_level
        +Date issued_date
        +Date effective_date
        +Date expired_date
        +DocumentStatus status
        +String issuing_body
        +String file_path
        +String content_hash
        +List~Tag~ tags
        +DateTime created_at
        +DateTime updated_at
        ---
        +is_active() bool
        +is_expired() bool
        +supersedes(other: Document) bool
    }

    class DocumentType {
        <<enumeration>>
        LAW
        CIRCULAR
        DECREE
        DECISION
        POLICY
        SOP
        FAQ
        PRODUCT_DOC
        MANUAL
    }

    class AuthorityLevel {
        <<enumeration>>
        NATIONAL_LAW
        NHNN_CIRCULAR
        NHNN_DECISION
        INTERNAL_POLICY
        DEPARTMENT_SOP
        FAQ
    }

    class DocumentStatus {
        <<enumeration>>
        DRAFT
        ACTIVE
        SUPERSEDED
        EXPIRED
        ARCHIVED
    }

    Document --> DocumentType
    Document --> AuthorityLevel
    Document --> DocumentStatus
```

### Chunk

```mermaid
classDiagram
    class Chunk {
        +UUID id
        +UUID document_id
        +String content
        +Integer chunk_index
        +Integer page_number
        +String section_title
        +String section_number
        +Embedding embedding
        +ChunkType chunk_type
        +Integer token_count
        +DateTime created_at
        ---
        +to_context_string() str
    }

    class Embedding {
        <<value object>>
        +List~float~ vector
        +Integer dimension
        +String model_name
        ---
        +cosine_similarity(other: Embedding) float
    }

    class ChunkType {
        <<enumeration>>
        ARTICLE
        CLAUSE
        PARAGRAPH
        TABLE
        DEFINITION
        APPENDIX
    }

    Chunk --> Embedding
    Chunk --> ChunkType
```

### DocumentRelation

```mermaid
classDiagram
    class DocumentRelation {
        +UUID id
        +UUID source_doc_id
        +UUID target_doc_id
        +RelationType relation_type
        +String description
        +Float confidence
        +DateTime created_at
        ---
        +is_supersession() bool
        +is_amendment() bool
    }

    class RelationType {
        <<enumeration>>
        REPLACES
        AMENDS
        REFERENCES
        SUPPLEMENTS
        IMPLEMENTS
        CONFLICTS_WITH
    }

    DocumentRelation --> RelationType
```

### Query

```mermaid
classDiagram
    class Query {
        +UUID id
        +UUID user_id
        +String question
        +QueryFilter filters
        +DateTime created_at
        +Integer result_count
        +Float latency_ms
    }

    class QueryFilter {
        <<value object>>
        +List~DocumentType~ doc_types
        +List~AuthorityLevel~ authority_levels
        +Date date_from
        +Date date_to
        +List~String~ tags
        +Boolean active_only
    }

    Query --> QueryFilter
```

### Citation

```mermaid
classDiagram
    class Citation {
        <<value object>>
        +UUID chunk_id
        +UUID document_id
        +String document_title
        +String doc_number
        +String section_title
        +String section_number
        +Integer page_number
        +Float relevance_score
        +String excerpt
        ---
        +to_reference_string() str
    }
```

---

## Domain Services

### ChunkingService

Trách nhiệm: quyết định strategy chunking dựa trên document type.

```
ChunkingService.chunk(document: ParsedDocument) → List[Chunk]
  - LAW/CIRCULAR: hierarchical chunking theo Điều, Khoản, Điểm
  - SOP/MANUAL: semantic chunking by section
  - FAQ: QA-pair chunking
```

### ScoringService

Trách nhiệm: tính điểm relevance cho một chunk với một query.

```
ScoringService.score(chunk: Chunk, query: Query, bm25_score: float, vector_score: float) → float
  - Weighted combination: vector_score * 0.6 + bm25_score * 0.4
  - Boosted by authority_level
  - Penalized if document is SUPERSEDED or EXPIRED
```

---

## Domain Rules (Invariants)

1. Một `Document` chỉ có thể là `ACTIVE` nếu không có document khác với `RelationType.REPLACES` trỏ đến nó.
2. `Chunk.embedding.dimension` phải bằng 1024 (BGE-M3 output).
3. `DocumentRelation.confidence` thuộc khoảng [0.0, 1.0].
4. `Document.effective_date` không được trước `Document.issued_date`.
5. Một Chunk phải thuộc đúng một Document (không shared).

---

## Entity Relationships

```mermaid
erDiagram
    DOCUMENT {
        uuid id PK
        string title
        string doc_number
        string doc_type
        string authority_level
        date issued_date
        date effective_date
        date expired_date
        string status
        string issuing_body
        string file_path
        string content_hash
    }

    CHUNK {
        uuid id PK
        uuid document_id FK
        text content
        int chunk_index
        int page_number
        string section_title
        string section_number
        vector embedding
        string chunk_type
        int token_count
    }

    DOCUMENT_RELATION {
        uuid id PK
        uuid source_doc_id FK
        uuid target_doc_id FK
        string relation_type
        string description
        float confidence
    }

    QUERY_LOG {
        uuid id PK
        uuid user_id FK
        text question
        jsonb filters
        int result_count
        float latency_ms
        timestamp created_at
    }

    DOCUMENT ||--o{ CHUNK : "has"
    DOCUMENT ||--o{ DOCUMENT_RELATION : "source"
    DOCUMENT ||--o{ DOCUMENT_RELATION : "target"
```

---

## Constraints

- Domain entities are pure Python dataclasses/classes
- No ORM decorators in domain entities
- Domain entities must be serializable without external libs

---

## Trade-offs

| Choice | Benefit | Cost |
|---|---|---|
| Separate Chunk entity | Fine-grained retrieval | More storage, complex queries |
| DocumentRelation as entity | Explicit relationship management | Manual maintenance of relations |
| AuthorityLevel enum | Enables ranking without hardcoding | Must update when new doc types added |

---

## Future Extensibility

- Add `DocumentVersion` entity for full version history
- Add `Annotation` entity for user highlights and comments
- Add `KnowledgeGraph` aggregate wrapping document relations
- Add `RetrievalSession` entity for multi-turn conversations

# 01 — System Architecture

## Purpose

Định nghĩa kiến trúc tổng thể của hệ thống: các tầng, component, luồng dữ liệu và ranh giới trách nhiệm.

---

## Architecture Style

**Clean Architecture** + **Layered Architecture** kết hợp:

```
┌─────────────────────────────────────────┐
│              Presentation               │  FastAPI Routers, Request/Response Models
├─────────────────────────────────────────┤
│              Application                │  Use Cases, Command/Query Handlers
├─────────────────────────────────────────┤
│                Domain                   │  Entities, Value Objects, Domain Services
├─────────────────────────────────────────┤
│            Infrastructure               │  Repositories, DB, LLM, Embedding clients
└─────────────────────────────────────────┘
```

Dependency Rule: outer layers depend on inner layers. Domain has zero external dependencies.

---

## High-Level Component Diagram

```mermaid
graph TB
    subgraph Frontend["Frontend (React)"]
        UI[Chat UI]
        UploadUI[Document Upload]
    end

    subgraph APIGateway["API Layer (FastAPI)"]
        QR[Query Router]
        DR[Document Router]
        AR[Admin Router]
    end

    subgraph Application["Application Layer"]
        QUC[Query Use Case]
        IUC[Ingestion Use Case]
        AUC[Admin Use Case]
    end

    subgraph DomainLayer["Domain Layer"]
        DE[Document Entity]
        CE[Chunk Entity]
        QE[Query Entity]
        KG[Knowledge Graph Domain]
        RS[Retrieval Strategy]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        subgraph Retrieval["Retrieval Engine"]
            VR[Vector Retriever]
            BR[BM25 Retriever]
            MF[Metadata Filter]
            RR[Re-ranker]
        end
        subgraph KnowledgeIntel["Knowledge Intelligence"]
            RE[Relationship Expander]
            AR2[Authority Ranker]
            VRS[Version Resolver]
            CD[Conflict Detector]
            CB[Citation Builder]
            TB[Timeline Builder]
        end
        subgraph AI["AI Clients"]
            EMB[BGE-M3 Embedder]
            LLM[DeepSeek Client]
        end
        subgraph Persistence["Persistence"]
            PGR[PostgreSQL Repository]
            VER[pgvector Extension]
        end
        subgraph Ingestion["Ingestion Pipeline"]
            DP[Document Parser]
            CS[Chunker]
            MI[Metadata Indexer]
        end
    end

    subgraph DataStore["Data Store"]
        PG[(PostgreSQL + pgvector)]
    end

    UI --> QR
    UploadUI --> DR
    QR --> QUC
    DR --> IUC
    AR --> AUC
    QUC --> RS
    IUC --> DP
    RS --> VR
    RS --> BR
    RS --> MF
    VR --> RR
    BR --> RR
    MF --> RR
    RR --> KnowledgeIntel
    KnowledgeIntel --> LLM
    EMB --> VER
    PGR --> PG
    VER --> PG
    DP --> CS
    CS --> EMB
    CS --> MI
    MI --> PGR
```

---

## Data Flow — Query Path

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant QUC as QueryUseCase
    participant MF as MetadataFilter
    participant VR as VectorRetriever
    participant BR as BM25Retriever
    participant RR as ReRanker
    participant KI as KnowledgeIntelligence
    participant LLM as DeepSeek
    participant DB as PostgreSQL

    U->>API: POST /query {question, filters}
    API->>QUC: handle(QueryCommand)
    QUC->>MF: filter(doc_type, date_range, authority)
    MF->>DB: SELECT candidate doc_ids
    QUC->>VR: search(embedding, doc_ids)
    QUC->>BR: search(bm25_tokens, doc_ids)
    VR->>DB: pgvector ANN search
    BR->>DB: BM25 tsvector search
    VR-->>QUC: vector_results
    BR-->>QUC: bm25_results
    QUC->>RR: rerank(merged_results, query)
    RR-->>QUC: ranked_chunks
    QUC->>KI: expand(ranked_chunks)
    KI->>DB: fetch related docs
    KI-->>QUC: enriched_chunks + citations
    QUC->>LLM: generate(prompt, enriched_chunks)
    LLM-->>QUC: answer
    QUC-->>API: QueryResponse{answer, citations, sources}
    API-->>U: 200 OK
```

---

## Data Flow — Ingestion Path

```mermaid
sequenceDiagram
    participant A as Admin
    participant API as FastAPI
    participant IUC as IngestionUseCase
    participant DP as DocParser
    participant CS as Chunker
    participant EMB as BGE-M3
    participant MI as MetadataExtractor
    participant DB as PostgreSQL

    A->>API: POST /documents {file, metadata}
    API->>IUC: handle(IngestCommand)
    IUC->>DP: parse(file) → raw_text, sections
    DP-->>IUC: ParsedDocument
    IUC->>MI: extract_metadata(parsed_doc)
    MI-->>IUC: DocumentMetadata{authority, date, doc_type, relations}
    IUC->>CS: chunk(parsed_doc, strategy)
    CS-->>IUC: List[Chunk]
    IUC->>DB: INSERT document + metadata
    note over DB: Document inserted FIRST\n(chunks have FK to document_id)
    loop batch embed chunks
        IUC->>EMB: embed_batch(chunk_texts)
        EMB-->>IUC: embeddings[]
    end
    IUC->>DB: INSERT chunks (bulk with embeddings)
    IUC->>DB: INSERT document_relations
    IUC-->>API: IngestionResponse{doc_id, chunk_count}
    API-->>A: 201 Created
```

---

## Component Responsibilities

| Component | Responsibility |
|---|---|
| FastAPI Routers | HTTP boundary, request validation, response serialization |
| Use Cases | Orchestrate domain logic, no business rules here |
| Domain Entities | Business rules, invariants, domain events |
| Repositories | Data access abstraction, async DB calls |
| Retrieval Engine | Hybrid search pipeline (BM25 + Vector + Filter + Rerank) |
| Knowledge Intelligence | Relationship expansion, conflict detection, citation |
| BGE-M3 Client | Encode text to dense vectors |
| DeepSeek Client | Generate natural language answers |
| Ingestion Pipeline | Parse → Chunk → Embed → Store |

---

## Constraints

- All I/O must be async (AsyncPG, async HTTP clients)
- No synchronous blocking calls in the request path
- Domain layer has zero imports from infrastructure
- Use Cases depend only on Domain and abstract Repository interfaces

---

## Trade-offs

| Choice | Benefit | Cost |
|---|---|---|
| Clean Architecture | Testable domain, swappable infra | More boilerplate |
| Async everywhere | High throughput, no thread blocking | Harder debugging |
| Single FastAPI app | Simple deployment | Harder to scale individual components |

---

## Future Extensibility

- Extract Ingestion Pipeline into separate worker/queue (Celery, ARQ)
- Add event sourcing for document version history
- Split retrieval into microservice if load demands
- Introduce CQRS for read/write separation at scale

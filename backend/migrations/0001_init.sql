-- Migration 0001 — schema khởi tạo cho RAG Tiền Gửi SHB
-- Chạy trong Supabase SQL editor (hoặc `supabase db execute -f`).
-- Khớp với app/repositories/vector_store.py và app/repositories/relation_store.py

create extension if not exists vector;

-- ============================================================
-- document_chunks — vector + metadata (điều/khoản) trong 1 bảng
-- ============================================================
create table if not exists document_chunks (
    id              bigint generated always as identity primary key,
    doc_id          text not null,
    title           text not null,
    clause          text not null,
    effective_date  date not null,
    status          text not null check (status in ('hieu_luc', 'het_hieu_luc', 'mot_phan_het_hieu_luc')),
    content         text not null,
    embedding       vector(1024) not null,  -- bge-m3 = 1024 chiều
    created_at      timestamptz not null default now()
);

create index if not exists document_chunks_doc_id_idx on document_chunks (doc_id);
create index if not exists document_chunks_status_idx on document_chunks (status);

-- HNSW cho vector search (pgvector >= 0.5). Đổi sang ivfflat nếu bản Supabase cũ hơn.
create index if not exists document_chunks_embedding_idx
    on document_chunks using hnsw (embedding vector_cosine_ops);

-- ============================================================
-- document_relations — cross-reference / amends / supersedes
-- ============================================================
create table if not exists document_relations (
    id                  bigint generated always as identity primary key,
    source_doc_id       text not null,
    related_doc_id      text not null,
    relation_type       text not null check (relation_type in ('cross_reference', 'amends', 'supersedes')),
    superseded_clause   text,  -- chỉ dùng khi relation_type = 'supersedes'
    created_at          timestamptz not null default now()
);

create index if not exists document_relations_source_idx on document_relations (source_doc_id, relation_type);
create index if not exists document_relations_related_idx on document_relations (related_doc_id, relation_type);

-- ============================================================
-- match_document_chunks — vector search + lọc trạng thái trong 1 query
-- ============================================================
create or replace function match_document_chunks(
    query_embedding vector(1024),
    match_count int default 5
)
returns table (
    doc_id          text,
    title           text,
    clause          text,
    effective_date  date,
    status          text,
    content         text,
    similarity      float
)
language sql stable
as $$
    select
        doc_id,
        title,
        clause,
        effective_date,
        status,
        content,
        1 - (embedding <=> query_embedding) as similarity
    from document_chunks
    where status <> 'het_hieu_luc'
    order by embedding <=> query_embedding
    limit match_count;
$$;

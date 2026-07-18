# Project Conventions

This document defines the naming conventions and repository organization rules for the entire project.

These conventions must be followed consistently.

---

# General Naming

Use English only.

Use meaningful names.

Avoid abbreviations unless universally accepted.

Good

CustomerProfile

DocumentChunk

EmbeddingService

Bad

Cus

Doc

EmbSrv

---

# File Naming

Python files

snake_case.py

Examples

document_service.py

embedding_service.py

knowledge_repository.py

hybrid_retriever.py

Never use

camelCase.py

PascalCase.py

---

# Class Naming

PascalCase

Examples

DocumentService

KnowledgeRepository

EmbeddingClient

ChunkingStrategy

---

# Function Naming

snake_case

Examples

create_document()

search_documents()

generate_embeddings()

---

# Variable Naming

snake_case

Examples

document_id

chunk_size

embedding_model

Never use

documentId

ChunkSize

---

# Constant Naming

UPPER_SNAKE_CASE

Examples

DEFAULT_CHUNK_SIZE

MAX_UPLOAD_SIZE

EMBEDDING_DIMENSION

---

# Enum Naming

PascalCase

Enum values

UPPER_CASE

Example

class DocumentStatus(Enum):

    ACTIVE

    ARCHIVED

    DRAFT

---

# Package Organization

One responsibility per package.

Avoid utility dumping.

Bad

utils/

Good

embedding/

retrieval/

knowledge/

documents/

---

# Router Naming

Every router represents one business capability.

Examples

documents.py

chat.py

knowledge.py

admin.py

Never

api.py

main_router.py

misc.py

---

# Service Naming

Services describe business capabilities.

Examples

DocumentService

ChatService

KnowledgeService

SearchService

Never

DocumentManager

Helper

Processor

Utils

---

# Repository Naming

Repositories represent persistence.

Examples

DocumentRepository

ChunkRepository

KnowledgeRepository

ConversationRepository

---

# DTO Naming

Request

CreateDocumentRequest

UpdateDocumentRequest

ChatRequest

Response

DocumentResponse

SearchResponse

ChatResponse

---

# Entity Naming

Entities are singular.

Good

Document

Chunk

Conversation

User

Bad

Documents

Chunks

Users

---

# Migration Naming

Always descriptive.

Good

add_document_metadata

create_chunk_table

add_vector_index

Bad

migration1

fix

update

---

# Database Tables

Plural

documents

chunks

embeddings

conversations

users

---

# Primary Keys

Always

id

UUID preferred.

Foreign keys

document_id

user_id

conversation_id

---

# API Endpoints

Plural nouns.

Examples

GET /documents

POST /documents

GET /documents/{id}

POST /chat

POST /search

---

# Environment Variables

UPPER_SNAKE_CASE

Examples

DATABASE_URL

DEEPSEEK_API_KEY

EMBEDDING_MODEL

VECTOR_DIMENSION

---

# Configuration

Never hardcode.

Everything configurable.

Examples

Chunk Size

Embedding Model

LLM Model

Top K

Temperature

Timeout

---

# Logging

Use structured logging.

Include

request_id

document_id

conversation_id

user_id

Never log secrets.

---

# Exceptions

Create domain-specific exceptions.

Examples

DocumentNotFoundError

EmbeddingError

RetrievalError

ValidationError

Never raise generic Exception directly.

---

# Tests

Mirror application structure.

Example

app/services/chat_service.py

↓

tests/services/test_chat_service.py

---

# Documentation

Every public service should include

Purpose

Inputs

Outputs

Exceptions

Complex logic should include inline comments explaining WHY, not WHAT.

---

# AI Components

Naming

EmbeddingClient

EmbeddingService

Retriever

HybridRetriever

CrossEncoder

PromptBuilder

CitationBuilder

RelationshipExtractor

KnowledgeGraphService

Use consistent terminology across the project.
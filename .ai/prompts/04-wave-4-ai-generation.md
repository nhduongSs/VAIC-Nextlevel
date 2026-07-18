# Wave 4 — AI Generation

## ROLE

You are a Principal AI Backend Engineer implementing Wave 4 (AI Generation) for an Enterprise Knowledge Assistant.

Wave 1 (Foundation), Wave 2 (Knowledge Ingestion), and Wave 3 (Retrieval + Knowledge Intelligence) have already been completed.

The architecture is frozen.

Your responsibility is to build the complete AI Generation Layer on top of the existing Retrieval Pipeline.

Reuse all existing modules whenever possible.

Do NOT refactor previous Waves unless absolutely necessary.

---

# Read First

Before implementing, carefully review:

1. CLAUDE.md
2. .ai/architecture/architecture-freeze.md
3. .ai/architecture/implementation-plan.md
4. Wave 3 implementation
5. Existing Retrieval & Knowledge Pipeline

Treat the architecture as immutable.

---

# Objective

Build the complete AI Generation Layer.

The final pipeline becomes:

User Question

↓

Hybrid Retrieval

↓

Knowledge Intelligence

↓

ContextPackage

↓

Prompt Builder

↓

DeepSeek Client

↓

Response Formatter

↓

AnswerPackage

↓

Chat API

---

# Core Architecture

Implement the following modules.

## Prompt Layer

Implement

- PromptBuilder
- PromptTemplate
- PromptRenderer
- PromptPackage
- PromptOptimizer
- PromptConfig
- TokenEstimator

Responsibilities

- build prompts from ContextPackage
- support configurable prompt templates
- optimize prompt size
- estimate prompt tokens
- support multiple prompt types

Supported prompt types

- Question Answering
- Summarization
- Comparison
- Explanation

---

## Prompt Structure

Generate prompts using the following sections.

### System Prompt

Contains

- assistant identity
- banking domain expertise
- response policy
- citation policy
- hallucination prevention
- formatting instructions
- language policy

---

### User Question

Original user question.

---

### Context

Build from ContextPackage.

Include

- ranked chunks
- citations
- metadata
- relationships
- timeline

---

### Response Instructions

The LLM must

- answer ONLY using provided context
- never fabricate information
- cite every important statement
- admit uncertainty if evidence is insufficient
- keep responses professional and concise

---

## Prompt Optimization

Implement PromptOptimizer.

Responsibilities

- remove duplicated chunks
- remove duplicated citations
- remove irrelevant metadata
- trim unnecessary relationships
- respect maximum token budget

Reject oversized prompts gracefully.

---

## Token Management

Implement TokenEstimator.

Estimate

- prompt tokens
- completion tokens
- total tokens

Expose token usage statistics.

---

# DeepSeek Layer

The system currently supports ONLY DeepSeek.

Implement

- LLMClient (interface)
- DeepSeekClient
- DeepSeekService

Responsibilities

- build request payload
- call DeepSeek API
- parse response
- timeout handling
- retry failed requests
- normalize output
- collect usage statistics

Design the interface so that future providers can be added without changing ChatService.

Do NOT implement

- Gemini
- OpenAI
- Claude
- Multi-provider routing

---

# Response Layer

Implement

- ResponseFormatter
- CitationFormatter
- AnswerPackage
- UsageStatistics

Responsibilities

- normalize response
- attach citations
- attach confidence score
- attach token usage
- attach latency
- attach provider metadata

---

# Chat Layer

Implement

- ChatService
- ChatController

ChatService orchestrates

Question

↓

Retrieval

↓

Knowledge Intelligence

↓

Prompt Builder

↓

DeepSeek

↓

Response Formatter

↓

AnswerPackage

Controllers must contain no business logic.

---

# Streaming

Support Server Sent Events (SSE).

Implement

POST /chat/stream

Streaming requirements

- incremental responses
- cancellation support
- timeout handling
- graceful failure

---

# APIs

Implement

POST /chat

POST /chat/stream

POST /prompt/build

POST /prompt/preview

GET /chat/health

---

# Configuration

Support configuration for

- DeepSeek API key
- DeepSeek model
- timeout
- retry count
- temperature
- top_p
- max prompt tokens
- max completion tokens
- streaming enabled

---

# Logging

Log

- prompt size
- estimated tokens
- latency
- retries
- provider
- response time

Never log

- API keys
- full prompt contents
- sensitive user data

---

# Metrics

Collect

- request count
- latency
- token usage
- estimated cost
- retry count
- streaming duration
- error rate

---

# Error Handling

Handle

- timeout
- invalid API response
- malformed JSON
- empty response
- rate limit
- unavailable provider

Return meaningful error messages.

---

# Security

Never expose

- API keys
- internal prompts
- stack traces

Sanitize logs.

Validate all inputs.

---

# Testing

Create unit and integration tests for

PromptBuilder

PromptRenderer

PromptOptimizer

TokenEstimator

DeepSeekClient

DeepSeekService

ResponseFormatter

CitationFormatter

ChatService

ChatController

Streaming API

Prompt APIs

Retry logic

Error handling

---

# Documentation

Update

- architecture documentation
- API documentation
- sequence diagrams
- Prompt Builder documentation
- DeepSeek integration guide

---

# Explicitly Out of Scope

Do NOT implement

- Conversation Memory
- Semantic Cache
- Prompt Cache
- Guardrails
- Multi-Agent
- Audit Logs
- Rate Limiting
- Monitoring Dashboard
- Multi-provider routing

These belong to later Waves.

---

# Deliverables

Implement

✓ PromptBuilder

✓ PromptTemplate

✓ PromptRenderer

✓ PromptOptimizer

✓ PromptPackage

✓ TokenEstimator

✓ LLMClient interface

✓ DeepSeekClient

✓ DeepSeekService

✓ ResponseFormatter

✓ CitationFormatter

✓ AnswerPackage

✓ ChatService

✓ ChatController

✓ Chat APIs

✓ Streaming API

✓ Tests

✓ Documentation

---

# Acceptance Criteria

✓ Prompt generated successfully

✓ Prompt optimization works

✓ Token estimation works

✓ DeepSeek integration works

✓ Streaming works

✓ Chat API works

✓ Response formatting works

✓ Citations are attached

✓ Ruff passes

✓ MyPy passes

✓ Pytest passes

---

# Completion Definition

After Wave 4, the backend is capable of generating grounded AI answers from enterprise knowledge.

The completed pipeline is

Question

↓

Hybrid Retrieval

↓

Knowledge Intelligence

↓

ContextPackage

↓

Prompt Builder

↓

DeepSeek

↓

Response Formatter

↓

AnswerPackage

↓

Chat API

↓

Streaming Response
# V1/V2 Data Flow

## Purpose

This document explains how the main project parts interact in V1/V2. It keeps the architecture simple and focused on implementation.

The frontend should only call FastAPI. It should not call PostgreSQL, Chroma, RAG, or Agent directly.

FastAPI is the main entry point and orchestrator.

## Component Responsibilities

### Frontend

Renders the user interface and sends requests to FastAPI.

### FastAPI

Validates requests, authenticates users, checks permissions, and coordinates services.

### Service

Contains application logic for one feature area, such as products, chat, documents, or sales.

### Repository

Reads and writes PostgreSQL data for a service.

### PostgreSQL

Stores structured data, user data, tenant ownership, conversations, document metadata, and feedback.

### RAG

Parses documents, chunks text, embeds chunks, retrieves relevant context, and helps generate grounded answers.

### Chroma

Stores vector embeddings for document chunks.

### Agent

Selects and calls read-only tools for business questions, then summarizes the results.

## 1. Normal Database Request Flow

Example: listing products or retrieving an order.

```text
Frontend
  -> FastAPI route
  -> Service
  -> Repository
  -> PostgreSQL
  -> Repository
  -> Service
  -> FastAPI response
  -> Frontend
```

Flow:

1. The frontend sends a request to FastAPI.
2. FastAPI validates the JWT and resolves the current tenant.
3. FastAPI calls the relevant service.
4. The service applies business rules.
5. The repository queries PostgreSQL with a tenant filter.
6. The service returns the result.
7. FastAPI sends the response to the frontend.

## 2. Chat With RAG Flow

Example: customer asks about return policy.

```text
Frontend
  -> FastAPI /chat
  -> Chat service
  -> RAG retrieval
  -> Chroma
  -> RAG retrieval
  -> LLM answer
  -> Chat service stores messages and sources
  -> FastAPI response with sources
  -> Frontend
```

Flow:

1. The frontend sends a chat message to `/chat`.
2. FastAPI authenticates the user and resolves the tenant.
3. The chat service stores the user message.
4. The chat service asks RAG for relevant context.
5. RAG searches Chroma using the tenant filter.
6. RAG returns relevant chunks and source metadata.
7. The LLM generates a grounded answer from the retrieved context.
8. The chat service stores the assistant message and sources.
9. FastAPI returns the answer and sources to the frontend.

For `/chat/stream`, the same flow applies, but FastAPI streams events as the answer is generated.

## 3. Chat With Agent Tool Flow

Example: store owner asks, "What were my sales this month?"

```text
Frontend
  -> FastAPI /chat
  -> Chat service
  -> Agent
  -> Tool
  -> Backend service
  -> Repository
  -> PostgreSQL
  -> Backend service
  -> Tool result
  -> Agent summary
  -> Chat service stores messages and used tools
  -> FastAPI response
  -> Frontend
```

Flow:

1. The frontend sends a chat message to `/chat`.
2. FastAPI authenticates the user and resolves the tenant.
3. The chat service decides the request needs business data.
4. The Agent selects one or more read-only tools.
5. Each tool calls a backend service instead of querying PostgreSQL directly.
6. The backend service uses a repository to query PostgreSQL with tenant filters.
7. The Agent summarizes the tool results.
8. The chat service stores the assistant message and used tool names.
9. FastAPI returns the summary to the frontend.

In V1/V2, agent tools are read-only. They do not create, update, or delete business resources.

## 4. Document Ingestion Flow

Example: store owner uploads a PDF policy document.

```text
Frontend uploads document
  -> FastAPI /documents
  -> Document service
  -> RAG ingestion
  -> Parser
  -> Chunker
  -> Embeddings
  -> Chroma
  -> Document metadata and chunk metadata stored in PostgreSQL
  -> FastAPI response
  -> Frontend
```

Flow:

1. The frontend uploads a PDF, DOCX, or TXT file to FastAPI.
2. FastAPI authenticates the user and checks upload permission.
3. The document service creates a document metadata record.
4. RAG ingestion parses the file text.
5. The chunker splits text into smaller chunks.
6. The embedding component generates a vector for each chunk.
7. Chroma stores each vector with tenant and source metadata.
8. PostgreSQL stores document metadata and chunk metadata.
9. The document status becomes `ready` or `failed`.
10. FastAPI returns the document status to the frontend.

## Boundary Rules

- Frontend calls only FastAPI.
- FastAPI coordinates all authentication, authorization, and tenant isolation.
- Services call repositories for PostgreSQL access.
- RAG talks to Chroma through a retrieval or ingestion interface.
- Agent tools call backend services, not repositories directly.
- PostgreSQL stores structured data and metadata.
- Chroma stores vector embeddings.

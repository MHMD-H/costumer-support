# V1/V2 Requirements

## Project Overview

AI Commerce Copilot is an AI-powered e-commerce assistant. V1/V2 focus on answering customer questions from company knowledge and helping store owners query basic business data.

The system combines:

- A FastAPI backend.
- A Next.js frontend.
- PostgreSQL for structured data.
- Chroma for vector storage.
- A RAG layer for document-grounded answers.
- A basic Agent layer for selecting and combining business tools.

## Version 1: Basic AI Assistant

### Customer Requirements

The system shall allow customers to:

- Ask questions about products.
- Ask questions about company policies.
- Ask about shipping, returns, and warranties.
- Receive answers grounded in uploaded documents.
- See sources used to produce an answer.

### Store Owner Requirements

The system shall allow store owners to:

- Query products.
- Query orders.
- Query sales.
- Retrieve simple business metrics.
- Ask the assistant basic business questions.

### RAG Requirements

The RAG system shall:

- Upload documents through FastAPI.
- Support PDF parsing.
- Support DOCX parsing.
- Support TXT parsing.
- Split documents into chunks.
- Generate embeddings for chunks.
- Store chunk vectors in Chroma.
- Store document and chunk metadata in PostgreSQL.
- Retrieve relevant chunks for a user question.
- Generate grounded answers with source references.
- Return an unknown answer when the retrieved context is insufficient.

### Agent Requirements

The Agent shall:

- Use an LLM.
- Select a tool when the request requires structured business data.
- Call basic tools for products, orders, and sales.
- Return tool results in natural language.
- Avoid executing business-changing actions in V1/V2.

## Version 2: Smart Assistant

### Customer Requirements

The system shall:

- Answer questions that require more than one document.
- Combine related policy or product information.
- Retrieve from several knowledge sources.

### Store Owner Requirements

The system shall:

- Compare simple business metrics.
- Aggregate information from multiple tools.
- Answer analytical questions using retrieved structured data.

### RAG Requirements

The RAG system shall support:

- Semantic search.
- Keyword search.
- Hybrid retrieval.
- Metadata filtering by tenant, document, document type, and source.
- Query rewriting for better retrieval.
- Improved chunking.

### Agent Requirements

The Agent shall:

- Execute more than one read-only tool for a single task.
- Aggregate tool outputs.
- Produce summarized business answers.
- Report tool failures clearly.

## Non-Functional Requirements

The system shall:

- Keep tenant data isolated.
- Validate authentication before protected requests.
- Enforce role and permission checks for business resources.
- Keep the frontend dependent only on FastAPI.
- Handle invalid input with consistent error responses.
- Log important backend operations during development.
- Be modular and testable.
- Remain simple enough for a junior developer to understand and implement.

## Out of Scope for V1/V2

The following are future work and should not be designed in detail yet:

- Autonomous monitoring.
- Scheduled agent tasks.
- Business action execution.
- Human approval workflows for real operational changes.
- Advanced observability dashboards.
- Complex policy engines.
- External e-commerce platform integrations.
- Long-term agent memory.

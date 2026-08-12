# AI Commerce Copilot Design

## Current Scope

AI Commerce Copilot is an e-commerce assistant platform focused on Version 1 and Version 2.

The current implementation target is:

- V1: Basic AI Assistant
- V2: Smart Assistant

Versions 3 through 6 remain future roadmap ideas. They should not drive detailed implementation decisions yet.

## Goal

Build a simple, modular platform that combines:

- A Retrieval-Augmented Generation (RAG) system for grounded answers from company knowledge.
- A basic AI Agent for selecting tools and summarizing business data.
- A FastAPI backend as the main entry point and orchestrator.
- A Next.js frontend that communicates only with FastAPI.
- PostgreSQL for structured application and commerce data.
- Chroma for document chunk embeddings and vector search.

## Target Users

### Customer

- Ask questions about products.
- Ask questions about company policies.
- Ask about shipping, returns, and warranties.
- Receive answers grounded in uploaded company documents.

### Store Owner

- Query products, orders, and sales.
- Retrieve simple business metrics.
- Ask analytical questions that may require multiple tools.
- Receive summarized answers from the assistant.

### Marketing Manager

For V1/V2, the marketing manager role is limited to reading campaign data and asking basic campaign questions. Advanced campaign optimization and action execution are future work.

## Architecture Summary

The project is organized into five main areas:

- `frontend`: Next.js user interface.
- `backend`: FastAPI routes, services, repositories, authentication, authorization, and orchestration.
- `rag`: document parsing, chunking, embeddings, retrieval, search, and grounded answer generation.
- `agent`: simple tool selection, tool execution coordination, and response summarization.
- `infra`: local PostgreSQL, Chroma, scripts, deployment notes, and supporting infrastructure.

FastAPI is the main entry point. The frontend must not call PostgreSQL, Chroma, the RAG package, or the Agent package directly.

## V1 Capabilities

V1 provides a basic assistant:

- Upload documents.
- Parse PDF, DOCX, and TXT files.
- Chunk documents.
- Generate embeddings.
- Store vectors in Chroma.
- Retrieve relevant document chunks.
- Generate grounded answers with sources.
- Query products, orders, and sales through backend services.
- Use basic agent tools such as `get_products`, `get_orders`, and `get_sales`.

## V2 Capabilities

V2 improves retrieval and business question handling:

- Hybrid retrieval using semantic search and keyword search.
- Metadata filtering.
- Query rewriting.
- Improved chunking.
- Multi-document answers.
- Multi-tool agent workflows.
- Aggregated answers from multiple business data sources.

## Core Documentation

Implementation details are split across:

- `Docs/requirements.md`: V1/V2 requirements and non-functional expectations.
- `Docs/architecture.md`: system components and boundaries.
- `Docs/api.md`: API overview.
- `Docs/api-contract.md`: endpoint contracts and Pydantic request/response models.
- `Docs/db-schema.md`: PostgreSQL schema and Chroma storage notes.
- `Docs/data-flow.md`: simple request, chat, agent, and ingestion flows.

## Design Principles

- Keep V1/V2 simple and implementable.
- Prefer clear module boundaries over premature abstraction.
- Keep tenant isolation in all business and knowledge data.
- Keep FastAPI responsible for orchestration and security checks.
- Keep RAG and Agent logic reusable behind backend services.
- Design for future versions without building V3-V6 complexity now.

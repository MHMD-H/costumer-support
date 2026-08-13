# AI Commerce Copilot Design

## Current Scope

AI Commerce Copilot is focused on Version 1 and Version 2:

- V1: Basic AI Assistant
- V2: Smart Assistant

Versions 3 through 6 remain future roadmap ideas. They should not drive detailed implementation decisions yet.

## Product Surfaces

AI Commerce Copilot has two different user experiences.

### 1. Owner Dashboard

The owner dashboard is the AI Commerce Copilot web application.

It is used by:

- Store owners
- Marketing managers
- Team members
- Admins

The dashboard requires Supabase Auth login. It is used to:

- Manage uploaded knowledge documents.
- Mark knowledge as internal or public.
- View products, orders, sales, and campaign data.
- Configure the Shopify customer chatbot widget.
- Use internal AI chat and read-only agent tools.

### 2. Shopify Customer Chat Widget

The customer chatbot is embedded inside the merchant's Shopify storefront.

It is used by store customers. Customers do not register for or log in to AI Commerce Copilot.

The widget can answer customer-facing questions about:

- Products
- Shipping
- Returns
- Warranties
- Public policies

The widget must resolve the correct tenant/store from Shopify context or widget configuration. It can only use customer-safe knowledge and approved product/policy information.

## Goal

Build a simple, modular platform that combines:

- A FastAPI backend as the main entry point and orchestrator.
- A protected owner dashboard API for internal users.
- A public Shopify widget API for customer-safe chat.
- A Retrieval-Augmented Generation (RAG) system for grounded answers from company knowledge.
- A basic AI Agent for owner dashboard tool selection and business data summaries.
- A Next.js dashboard frontend that communicates only with protected FastAPI APIs.
- An embedded Shopify chat widget that communicates only with public widget APIs.
- PostgreSQL for structured application and commerce data.
- Chroma for document chunk embeddings and vector search.

## Architecture Summary

The project is organized into five main areas:

- `frontend`: Next.js owner dashboard user interface.
- `backend`: FastAPI routes, services, repositories, authentication, authorization, public widget validation, and orchestration.
- `rag`: document parsing, chunking, embeddings, retrieval, search, and grounded answer generation.
- `agent`: simple owner-dashboard tool selection, tool execution coordination, and response summarization.
- `infra`: local PostgreSQL, Chroma, scripts, deployment notes, and supporting infrastructure.

FastAPI is the main entry point for both surfaces.

The owner dashboard must not call PostgreSQL, Chroma, the RAG package, or the Agent package directly.

The Shopify widget must not call protected dashboard APIs. It must only call public widget APIs.

## V1 Capabilities

V1 provides:

- Owner dashboard login with Supabase Auth.
- Protected dashboard APIs for store/team/admin users.
- Public widget configuration lookup.
- Public customer chat inside a Shopify storefront.
- Document upload from the dashboard.
- Document visibility marking as `internal` or `public`.
- PDF, DOCX, and TXT parsing.
- Chunking and embeddings.
- Vector storage in Chroma.
- Customer-safe RAG answers with public sources.
- Internal dashboard RAG answers with tenant-scoped sources.
- Basic owner dashboard queries for products, orders, and sales.
- Basic owner dashboard agent tools such as `get_products`, `get_orders`, and `get_sales`.

## V2 Capabilities

V2 improves retrieval and business question handling:

- Hybrid retrieval using semantic search and keyword search.
- Metadata filtering by tenant, document type, source, and visibility.
- Query rewriting.
- Improved chunking.
- Multi-document customer-safe answers in the Shopify widget.
- Multi-tool owner dashboard agent workflows.
- Aggregated internal answers from multiple business data sources.

## Security Boundaries

- Protected dashboard APIs require Supabase Auth JWTs.
- Dashboard tenant context is resolved from the authenticated user and database user record.
- Public widget APIs do not require customer login.
- Public widget tenant context is resolved from `shop_domain` or `shop_id`, `widget_public_key`, and allowed domain validation.
- Public widget APIs must never expose sales, orders, campaigns, internal agent tools, private documents, or user/team/admin data.
- Public widget APIs can access only customer-facing knowledge and approved product/policy information.
- Public widget endpoints need rate limiting and domain validation.
- Public widget tools must be read-only and customer-safe.

## Core Documentation

Implementation details are split across:

- `Docs/requirements.md`: V1/V2 requirements and non-functional expectations.
- `Docs/architecture.md`: system components, product surfaces, and boundaries.
- `Docs/api.md`: protected dashboard API and public widget API overview.
- `Docs/api-contract.md`: endpoint contracts and Pydantic request/response models.
- `Docs/db-schema.md`: PostgreSQL schema and Chroma storage notes.
- `Docs/data-flow.md`: owner dashboard, public widget, chat, agent, and ingestion flows.

## Design Principles

- Keep V1/V2 simple and implementable.
- Separate internal dashboard behavior from public customer widget behavior.
- Prefer clear module boundaries over premature abstraction.
- Keep tenant isolation in all business and knowledge data.
- Keep FastAPI responsible for orchestration and security checks.
- Keep public widget behavior customer-safe by default.
- Design for future versions without building V3-V6 complexity now.

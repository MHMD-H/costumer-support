# V1/V2 Requirements

## Project Overview

AI Commerce Copilot is an AI-powered e-commerce assistant with two product surfaces:

- Owner Dashboard: an authenticated SaaS dashboard for the merchant's internal team.
- Shopify Customer Chat Widget: an embedded storefront chatbot for shoppers.

V1/V2 focus on answering customer questions from public company knowledge and helping store owners query basic business data.

The system combines:

- A FastAPI backend.
- A Next.js owner dashboard.
- A Shopify embedded customer chat widget.
- PostgreSQL for structured data.
- Chroma for vector storage.
- A RAG layer for document-grounded answers.
- A basic Agent layer for internal read-only business tools.

## User Experiences

### Owner Dashboard

The dashboard is used by:

- Store owners
- Marketing managers
- Team members
- Admins

Dashboard users must authenticate through Supabase Auth.

The dashboard shall allow internal users to:

- Manage company knowledge documents.
- Choose whether documents are `internal` or `public`.
- View product, order, sales, and campaign data according to role and permissions.
- Configure the Shopify customer chatbot widget.
- Use internal chat and read-only AI agent tools.

### Shopify Customer Chat Widget

The widget is embedded inside a merchant's Shopify storefront.

Customers do not register for or log in to AI Commerce Copilot.

The widget shall allow shoppers to:

- Ask customer-facing questions about products.
- Ask about shipping, returns, warranties, and public policies.
- Receive grounded answers from public knowledge.
- Continue a widget conversation using a public conversation ID.

The widget shall use tenant/store context from Shopify integration or widget configuration.

## Version 1: Basic AI Assistant

### Dashboard Requirements

The system shall allow authenticated dashboard users to:

- Upload PDF, DOCX, and TXT documents.
- Mark uploaded documents as internal or public.
- Query products.
- Query orders.
- Query sales.
- Retrieve simple business metrics.
- Ask internal assistant questions.
- Use basic read-only agent tools.

### Widget Requirements

The system shall allow unauthenticated Shopify storefront customers to:

- Load widget configuration through a public widget endpoint.
- Ask customer-safe questions through public chat endpoints.
- Receive answers that use only public documents and approved product/policy information.

### RAG Requirements

The RAG system shall:

- Upload documents through protected FastAPI dashboard APIs.
- Support PDF parsing.
- Support DOCX parsing.
- Support TXT parsing.
- Split documents into chunks.
- Generate embeddings for chunks.
- Store chunk vectors in Chroma.
- Store document and chunk metadata in PostgreSQL.
- Track document visibility as `internal` or `public`.
- Retrieve relevant chunks for a user question.
- Filter widget retrieval to public customer-safe chunks only.
- Generate grounded answers with source references.
- Return an unknown answer when the retrieved context is insufficient.

### Agent Requirements

The Agent shall:

- Be available only to authenticated dashboard users in V1/V2.
- Use an LLM.
- Select a tool when an internal dashboard request requires structured business data.
- Call basic read-only tools for products, orders, and sales.
- Return tool results in natural language.
- Avoid executing business-changing actions in V1/V2.

## Version 2: Smart Assistant

### Dashboard Requirements

The system shall:

- Compare simple business metrics.
- Aggregate information from multiple read-only tools.
- Answer internal analytical questions using retrieved structured data.

### Widget Requirements

The system shall:

- Answer customer questions that require more than one public document.
- Combine related public policy or product information.
- Retrieve from several public knowledge sources for the same tenant.

### RAG Requirements

The RAG system shall support:

- Semantic search.
- Keyword search.
- Hybrid retrieval.
- Metadata filtering by tenant, document, document type, source, and visibility.
- Query rewriting for better retrieval.
- Improved chunking.

### Agent Requirements

The Agent shall:

- Execute more than one read-only dashboard tool for a single internal task.
- Aggregate tool outputs.
- Produce summarized business answers.
- Report tool failures clearly.

## API Requirements

The system shall expose two API groups.

### Protected Dashboard APIs

Protected dashboard APIs:

- Require Supabase Auth JWT.
- Resolve `tenant_id` from the authenticated user and database user record.
- Can access business data according to role and permissions.
- Are used only by the AI Commerce Copilot dashboard.

Examples:

- `/auth/*`
- `/products`
- `/orders`
- `/sales`
- `/documents`
- `/conversations`
- `/search`
- `/agent/tools`

### Public Widget APIs

Public widget APIs:

- Do not require customer login to AI Commerce Copilot.
- Resolve `tenant_id` from `shop_domain` or `shop_id`, `widget_public_key`, and allowed domain validation.
- Must not expose private business data.
- Are limited to customer-safe RAG/chat behavior.
- Need rate limiting and domain validation.

Public widget endpoints:

- `GET /public/widget/config`
- `POST /public/chat`
- `POST /public/chat/stream`

## Security Boundaries

Public widget APIs must never expose:

- Sales
- Orders
- Campaigns
- Internal agent tools
- Private documents
- User, team, or admin data

Public widget APIs can access only:

- Public documents.
- Customer-facing product information from products where `tenant_id` matches the resolved tenant and `public_visible = true`.
- Approved shipping, return, warranty, and policy content.

Public widget product context is used internally by `/public/chat` and `/public/chat/stream`. V1/V2 should not expose a standalone public products endpoint. Public widget answers may only expose product `id`, `external_product_id`, `name`, `description`, `category`, and `price`.

Public widget APIs must never expose product cost, profit, revenue, internal notes, orders, sales, campaigns, dashboard users, or agent tools.

## Authorization Matrix

The detailed V1/V2 RBAC and ACL rules are defined in `Docs/system-design.md`.

## Non-Functional Requirements

The system shall:

- Keep tenant data isolated.
- Validate authentication before protected requests.
- Enforce role and permission checks for business resources.
- Keep dashboard frontend calls limited to protected FastAPI APIs.
- Keep Shopify widget calls limited to public widget FastAPI APIs.
- Validate public widget origin/domain and widget key.
- Rate limit public widget endpoints.
- Handle invalid input with consistent error responses.
- Log important backend operations during development.
- Be modular and testable.
- Remain simple enough for a junior developer to understand and implement.

## Out of Scope for V1/V2

The following are future work and should not be designed in detail yet:

- Advanced Shopify billing.
- Shopify OAuth app installation.
- Shopify webhook processing.
- Autonomous monitoring.
- Scheduled agent tasks.
- Business action execution.
- Human approval workflows for real operational changes.
- Advanced observability dashboards.
- Complex policy engines.
- Long-term agent memory.

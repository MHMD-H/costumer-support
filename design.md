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
- Orders
- Sales
- Campaigns
- Documents metadata
- Conversations
- Messages
- Feedback
- Agent actions
- Approval records

### Chroma

Chroma stores vector embeddings for RAG retrieval:

- Document chunks
- Product documentation chunks
- Company policies
- SOPs
- Marketing guidelines
- Historical reports

## Data Model

### users

- `id`
- `name`
- `email`
- `role`
- `created_at`
- `updated_at`

### products

- `id`
- `name`
- `description`
- `category`
- `status`
- `created_at`
- `updated_at`

### orders

- `id`
- `user_id`
- `status`
- `total_amount`
- `created_at`
- `updated_at`

### sales

- `id`
- `order_id`
- `product_id`
- `amount`
- `created_at`

### campaigns

- `id`
- `name`
- `channel`
- `spend`
- `revenue`
- `roas`
- `created_at`
- `updated_at`

### documents

- `id`
- `title`
- `type`
- `source`
- `created_at`
- `updated_at`
- `visibility`
- `tenant_id`
### document_chunks

- `id`
- `document_id`
- `chunk_index`
- `content`
- `chroma_vector_id`
- `metadata`
- `created_at`
- `visibility`
- `tenant_id`


### conversations

- `id`
- `user_id`
- `status`
- `created_at`
- `updated_at`

### messages

- `id`
- `conversation_id`
- `sender`
- `content`
- `sources`
- `created_at`

### feedback

- `id`
- `user_id`
- `conversation_id`
- `message_id`
- `rating`
- `comment`
- `created_at`

### agent_tools

- `id`
- `name`
- `description`
- `created_at`

### agent_actions

- `id`
- `user_id`
- `type`
- `status`
- `approval_status`
- `created_at`
- `updated_at`

## Frontend Architecture

The frontend will be built as a professional, interactive dashboard application for the AI Commerce Copilot platform.

---

### Frontend Technology Stack

The frontend shall use the following technologies:

- **Next.js**: React framework for routing, layouts, pages, and production-ready frontend structure.
- **TypeScript**: Type-safe development and better maintainability.
- **Tailwind CSS**: Utility-first styling for fast, consistent, and responsive UI development.
- **shadcn/ui**: Professional reusable UI components such as buttons, dialogs, forms, tables, tabs, cards, and dropdowns.
- **Framer Motion**: Smooth animations and micro-interactions.
- **TanStack Query**: API data fetching, caching, loading states, and error handling.
- **React Hook Form**: Form state management.
- **Zod**: Frontend validation schemas.
- **Recharts**: Charts and visual analytics.
- **Lucide React**: Clean and consistent icon system.
- **next-themes**: Light mode and dark mode support.
## Chat Flow

1. User sends a request to `/chat` or `/chat/stream`.
2. System identifies the user role.
3. System stores the user message in PostgreSQL.
4. System retrieves relevant company knowledge from Chroma.
5. System retrieves structured business data from PostgreSQL when needed.
6. AI Agent selects the needed tool if the request requires orders, products, sales, campaigns, or actions.
7. System generates a grounded answer using retrieved knowledge and business data.
8. If the response is streamed, `/chat/stream` sends the answer using SSE.
9. If the request needs action execution, the Agent creates a pending action.
10. Store Owner or Marketing Manager approves or rejects the action through `/agent/actions/{id}/approval`.
11. System stores the assistant response in PostgreSQL.
12. User can submit feedback through `/feedback`.

## Requirements

# DESIGN.md

# AI Commerce Copilot — System Requirements

## 1. Project Overview

AI Commerce Copilot is an AI-powered platform for E-commerce businesses that combines a **Retrieval-Augmented Generation (RAG)** system with an **AI Agent**.

The system evolves incrementally through multiple versions, starting as a knowledge assistant and gradually becoming an autonomous business copilot capable of reasoning over business data, consulting company knowledge, and safely executing actions with human approval.

---

# 2. Vision

Build a production-grade AI platform that can:

- Answer customer questions accurately using company knowledge.
- Assist store owners with business insights.
- Analyze operational and sales data.
- Recommend business decisions.
- Execute approved business actions.
- Eventually operate as an autonomous AI copilot.

---

# 3. Target Users

## Customer

Uses the assistant to:

- Ask about products.
- Ask about return policies.
- Ask about shipping.
- Ask about warranties.
- Receive grounded answers from company knowledge.

---

## Store Owner

Uses the assistant to:

- Analyze sales.
- Analyze products.
- Analyze orders.
- Compare business performance.
- Receive recommendations.
- Approve AI actions.

---

## Marketing Manager

Uses the assistant to:

- Analyze campaigns.
- Improve ROAS.
- Review recommendations.
- Execute marketing actions safely.

---

# 4. High-Level Architecture

The system consists of two major components.

## RAG Layer

Responsible for:

- Knowledge ingestion
- Document processing
- Retrieval
- Grounded answer generation

---

## Agent Layer

Responsible for:

- Planning
- Tool calling
- Data analysis
- Decision making
- Action execution
- Human approval workflow

---

# 5. Functional Requirements

---

# Version 1 — Basic AI Assistant

## Objective

Provide a basic AI assistant for both customers and store owners.

---

## Customer Requirements

The system shall allow customers to:

- Ask questions about products.
- Ask questions about company policies.
- Receive answers grounded in uploaded documents.

---

## Store Owner Requirements

The system shall allow store owners to:

- Retrieve simple business metrics.
- Query orders.
- Query products.
- Query sales.

---

## RAG Requirements

The RAG system shall:

- Support document upload.
- Support PDF parsing.
- Support DOCX parsing.
- Support TXT parsing.
- Chunk documents.
- Generate embeddings.
- Store vectors.
- Retrieve relevant chunks.
- Generate grounded answers.

---

## Agent Requirements

The Agent shall:

- Use an LLM.
- Support basic tool calling.
- Select the appropriate tool.
- Return tool results naturally.

Example tools:

- get_sales()
- get_orders()
- get_products()

---

# Version 2 — Smart Assistant

## Objective

Support more complex reasoning and retrieval.

---

## Customer Requirements

The system shall:

- Answer questions requiring multiple documents.
- Combine multiple company policies.
- Retrieve information from several knowledge sources.

---

## Store Owner Requirements

The system shall:

- Compare multiple business metrics.
- Aggregate information from several tools.
- Answer analytical business questions.

---

## RAG Requirements

The RAG system shall support:

- Hybrid Retrieval
- Semantic Search
- Keyword Search
- Metadata Filtering
- Query Rewriting
- Improved Chunking

---

## Agent Requirements

The Agent shall:

- Execute multiple tools in one task.
- Aggregate outputs.
- Produce summarized business answers.

---

# Version 3 — AI Business Analyst

## Objective

Transform the AI Agent into a business analyst.

---

## Customer Requirements

The system shall maintain all previous customer capabilities.

---

## Store Owner Requirements

The system shall:

- Analyze business performance.
- Explain sales drops.
- Detect possible causes.
- Produce analytical reports.

---

## RAG Requirements

The RAG system shall support:

- Context Selection
- Reranking
- Source Citations
- Source Display
- Unknown-answer behavior

---

## Agent Requirements

The Agent shall:

- Decompose tasks.
- Plan execution.
- Select tools dynamically.
- Analyze retrieved data.
- Retry failed operations.
- Recover from tool failures.

---

# Version 4 — AI Business Copilot

## Objective

Combine business data with enterprise knowledge.

---

## Store Owner Requirements

The system shall:

- Analyze business metrics.
- Retrieve company SOPs.
- Retrieve marketing guidelines.
- Generate recommendations aligned with company policies.

---

## RAG Requirements

The knowledge base shall contain:

- SOPs
- Marketing Guidelines
- Company Policies
- Product Documentation
- Historical Reports

The RAG system shall expose a reusable retrieval interface that can be invoked by the AI Agent.

---

## Agent Requirements

The Agent shall:

- Understand user goals.
- Create execution plans.
- Retrieve structured data.
- Retrieve enterprise knowledge.
- Combine both sources.
- Generate business recommendations.

---

# Version 5 — AI Operator

## Objective

Allow the Agent to safely execute business operations.

---

## Store Owner Requirements

The system shall allow owners to:

- Request operational changes.
- Review pending actions.
- Approve or reject AI decisions.

---

## RAG Requirements

The knowledge system shall validate whether requested actions comply with company policies.

---

## Agent Requirements

The Agent shall:

- Execute operational tools.
- Request human approval.
- Integrate with external APIs.
- Verify completed actions.
- Produce audit logs.
- Handle failures safely.

---

# Version 6 — Autonomous Growth Copilot

## Objective

Create an autonomous business assistant capable of continuous monitoring.

---

## Store Owner Requirements

The system shall:

- Monitor business performance.
- Detect anomalies.
- Detect opportunities.
- Generate recommendations.
- Prepare executable actions.
- Request approval before execution.
- Produce business reports.

---

## RAG Requirements

The RAG system shall evolve into an Enterprise Knowledge Engine supporting:

- Multi-tenant knowledge bases
- Document permissions
- Versioning
- Advanced Retrieval
- Reranking
- Citations
- Evaluation
- Access Control
- Historical Knowledge

---

## Agent Requirements

The Agent shall support:

- Long-term memory
- Autonomous monitoring
- Scheduled tasks
- Planning
- Tool orchestration
- Business actions
- Guardrails
- Approval policies
- Verification
- Observability

---

# 6. Non-Functional Requirements

The system shall:

- Be modular.
- Be production-ready.
- Support scalability.
- Support observability.
- Support authentication.
- Support authorization.
- Isolate tenant data.
- Log all important operations.
- Handle failures gracefully.
- Be extensible.
- Be testable.
- Be secure by default.

---

# 7. Milestones

| Version | Goal |
|----------|------|
| V1 | Basic AI Assistant |
| V2 | Smart Assistant |
| V3 | AI Business Analyst |
| V4 | AI Business Copilot |
| V5 | AI Operator |
| V6 | Autonomous Growth Copilot |

---

# 8. Portfolio Strategy

- **V2** delivers a solid RAG + Agent demonstration suitable for showcasing core AI engineering skills.
- **V3** demonstrates business reasoning and analytical capabilities.
- **V4** represents the primary portfolio milestone and recommended first production target.
- **V5** introduces production-safe action execution suitable for freelance client demonstrations.
- **V6** represents the long-term SaaS vision with autonomous business operations.

---

# 9. Current Target

The immediate project objective is to complete **Version 4 (AI Business Copilot)**.

This version provides the best balance between:

- Production readiness
- Portfolio quality
- Freelancing opportunities
- Future SaaS extensibility

Subsequent versions (V5 and V6) extend the platform toward a fully autonomous commercial AI product without requiring major architectural redesign.

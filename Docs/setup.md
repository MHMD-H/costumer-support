# Setup

## Current Scaffold Status

This project is currently a V1/V2 API contract scaffold. It is intended to make
route shapes, request models, response models, and basic local tests runnable
before the production integrations are added.

### DB

- Current status: placeholder repository files and no real DB connection.
- Why placeholder: SQL schema and migrations have not been finalized in code.
- Replace when: SQL schema/migrations are created and approved.
- Target implementation: PostgreSQL/Supabase SQL-backed repositories.

### Auth

- Current status: placeholder bearer-token validation only.
- Why placeholder: local/mock API testing needs protected-route behavior before
  real user sessions are wired.
- Replace when: dashboard auth moves from local/mock testing to real user
  sessions.
- Target implementation: Supabase JWT verification plus DB-backed user and
  tenant lookup.

### RAG

- Current status: placeholder/mock responses.
- Why placeholder: ingestion, embeddings, vector indexing, and retrieval are not
  implemented yet.
- Replace when: document ingestion, embeddings, and retrieval pipeline are
  implemented.
- Target implementation: real retrieval over indexed document chunks.

### Agent

- Current status: placeholder/mock tool list or mock agent behavior.
- Why placeholder: safe tool execution and orchestration are separate follow-up
  work.
- Replace when: real tool execution and orchestration are implemented.
- Target implementation: real agent service that calls backend services/tools
  safely.

### Document Processing

- Current status: upload contract exists, but parsing/chunking/embedding are not
  implemented.
- Why placeholder: the API contract can be tested before ingestion internals are
  ready.
- Replace when: RAG ingestion iterations implement parsing, chunking,
  embeddings, and status updates.
- Target implementation: validated file upload, metadata persistence, text
  extraction, chunking, embeddings, and processing status updates.

### Public Security

- Current status: placeholder widget/origin/rate-limit validation.
- Why placeholder: local/mock widget tests need the public route contract before
  production store validation exists.
- Replace when: public widget is exposed beyond local/mock testing.
- Target implementation: widget key validation, allowed-origin checks, tenant
  lookup, and rate limiting.

### Filters And Pagination

- Current status: query params may exist, but real filtering/pagination against
  persistent data is deferred.
- Why placeholder: current responses come from in-memory mock service helpers,
  not repository queries.
- Replace when: database repositories are implemented.
- Target implementation: SQL-backed filtering and pagination with tenant
  filters.

## Backend Tests

Install dependencies from the repository root:

```powershell
python -m pip install -r requirements.txt
```

Run the backend tests:

```powershell
python -m pytest backend/tests -q
```

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

- Current status: authenticated PDF, DOCX, and TXT uploads are size-bounded,
  structurally validated, staged under the trusted tenant, and processed by the
  standalone ingestion worker. Authentication and upload permission checks run
  before multipart parsing. The worker rotates between queued tenants when
  possible and records safe `ready` or `failed` status.
- Resource limits: 5 MB input, bounded multipart bytes, at most 500 PDF pages,
  bounded DOCX entries/expanded bytes, and at most 2,000,000 extracted text
  characters before chunking and embedding. PDF/DOCX validation and text
  extraction run in killable subprocesses with a 30-second wall-clock limit
  and a 1 GB process-memory limit.
- Production boundary: the current private local staging model is for the
  documented single-host deployment only. Do not enable production merchant
  uploads until shared private storage and a fail-closed malware-scanning
  provider are selected and configured.

### Public Security

- Current status: public widget routes resolve an enabled tenant from the exact
  store/widget mapping, require an allowlisted HTTPS storefront origin, and
  apply a bounded per-client rate limit. Public chat request bodies are capped
  before JSON parsing, with additional maximum lengths on public string fields.
- Public chat currently returns a customer-safe placeholder without sources.
  Real public retrieval must use the resolved tenant and public-only RAG filter;
  optional product context is limited to same-tenant `public_visible` products.
- The current rate limiter is process-local for the documented single-process
  deployment. Use a shared limiter before running multiple API workers or hosts.

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

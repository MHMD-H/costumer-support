# AI Commerce Copilot

AI Commerce Copilot is a V1/V2-first e-commerce assistant platform with a Next.js frontend, FastAPI backend, RAG system, AI agent, and local infrastructure setup.

The backend is currently an explicit scaffold: route contracts, Pydantic schemas,
mock service responses, and local tests exist while DB, Supabase auth, RAG,
agent orchestration, document processing, public widget security, and
SQL-backed filters/pagination are intentionally deferred. See `Docs/setup.md`
for the current placeholder status and replacement criteria.

# Document upload staging (Task 20)

Set `DOCUMENT_UPLOAD_DIR` to a private, persistent directory before using
`POST /documents`. Accepted files are retained under
`<DOCUMENT_UPLOAD_DIR>/<trusted tenant UUID>/<document UUID>.<validated type>`.
The upload limit is 5 MB per file. This local staging requires a shared,
durable storage and malware-scanning decision before production merchant
uploads. Files remain `uploaded` until Tasks 21–22 add ingestion and status
tracking.

Task 21 provides a document-service call into the existing LangChain pipeline
for stored TXT, PDF, and DOCX files. Uploads still remain `uploaded` until
Task 22 schedules ingestion and persists chunks and processing status.

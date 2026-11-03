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
uploads. Files remain `uploaded` until the Task 22 worker claims them.
Authentication, tenant resolution, and upload permission checks complete before
the multipart body is parsed. The API counts streamed request bytes without
buffering the body in middleware, validates file structure, caps PDF pages and
DOCX expansion, and rejects excessive extracted text before chunking. Untrusted
PDF and DOCX validation and extraction run in killable subprocesses with 30-second and 1 GB
limits so parser expansion cannot indefinitely occupy the API or worker process.

Task 21 provides a document-service call into the existing LangChain pipeline
for stored TXT, PDF, and DOCX files. Task 22 runs ingestion in a separate worker.
For the current single-host setup, set `DATABASE_URL`, `DOCUMENT_UPLOAD_DIR`,
and `CHROMA_PERSIST_DIRECTORY` to persistent paths accessible to the API and
worker. Install the root requirements, then start one worker from `backend/`
with `PYTHONPATH=src` and `python -m app.features.document_worker`. The worker
uses a PostgreSQL advisory lock to enforce one active instance, resumes
interrupted `processing` documents on restart, and records `ready` or `failed`
plus a safe failure reason. Failed documents can be queued again with
`POST /documents/{id}/retry` by a user with document management permission.
Replacing a file with `PUT /documents/{id}` validates and stages a new revision,
then queues it for the same worker.
The single worker prioritizes a tenant other than the one it processed most
recently whenever another tenant has queued work, preventing one tenant's FIFO
backlog from starving all others.

This setup is for one host. A multi-host deployment still needs a shared
private file store and a shared Chroma service or volume, plus a deployment
decision for the worker. Real production merchant uploads remain disabled until
a shared private storage model and fail-closed malware scanner are selected.

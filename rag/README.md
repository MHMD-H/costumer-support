# Standalone RAG ingestion

Install dependencies with `python -m pip install -r rag/requirements.txt`.

The ingestion flow is independent of FastAPI:

1. Select a loader with `create_loader`; ordinary local file types are inferred.
2. Split with `SourceAwareChunker`.
3. Create a configurable LangChain embedding implementation with
   `create_embeddings` (default: `BAAI/bge-small-en-v1.5`).
4. Store chunks and filter-ready metadata with `ChromaStore`.
5. Run the steps together with `IngestionPipeline`.

Use `IngestionPipeline.from_settings()` for the default end-to-end pipeline and
`pipeline.ingest_source(path, tenant_id="...")` for inferred local files. Pass
`source_type="web"` or `source_type="notion"` explicitly because those sources
cannot be identified reliably from a path alone.

`NotionMarkdownLoader` accepts Markdown fetched by a connector/API or a local
Notion Markdown export. This keeps authentication separate and makes ingestion
testable without API keys. `CSVLoader` intentionally raises `NotImplementedError`:
FAQ/knowledge, catalog, order, and sales rows require distinct formatting,
privacy, identifier, update, and chunking policies.

No PostgreSQL or backend service is used in this phase.

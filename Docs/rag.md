# RAG

RAG covers ingestion, parsing, chunking, embeddings, retrieval, search, and grounded generation.

For V1/V2, retrieval must respect product surface boundaries:

- Dashboard RAG can use tenant-scoped internal and public knowledge according to user permissions.
- Shopify widget RAG can use only public customer-facing knowledge and approved product/policy information.

Document and chunk metadata should include tenant and visibility information so retrieval can filter safely.

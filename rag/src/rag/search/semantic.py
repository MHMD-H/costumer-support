"""Semantic search."""

from __future__ import annotations

from collections.abc import Iterable
import math

from langchain_core.embeddings import Embeddings

from rag.core.contracts import Chunk, SearchResult


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimensions")
    denominator = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def semantic_search(
    query: str,
    chunks: Iterable[Chunk],
    *,
    embedder: Embeddings,
    top_k: int = 5,
) -> list[SearchResult]:
    query_embedding = embedder.embed_query(query)
    chunk_list = list(chunks)
    chunk_embeddings = embedder.embed_documents([chunk.content for chunk in chunk_list])
    results: list[SearchResult] = []

    for chunk, chunk_embedding in zip(chunk_list, chunk_embeddings):
        score = _cosine_similarity(query_embedding, chunk_embedding)
        if score > 0:
            results.append(SearchResult(chunk=chunk, score=score, semantic_score=score))

    return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

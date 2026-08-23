"""Keyword search."""

from __future__ import annotations

from collections.abc import Iterable
import re

from rag.core.contracts import Chunk, SearchResult

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def keyword_search(query: str, chunks: Iterable[Chunk], top_k: int = 5) -> list[SearchResult]:
    query_terms = set(tokenize(query))
    if not query_terms:
        return []

    results: list[SearchResult] = []
    query_lower = query.lower()
    for chunk in chunks:
        chunk_terms = set(tokenize(chunk.content))
        overlap = query_terms & chunk_terms
        if not overlap:
            continue
        score = len(overlap) / len(query_terms)
        if query_lower in chunk.content.lower():
            score += 0.25
        results.append(SearchResult(chunk=chunk, score=score, keyword_score=score))

    return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

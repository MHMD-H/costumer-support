"""Metadata filtering for retrieval."""

from __future__ import annotations

from collections.abc import Iterable

from rag.core.contracts import Chunk, Visibility


def filter_chunks(
    chunks: Iterable[Chunk],
    *,
    tenant_id: str,
    allowed_visibility: set[Visibility] | None = None,
) -> list[Chunk]:
    allowed = {"public", "internal"} if allowed_visibility is None else allowed_visibility
    return [
        chunk
        for chunk in chunks
        if chunk.tenant_id == tenant_id and chunk.visibility in allowed
    ]

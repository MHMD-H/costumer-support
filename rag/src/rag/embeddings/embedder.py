"""Embedding generation adapter."""

from __future__ import annotations

from dataclasses import dataclass
from langchain_core.embeddings import Embeddings


@dataclass(frozen=True)
class EmbeddingConfig:
    """Provider-independent embedding configuration."""

    provider: str = "huggingface"
    model_name: str = "BAAI/bge-small-en-v1.5"
    device: str = "cpu"
    normalize_embeddings: bool = True


def create_embeddings(config: EmbeddingConfig | None = None) -> Embeddings:
    """Create the configured LangChain embedding provider."""
    selected = config or EmbeddingConfig()
    if selected.provider != "huggingface":
        raise ValueError(f"Unsupported embedding provider: {selected.provider}")
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:
        raise RuntimeError(
            "Install rag/requirements.txt to use Hugging Face embeddings"
        ) from exc
    return HuggingFaceEmbeddings(
        model_name=selected.model_name,
        model_kwargs={"device": selected.device},
        encode_kwargs={"normalize_embeddings": selected.normalize_embeddings},
    )

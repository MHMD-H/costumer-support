import sys
from types import SimpleNamespace

from rag.embeddings.embedder import EmbeddingConfig, create_embeddings


def test_default_embedding_model_is_local_bge() -> None:
    config = EmbeddingConfig()
    assert config.provider == "huggingface"
    assert config.model_name == "BAAI/bge-small-en-v1.5"


def test_unknown_embedding_provider_is_rejected() -> None:
    try:
        create_embeddings(EmbeddingConfig(provider="unknown"))
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("unsupported provider should fail")


def test_huggingface_factory_passes_configured_bge_model(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeHuggingFaceEmbeddings:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "langchain_huggingface",
        SimpleNamespace(HuggingFaceEmbeddings=FakeHuggingFaceEmbeddings),
    )
    create_embeddings(EmbeddingConfig())

    assert captured["model_name"] == "BAAI/bge-small-en-v1.5"
    assert captured["encode_kwargs"] == {"normalize_embeddings": True}

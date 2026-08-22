"""CSV ingestion boundary."""


class CSVLoader:
    """Placeholder until the dataset semantics and privacy rules are known."""

    def __init__(self, *_: object, **__: object) -> None:
        pass

    def load(self) -> list[object]:
        # TODO: CSV needs a separate strategy depending on whether rows represent
        # FAQ/knowledge, products, orders, sales, or other structured/private data.
        # Each needs different text, identifiers, privacy, updates, and chunking.
        raise NotImplementedError(
            "CSV ingestion requires a strategy tailored to the dataset semantics"
        )

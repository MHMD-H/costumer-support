"""Pagination response helpers."""

from app.features.schemas import PageMeta


def page(limit: int, offset: int, total: int) -> PageMeta:
    return PageMeta(limit=limit, offset=offset, total=total)

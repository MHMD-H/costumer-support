"""Small, typed helpers for list endpoint pagination."""

import base64
import binascii
import json
from datetime import datetime
from typing import TypeVar
from uuid import UUID

from app.features.schemas import OffsetPaginationResponse


T = TypeVar("T")


def offset_pagination(
    response_type: type[OffsetPaginationResponse[T]],
    items: list[T],
    *,
    limit: int,
    offset: int,
    total: int,
) -> OffsetPaginationResponse[T]:
    return response_type(
        items=items,
        limit=limit,
        offset=offset,
        page=(offset // limit) + 1,
        total=total,
        has_more=offset + len(items) < total,
    )


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": str(item_id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padded_cursor = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_cursor.encode()))
        created_at = datetime.fromisoformat(payload["created_at"])
        item_id = UUID(payload["id"])
    except (binascii.Error, KeyError, TypeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Cursor is invalid.") from exc

    if created_at.tzinfo is None:
        raise ValueError("Cursor is invalid.")

    return created_at, item_id

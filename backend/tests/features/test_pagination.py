"""Focused pagination behavior tests without a live database."""

import asyncio
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.db.models import Conversation, Message
from app.features.conversations import service as conversation_service
from app.features.pagination import decode_cursor, encode_cursor, offset_pagination
from app.features.schemas import OffsetPaginationResponse


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
CONVERSATION_ID = UUID("22222222-2222-2222-2222-222222222222")
MESSAGE_ID = UUID("33333333-3333-3333-3333-333333333333")


def conversation(identifier: int, created_at: datetime) -> Conversation:
    return Conversation(
        id=UUID(f"00000000-0000-0000-0000-{identifier:012d}"),
        tenant_id=TENANT_ID,
        user_id=None,
        surface="dashboard",
        status="active",
        created_at=created_at,
        updated_at=created_at,
    )


def test_offset_response_calculates_page_has_more_and_empty_results() -> None:
    response = offset_pagination(
        OffsetPaginationResponse[str],
        ["a", "b"],
        limit=2,
        offset=2,
        total=5,
    )
    empty = offset_pagination(
        OffsetPaginationResponse[str],
        [],
        limit=20,
        offset=0,
        total=0,
    )

    assert response.page == 2
    assert response.has_more is True
    assert response.total == 5
    assert empty.model_dump() == {
        "items": [],
        "limit": 20,
        "offset": 0,
        "page": 1,
        "total": 0,
        "has_more": False,
    }


def test_cursor_round_trip_retains_timestamp_and_id() -> None:
    created_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    cursor = encode_cursor(created_at, CONVERSATION_ID)

    assert decode_cursor(cursor) == (created_at, CONVERSATION_ID)


def test_conversation_cursor_pagination_has_no_duplicates_with_tied_timestamps(monkeypatch) -> None:
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first, second, third = (conversation(value, created_at) for value in (3, 2, 1))
    captured_boundaries = []

    async def list_conversations(session, tenant_id, *, status, limit, cursor_created_at, cursor_id):
        captured_boundaries.append((cursor_created_at, cursor_id))
        if cursor_id is None:
            return [first, second, third]
        return [third]

    monkeypatch.setattr(conversation_service.conversation_repository, "list_conversations", list_conversations)

    first_page = asyncio.run(
        conversation_service.list_conversations(None, TENANT_ID, status="active", limit=2, cursor=None)
    )
    second_page = asyncio.run(
        conversation_service.list_conversations(
            None,
            TENANT_ID,
            status="active",
            limit=2,
            cursor=first_page.next_cursor,
        )
    )

    assert [item.id for item in first_page.items + second_page.items] == [first.id, second.id, third.id]
    assert first_page.has_more is True
    assert first_page.next_cursor is not None
    assert second_page.has_more is False
    assert second_page.next_cursor is None
    assert captured_boundaries[1] == (second.created_at, second.id)


def test_invalid_cursor_returns_bad_request_without_querying_repository(monkeypatch) -> None:
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("Repository should not be called for an invalid cursor.")

    monkeypatch.setattr(conversation_service.conversation_repository, "list_conversations", fail_if_called)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            conversation_service.list_conversations(None, TENANT_ID, status=None, limit=20, cursor="invalid")
        )

    assert exc.value.status_code == 400
    assert exc.value.detail["message"] == "Cursor is invalid."


def test_message_list_requires_dashboard_conversation(monkeypatch) -> None:
    widget_conversation = conversation(9, datetime.now(timezone.utc))
    widget_conversation.surface = "widget"

    async def get_conversation_by_id(session, tenant_id, conversation_id):
        return widget_conversation

    monkeypatch.setattr(
        conversation_service.conversation_repository,
        "get_conversation_by_id",
        get_conversation_by_id,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            conversation_service.list_messages(
                None,
                TENANT_ID,
                CONVERSATION_ID,
                limit=20,
                cursor=None,
            )
        )

    assert exc.value.status_code == 404

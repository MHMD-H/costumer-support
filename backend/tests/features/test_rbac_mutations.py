"""Privilege mutation checks on the existing users and permissions tables."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.rbac import Permission as PermissionValue, Role
from app.db.models import Permission, User
from app.features import permissions as permission_service
from app.features.schemas import AuthUserResponse, PermissionUpdateRequest, UserUpdateRequest
from app.features.users import service as user_service


def actor(role: Role, tenant_id, user_id=None) -> AuthUserResponse:
    return AuthUserResponse(
        id=user_id or uuid4(), tenant_id=tenant_id, name="Actor",
        email="actor@example.com", role=role,
    )


def stored_user(role: Role, tenant_id, user_id=None) -> User:
    return User(
        id=user_id or uuid4(), tenant_id=tenant_id, auth_user_id=uuid4(),
        is_active=True, name="Target", email="target@example.com", role=role.value,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.parametrize(
    ("actor_role", "target_role", "new_value", "same_user", "foreign_tenant", "allowed"),
    [
        (Role.STORE_OWNER, Role.TEAM_MEMBER, PermissionValue.VIEW_ORDERS, False, False, True),
        (Role.ADMIN, Role.TEAM_MEMBER, PermissionValue.MANAGE_CAMPAIGNS, False, False, False),
        (Role.STORE_OWNER, Role.TEAM_MEMBER, PermissionValue.VIEW_DOCUMENTS, False, False, False),
        (Role.STORE_OWNER, Role.TEAM_MEMBER, PermissionValue.VIEW_ORDERS, True, False, False),
        (Role.STORE_OWNER, Role.TEAM_MEMBER, PermissionValue.VIEW_ORDERS, False, True, False),
        (Role.STORE_OWNER, Role.MARKETING_MANAGER, PermissionValue.VIEW_ORDERS, False, False, False),
    ],
)
def test_permission_mutation_respects_actor_target_and_tenant(
    monkeypatch, actor_role, target_role, new_value, same_user, foreign_tenant, allowed
) -> None:
    tenant_id = uuid4()
    target = stored_user(target_role, uuid4() if foreign_tenant else tenant_id)
    current = actor(actor_role, tenant_id, target.id if same_user else None)
    row = Permission(
        id=uuid4(), tenant_id=tenant_id, user_id=target.id,
        permission=PermissionValue.VIEW_SALES.value,
        created_at=datetime.now(timezone.utc),
    )
    writes = []

    async def get_row(_session, received_tenant_id, _permission_id):
        assert received_tenant_id == tenant_id
        return row

    async def get_user(_session, _tenant_id, _user_id):
        return target

    async def no_duplicate(*_args):
        return None

    async def update_row(_session, record, updates):
        writes.append(updates)
        record.permission = updates["permission"]
        return record

    monkeypatch.setattr(permission_service.permission_repository, "get_permission_by_id", get_row)
    monkeypatch.setattr(permission_service.user_repository, "get_user_by_id", get_user)
    monkeypatch.setattr(permission_service.permission_repository, "get_permission_by_value", no_duplicate)
    monkeypatch.setattr(permission_service.permission_repository, "update_permission", update_row)

    operation = permission_service.update_permission(
        None, tenant_id, row.id, PermissionUpdateRequest(permission=new_value),
        acting_user=current,
    )
    if allowed:
        response = asyncio.run(operation)
        assert response.permission == new_value
        assert writes == [{"permission": new_value.value}]
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(operation)
        assert error.value.status_code == 403
        assert writes == []


def test_invalid_stored_acl_value_is_denied(monkeypatch) -> None:
    tenant_id = uuid4()
    target = stored_user(Role.TEAM_MEMBER, tenant_id)
    row = Permission(
        id=uuid4(), tenant_id=tenant_id, user_id=target.id,
        permission="unknown_permission", created_at=datetime.now(timezone.utc),
    )

    async def get_row(*_args):
        return row

    async def get_user(*_args):
        return target

    monkeypatch.setattr(permission_service.permission_repository, "get_permission_by_id", get_row)
    monkeypatch.setattr(permission_service.user_repository, "get_user_by_id", get_user)

    with pytest.raises(HTTPException) as error:
        asyncio.run(permission_service.update_permission(
            None, tenant_id, row.id,
            PermissionUpdateRequest(permission=PermissionValue.VIEW_ORDERS),
            acting_user=actor(Role.STORE_OWNER, tenant_id),
        ))
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    ("actor_role", "new_role", "same_user", "allowed"),
    [
        (Role.ADMIN, Role.STORE_OWNER, False, False),
        (Role.ADMIN, Role.ADMIN, True, False),
        (Role.STORE_OWNER, Role.MARKETING_MANAGER, False, True),
    ],
)
def test_user_role_update_cannot_self_escalate_or_assign_above_actor(
    monkeypatch, actor_role, new_role, same_user, allowed
) -> None:
    tenant_id = uuid4()
    target = stored_user(Role.ADMIN if same_user else Role.TEAM_MEMBER, tenant_id)
    current = actor(actor_role, tenant_id, target.id if same_user else None)
    writes = []

    async def get_user(*_args):
        return target

    async def update_user(_session, record, updates):
        writes.append(updates)
        for field, value in updates.items():
            setattr(record, field, value)
        return record

    monkeypatch.setattr(user_service.user_repository, "get_user_by_id", get_user)
    monkeypatch.setattr(user_service.user_repository, "update_user", update_user)
    operation = user_service.update_user(
        None, tenant_id, target.id, UserUpdateRequest(role=new_role), acting_user=current
    )
    if allowed:
        assert asyncio.run(operation).role == new_role
        assert writes[0]["role"] == new_role.value
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(operation)
        assert error.value.status_code == 403
        assert writes == []


def test_invalid_role_and_permission_payloads_are_forbidden() -> None:
    with pytest.raises(HTTPException) as role_error:
        UserUpdateRequest(role="super_admin")
    with pytest.raises(HTTPException) as permission_error:
        PermissionUpdateRequest(permission="view_everything")
    assert role_error.value.status_code == 403
    assert permission_error.value.status_code == 403

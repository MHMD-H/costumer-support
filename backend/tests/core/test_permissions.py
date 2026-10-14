"""Closed Task 7 role policy and tenant-scoped ACL resolution."""

import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.permissions import checked_permission, checked_role, get_effective_permissions
from app.core.rbac import Permission, Role, ROLE_GRANTABLE_PERMISSIONS, ROLE_PERMISSIONS
from app.core.tenant_context import TenantContext
from app.features.schemas import AuthUserResponse


def test_closed_role_and_permission_matrix() -> None:
    assert {role.value for role in Role} == {
        "store_owner", "admin", "marketing_manager", "team_member"
    }
    assert ROLE_PERMISSIONS[Role.STORE_OWNER] == frozenset(Permission)
    assert ROLE_PERMISSIONS[Role.ADMIN] == frozenset({
        Permission.VIEW_USERS, Permission.MANAGE_USERS, Permission.VIEW_PERMISSIONS,
        Permission.MANAGE_PERMISSIONS, Permission.VIEW_TENANT, Permission.MANAGE_TENANT,
        Permission.VIEW_PRODUCTS, Permission.MANAGE_PRODUCTS, Permission.VIEW_ORDERS,
        Permission.VIEW_SALES, Permission.VIEW_CAMPAIGNS, Permission.VIEW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS, Permission.MANAGE_DOCUMENTS,
        Permission.VIEW_CONVERSATIONS, Permission.CREATE_CONVERSATIONS,
        Permission.USE_DASHBOARD_CHAT, Permission.SEARCH_KNOWLEDGE,
        Permission.SUBMIT_FEEDBACK, Permission.USE_AGENT_TOOLS,
    })
    assert ROLE_PERMISSIONS[Role.MARKETING_MANAGER] == frozenset({
        Permission.VIEW_USERS, Permission.VIEW_PRODUCTS, Permission.MANAGE_PRODUCTS,
        Permission.VIEW_ORDERS, Permission.VIEW_SALES, Permission.VIEW_CAMPAIGNS,
        Permission.MANAGE_CAMPAIGNS, Permission.VIEW_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS, Permission.MANAGE_DOCUMENTS,
        Permission.VIEW_CONVERSATIONS, Permission.CREATE_CONVERSATIONS,
        Permission.USE_DASHBOARD_CHAT, Permission.SEARCH_KNOWLEDGE,
        Permission.SUBMIT_FEEDBACK, Permission.USE_AGENT_TOOLS,
    })
    assert ROLE_PERMISSIONS[Role.TEAM_MEMBER] == frozenset({
        Permission.VIEW_USERS, Permission.VIEW_PRODUCTS,
        Permission.USE_DASHBOARD_CHAT, Permission.SEARCH_KNOWLEDGE,
        Permission.USE_AGENT_TOOLS,
    })
    assert ROLE_GRANTABLE_PERMISSIONS == {Role.TEAM_MEMBER: frozenset({
        Permission.MANAGE_PRODUCTS, Permission.VIEW_ORDERS, Permission.VIEW_SALES,
        Permission.VIEW_CAMPAIGNS, Permission.MANAGE_CAMPAIGNS,
        Permission.CREATE_CONVERSATIONS, Permission.SUBMIT_FEEDBACK,
    })}


@pytest.mark.parametrize("value", ["owner", "super_admin", "", None])
def test_unknown_roles_are_denied(value) -> None:
    with pytest.raises(HTTPException) as error:
        checked_role(value)
    assert error.value.status_code == 403


@pytest.mark.parametrize("value", ["view_everything", "VIEW_ORDERS", "", None])
def test_unknown_permissions_are_denied(value) -> None:
    with pytest.raises(HTTPException) as error:
        checked_permission(value)
    assert error.value.status_code == 403


@pytest.mark.parametrize(
    ("stored", "expected_status"),
    [
        (["view_orders"], None),
        ([], None),
        (["view_orders", "unknown_permission"], 403),
        (["view_documents"], 403),
    ],
)
def test_team_member_effective_permissions_use_only_valid_same_tenant_grants(
    monkeypatch, stored, expected_status
) -> None:
    tenant_id, user_id = uuid4(), uuid4()
    user = AuthUserResponse(
        id=user_id, tenant_id=tenant_id, name="Member",
        email="member@example.com", role=Role.TEAM_MEMBER,
    )

    async def rows(_session, received_tenant_id, received_user_id):
        assert (received_tenant_id, received_user_id) == (tenant_id, user_id)
        return [(value, tenant_id) for value in stored]

    monkeypatch.setattr(
        "app.core.permissions.permission_repository.list_user_permission_values", rows
    )
    if expected_status:
        with pytest.raises(HTTPException) as error:
            asyncio.run(get_effective_permissions(user, TenantContext(tenant_id), None))
        assert error.value.status_code == expected_status
    else:
        effective = asyncio.run(get_effective_permissions(user, TenantContext(tenant_id), None))
        assert effective == ROLE_PERMISSIONS[Role.TEAM_MEMBER] | {
            Permission(value) for value in stored
        }


def test_effective_permissions_reject_mismatched_trusted_tenant() -> None:
    user = AuthUserResponse(
        id=uuid4(), tenant_id=uuid4(), name="Owner",
        email="owner@example.com", role=Role.STORE_OWNER,
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_effective_permissions(user, TenantContext(uuid4()), None))
    assert error.value.status_code == 403


def test_effective_permissions_reject_cross_tenant_acl_row(monkeypatch) -> None:
    tenant_id, user_id = uuid4(), uuid4()
    user = AuthUserResponse(
        id=user_id, tenant_id=tenant_id, name="Member",
        email="member@example.com", role=Role.TEAM_MEMBER,
    )

    async def rows(_session, _tenant_id, _user_id):
        return [(Permission.VIEW_ORDERS.value, uuid4())]

    monkeypatch.setattr(
        "app.core.permissions.permission_repository.list_user_permission_values", rows
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_effective_permissions(user, TenantContext(tenant_id), None))
    assert error.value.status_code == 403

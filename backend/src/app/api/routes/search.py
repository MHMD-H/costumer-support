"""Search API routes."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import EffectivePermissionsDep, forbidden, require_permission
from app.core.rbac import Permission
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])

SCOPE_PERMISSIONS: dict[str, Permission] = {
    "knowledge": Permission.VIEW_DOCUMENTS,
    "products": Permission.VIEW_PRODUCTS,
    "orders": Permission.VIEW_ORDERS,
    "sales": Permission.VIEW_SALES,
    "campaigns": Permission.VIEW_CAMPAIGNS,
}


@router.post("", dependencies=[Depends(require_permission(Permission.SEARCH_KNOWLEDGE))])
def search(
    request: SearchRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    effective_permissions: EffectivePermissionsDep,
) -> SearchResponse:
    if request.scope == "all":
        return SearchResponse(items=[
            item
            for scope, required in SCOPE_PERMISSIONS.items()
            if required in effective_permissions
            for item in mock_services.search(request.model_copy(update={"scope": scope})).items
            if item.type == scope
        ])
    if SCOPE_PERMISSIONS[request.scope] not in effective_permissions:
        raise forbidden()
    response = mock_services.search(request)
    return SearchResponse(items=[
        item for item in response.items if item.type == request.scope
    ])

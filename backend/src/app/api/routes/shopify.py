"""Authenticated Shopify connection endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from app.core.auth import CurrentApplicationUserDep, unauthorized
from app.core.rbac import Role
from app.core.permissions import forbidden, require_shopify_connect
from app.db.postgres import DbSessionDep
from app.db.repositories import users as user_repository
from app.features import shopify as shopify_service
from app.features.schemas import ShopifyConnectionStatusResponse

router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.get("/connect", dependencies=[Depends(require_shopify_connect)])
async def connect_shopify(
    shop_domain: Annotated[str, Query()],
    current_user: CurrentApplicationUserDep,
    session: DbSessionDep,
) -> RedirectResponse:
    user = await user_repository.get_user_by_application_id(session, current_user.id)
    if user is None:
        raise unauthorized()
    return RedirectResponse(await shopify_service.begin_connection(session, user=user, shop_domain=shop_domain))


@router.get("/status")
async def shopify_connection_status(
    current_user: CurrentApplicationUserDep,
    session: DbSessionDep,
) -> ShopifyConnectionStatusResponse:
    connection = None
    if current_user.tenant_id is not None:
        connection = await shopify_service.get_active_connection(
            session, tenant_id=current_user.tenant_id
        )
    if connection is None and current_user.role is not Role.STORE_OWNER:
        raise forbidden("Only a store owner can connect Shopify.")
    return ShopifyConnectionStatusResponse(
        connected=connection is not None,
        shop_domain=connection.shop_domain if connection is not None else None,
    )


@router.get("/callback")
async def shopify_callback(
    request: Request,
    shop: Annotated[str, Query()],
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    session: DbSessionDep,
) -> RedirectResponse:
    await shopify_service.complete_connection(
        session,
        state=state,
        callback_shop_domain=shop,
        code=code,
        callback_parameters=list(request.query_params.multi_items()),
    )
    return RedirectResponse(shopify_service.configuration("SHOPIFY_POST_CONNECT_REDIRECT_URI"))

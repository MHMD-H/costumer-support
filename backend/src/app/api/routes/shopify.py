"""Authenticated Shopify connection endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from app.core.auth import CurrentDashboardUserDep
from app.db.postgres import DbSessionDep
from app.db.repositories import users as user_repository
from app.features import shopify as shopify_service

router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.get("/connect")
async def connect_shopify(
    shop_domain: Annotated[str, Query()],
    current_user: CurrentDashboardUserDep,
    session: DbSessionDep,
) -> RedirectResponse:
    user = await user_repository.get_user_by_application_id(session, current_user.id)
    if user is None:
        from app.core.auth import unauthorized
        raise unauthorized()
    return RedirectResponse(await shopify_service.begin_connection(session, user=user, shop_domain=shop_domain))


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

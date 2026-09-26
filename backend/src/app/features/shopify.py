"""Server-side Shopify OAuth connection flow."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
from os import getenv
import re
from secrets import token_urlsafe
from urllib.parse import urlencode

from cryptography.fernet import Fernet, InvalidToken
import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import shopify as shopify_repository

SHOP_DOMAIN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")
OAUTH_STATE_TTL = timedelta(minutes=10)


def configuration(name: str) -> str:
    value = getenv(name, "")
    if not value:
        raise RuntimeError(f"{name} must be configured")
    return value


def normalize_shop_domain(shop_domain: str) -> str:
    normalized = shop_domain.strip().lower()
    if not SHOP_DOMAIN_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "bad_request", "message": "A valid Shopify store domain is required."},
        )
    return normalized


def state_hash(state: str) -> str:
    return sha256(state.encode("utf-8")).hexdigest()


def encrypt_access_token(access_token: str) -> str:
    try:
        return Fernet(configuration("SHOPIFY_TOKEN_ENCRYPTION_KEY").encode()).encrypt(
            access_token.encode()
        ).decode()
    except (ValueError, InvalidToken):
        raise RuntimeError("SHOPIFY_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from None


def build_authorization_url(shop_domain: str, state: str) -> str:
    query = urlencode(
        {
            "client_id": configuration("SHOPIFY_API_KEY"),
            "scope": configuration("SHOPIFY_SCOPES"),
            "redirect_uri": configuration("SHOPIFY_OAUTH_REDIRECT_URI"),
            "state": state,
        }
    )
    return f"https://{shop_domain}/admin/oauth/authorize?{query}"


def is_valid_callback_hmac(parameters: list[tuple[str, str]]) -> bool:
    received_hmac = next((value for key, value in parameters if key == "hmac"), None)
    if not received_hmac:
        return False
    message = urlencode(sorted((key, value) for key, value in parameters if key != "hmac"))
    expected_hmac = hmac.new(
        configuration("SHOPIFY_API_SECRET").encode(), message.encode(), sha256
    ).hexdigest()
    return hmac.compare_digest(expected_hmac, received_hmac)


async def begin_connection(
    session: AsyncSession, *, user: User, shop_domain: str
) -> str:
    state = token_urlsafe(32)
    await shopify_repository.create_oauth_state(
        session,
        user_id=user.id,
        state_hash=state_hash(state),
        expires_at=datetime.now(timezone.utc) + OAUTH_STATE_TTL,
    )
    return build_authorization_url(normalize_shop_domain(shop_domain), state)


async def exchange_code_for_access_token(shop_domain: str, code: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"https://{shop_domain}/admin/oauth/access_token",
            data={
                "client_id": configuration("SHOPIFY_API_KEY"),
                "client_secret": configuration("SHOPIFY_API_SECRET"),
                "code": code,
            },
        )
        response.raise_for_status()
    access_token = response.json().get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "bad_gateway", "message": "Shopify did not return a usable access token."},
        )
    return access_token


async def fetch_canonical_shop(shop_domain: str, access_token: str) -> tuple[str, str, str]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"https://{shop_domain}/admin/api/{getenv('SHOPIFY_API_VERSION', '2026-07')}/shop.json",
            headers={"X-Shopify-Access-Token": access_token},
        )
        response.raise_for_status()
    shop = response.json().get("shop", {})
    shop_id = shop.get("id")
    canonical_domain = shop.get("myshopify_domain")
    shop_name = shop.get("name")
    if not isinstance(shop_id, (str, int)) or not isinstance(canonical_domain, str) or not isinstance(shop_name, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "bad_gateway", "message": "Shopify did not return a usable store identity."},
        )
    return str(shop_id), normalize_shop_domain(canonical_domain), shop_name


async def complete_connection(
    session: AsyncSession,
    *,
    state: str,
    callback_shop_domain: str,
    code: str,
    callback_parameters: list[tuple[str, str]],
) -> None:
    if not is_valid_callback_hmac(callback_parameters):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "bad_request", "message": "Shopify callback is invalid."})

    oauth_state = await shopify_repository.consume_oauth_state(
        session, state_hash=state_hash(state), consumed_at=datetime.now(timezone.utc)
    )
    if oauth_state is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "bad_request", "message": "Shopify connection state is invalid or expired."})

    access_token = await exchange_code_for_access_token(normalize_shop_domain(callback_shop_domain), code)
    shop_id, canonical_domain, shop_name = await fetch_canonical_shop(
        normalize_shop_domain(callback_shop_domain), access_token
    )
    encrypted_token = encrypt_access_token(access_token)

    try:
        async with session.begin():
            user = await shopify_repository.get_user(session, oauth_state.user_id)
            if user is None or not user.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "bad_request", "message": "Shopify connection is no longer available."})
            existing_connection = await shopify_repository.get_connection_by_shop_id(session, shop_id)
            if existing_connection is not None and existing_connection.tenant_id != user.tenant_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "conflict", "message": "This Shopify store is already connected."})
            if user.tenant_id is None:
                tenant = await shopify_repository.create_tenant(
                    session, name=shop_name, shop_id=shop_id, shop_domain=canonical_domain
                )
                user.tenant_id = tenant.id
            else:
                connection = await shopify_repository.get_connection_by_tenant_id(session, user.tenant_id)
                if connection is not None:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "conflict", "message": "This user already has a connected Shopify store."})
                tenant = user.tenant
                if tenant is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "bad_request", "message": "Shopify connection is no longer available."})
                tenant.shop_id = shop_id
                tenant.shop_domain = canonical_domain
            await shopify_repository.create_connection(
                session,
                tenant_id=user.tenant_id,
                shop_id=shop_id,
                shop_domain=canonical_domain,
                access_token_encrypted=encrypted_token,
            )
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "conflict", "message": "This Shopify store is already connected."}) from None

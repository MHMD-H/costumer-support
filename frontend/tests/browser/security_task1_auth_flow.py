import base64
import json
import time

from playwright.sync_api import Page, Route, expect, sync_playwright


APP_URL = "http://localhost:3000"


def encoded(value: dict[str, object]) -> str:
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")


def test_token() -> str:
    return ".".join(
        (
            encoded({"alg": "none", "typ": "JWT"}),
            encoded({"aud": "authenticated", "exp": int(time.time()) + 3600, "sub": "11111111-1111-1111-1111-111111111111"}),
            "test-signature",
        )
    )


def auth_user() -> dict[str, object]:
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "aud": "authenticated",
        "role": "authenticated",
        "email": "owner@example.com",
        "email_confirmed_at": "2026-10-21T00:00:00Z",
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {},
        "created_at": "2026-10-21T00:00:00Z",
        "updated_at": "2026-10-21T00:00:00Z",
    }


def session_response() -> dict[str, object]:
    return {
        "access_token": test_token(),
        "refresh_token": "test-refresh-token",
        "token_type": "bearer",
        "expires_in": 3600,
        "expires_at": int(time.time()) + 3600,
        "user": auth_user(),
    }


def json_response(route: Route, body: object, status: int = 200) -> None:
    route.fulfill(status=status, content_type="application/json", body=json.dumps(body))


def mock_supabase(page: Page, *, valid_credentials: bool = True) -> None:
    def token(route: Route) -> None:
        if valid_credentials:
            json_response(route, session_response())
        else:
            json_response(route, {"error": "invalid_grant", "error_description": "Invalid login credentials"}, 400)

    page.route("**/auth/v1/token?grant_type=password", token)
    page.route("**/auth/v1/user", lambda route: json_response(route, auth_user()))
    page.route("**/auth/v1/recover*", lambda route: json_response(route, {}))
    page.route("**/auth/v1/logout*", lambda route: json_response(route, {}))


def fill_login(page: Page, email: str = "owner@example.com", password: str = "password123") -> None:
    page.get_by_label("Email address").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Log in").click()


def run() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
        )

        connected_context = browser.new_context()
        connected = connected_context.new_page()
        mock_supabase(connected)
        connected.route(
            "http://localhost:8000/auth/me",
            lambda route: json_response(route, {"role": "store_owner", "tenant_id": "22222222-2222-4222-8222-222222222222"}),
        )
        connected.goto(f"{APP_URL}/login", wait_until="networkidle")
        fill_login(connected)
        connected.wait_for_url(f"{APP_URL}/dashboard")
        expect(connected.get_by_text("Dashboard", exact=True)).to_be_visible()

        unlinked_context = browser.new_context()
        unlinked = unlinked_context.new_page()
        mock_supabase(unlinked)
        unlinked.route(
            "http://localhost:8000/auth/me",
            lambda route: json_response(route, {"role": "store_owner", "tenant_id": None}),
        )
        unlinked.goto(f"{APP_URL}/login", wait_until="networkidle")
        fill_login(unlinked)
        unlinked.wait_for_url(f"{APP_URL}/onboarding/connect-shopify")
        expect(unlinked.get_by_role("heading", name="Connect your Shopify store")).to_be_visible()

        refreshed = unlinked_context.new_page()
        mock_supabase(refreshed)
        refreshed.route(
            "http://localhost:8000/auth/me",
            lambda route: json_response(route, {"role": "store_owner", "tenant_id": None}),
        )
        refreshed.goto(f"{APP_URL}/onboarding/connect-shopify", wait_until="networkidle")
        expect(refreshed.get_by_role("heading", name="Connect your Shopify store")).to_be_visible()

        invalid_context = browser.new_context()
        invalid = invalid_context.new_page()
        mock_supabase(invalid, valid_credentials=False)
        invalid.goto(f"{APP_URL}/login", wait_until="networkidle")
        fill_login(invalid, password="wrong-password")
        expect(invalid.get_by_text("The email or password is incorrect.", exact=False)).to_be_visible()
        assert invalid.url == f"{APP_URL}/login"

        missing = invalid_context.new_page()
        missing.goto(f"{APP_URL}/login", wait_until="networkidle")
        missing.get_by_role("button", name="Log in").click()
        assert not missing.get_by_label("Email address").evaluate("element => element.validity.valid")

        signed_out_context = browser.new_context()
        signed_out = signed_out_context.new_page()
        signed_out.goto(f"{APP_URL}/onboarding/connect-shopify", wait_until="networkidle")
        signed_out.wait_for_url(f"{APP_URL}/login?session=expired")
        expect(signed_out.get_by_text("Your session has ended.", exact=False)).to_be_visible()

        recovery_context = browser.new_context()
        forgot = recovery_context.new_page()
        mock_supabase(forgot)
        forgot.goto(f"{APP_URL}/forgot-password", wait_until="networkidle")
        forgot.get_by_label("Email address").fill("owner@example.com")
        forgot.get_by_role("button", name="Send reset link").click()
        expect(forgot.get_by_text("If an account exists", exact=False)).to_be_visible()

        expired = browser.new_page()
        expired.goto(f"{APP_URL}/reset-password", wait_until="networkidle")
        expect(expired.get_by_text("invalid or expired", exact=False)).to_be_visible()

        browser.close()


if __name__ == "__main__":
    run()

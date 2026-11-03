"""Browser verification of the frontend onboarding handoffs with trusted services mocked."""

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright


FRONTEND = Path(__file__).resolve().parents[2]
ENV = dict(
    line.split("=", 1)
    for line in (FRONTEND / ".env.local").read_text(encoding="utf-8").splitlines()
    if line and not line.startswith("#") and "=" in line
)
SUPABASE_URL = ENV["NEXT_PUBLIC_SUPABASE_URL"].strip()
EMAIL = "owner@example.test"
SHOP = "demo-store.myshopify.com"
NOW = datetime.now(timezone.utc).isoformat()
USER = {
    "id": "00000000-0000-4000-8000-000000000001",
    "aud": "authenticated",
    "role": "authenticated",
    "email": EMAIL,
    "email_confirmed_at": NOW,
    "created_at": NOW,
    "updated_at": NOW,
    "app_metadata": {},
    "user_metadata": {},
}
SESSION = {
    "access_token": "browser-check-supabase-token",
    "refresh_token": "browser-check-refresh-token",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": USER,
}
connect_calls = []


class MockConnectBackend(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/shopify/connect":
            self.send_error(404)
            return
        connect_calls.append((parse_qs(parsed.query), self.headers.get("Authorization")))
        self.send_response(307)
        self.send_header("Location", f"https://{SHOP}/admin/oauth/authorize?state=server-owned")
        self.end_headers()

    def log_message(self, *_args):
        pass


def json_route(route, payload, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        headers={
            "access-control-allow-origin": "*",
            "access-control-allow-headers": "authorization, apikey, content-type, x-client-info",
            "access-control-allow-methods": "GET, POST, OPTIONS",
        },
        body=json.dumps(payload),
    )


def run():
    backend = ThreadingHTTPServer(("127.0.0.1", 8000), MockConnectBackend)
    thread = threading.Thread(target=backend.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
                headless=True,
            )
            context = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
            context.add_init_script(
                "if (location.pathname === '/onboarding/verify-email') "
                f"sessionStorage.setItem('pendingVerificationEmail', {json.dumps(EMAIL)});"
            )
            backend_state = {"connected": False, "checks": 0, "role": "store_owner"}

            def handle_supabase(route):
                path = urlparse(route.request.url).path
                if route.request.method == "OPTIONS":
                    json_route(route, {})
                elif path.endswith("/verify"):
                    json_route(route, SESSION)
                elif path.endswith("/user"):
                    json_route(route, USER)
                else:
                    json_route(route, SESSION)

            def handle_me(route):
                if route.request.method == "OPTIONS":
                    json_route(route, {})
                    return
                backend_state["checks"] += 1
                json_route(route, {
                    "id": USER["id"], "name": "Owner", "email": EMAIL,
                    "role": backend_state["role"],
                    "tenant_id": "00000000-0000-4000-8000-000000000002" if backend_state["connected"] else None,
                })

            context.route(f"{SUPABASE_URL}/auth/v1/**", handle_supabase)
            context.route("http://localhost:8000/auth/me", handle_me)
            context.route(
                f"https://{SHOP}/admin/oauth/authorize?**",
                lambda route: route.fulfill(status=200, content_type="text/html", body="<h1>Shopify approval simulated</h1>"),
            )
            page = context.new_page()

            page.goto("http://localhost:3000/onboarding/verify-email", wait_until="domcontentloaded")
            page.get_by_role("heading", name="Check your inbox").wait_for()
            page.locator(".verify-email__description").get_by_text(EMAIL).wait_for()
            page.screenshot(path=str(FRONTEND / ".task31-verify.png"), full_page=True)
            digits = page.locator(".verify-email__digit input")
            assert digits.count() == 6
            for index, digit in enumerate("123456"):
                digits.nth(index).fill(digit)
            page.get_by_role("button", name="Verify email").click()
            page.wait_for_url("**/onboarding/connect-shopify", timeout=15000)
            page.get_by_role("heading", name="Connect your Shopify store").wait_for()
            page.screenshot(path=str(FRONTEND / ".task31-connect.png"), full_page=True)

            page.get_by_role("link", name="Connect Shopify store").click()
            page.wait_for_url("**/onboarding/shopify-domain")
            page.get_by_role("heading", name="Enter your Shopify store address").wait_for()
            page.screenshot(path=str(FRONTEND / ".task31-domain.png"), full_page=True)
            page.get_by_label("Your store URL").fill("demo-store")
            page.get_by_role("button", name="Continue to Shopify").click()
            page.get_by_role("heading", name="Shopify approval simulated").wait_for(timeout=15000)
            assert connect_calls == [({"shop_domain": [SHOP]}, "Bearer browser-check-supabase-token")]

            # The backend callback is not simulated as successful until /auth/me changes.
            page.goto("http://localhost:3000/onboarding/shopify-connecting?state=forged", wait_until="domcontentloaded")
            page.get_by_role("heading", name="Connecting your store securely").wait_for()
            assert page.get_by_role("link", name="Continue to your workspace").count() == 0
            assert "forged" not in page.locator("body").inner_text()
            assert page.locator(".shopify-connecting__status-mark--active").evaluate(
                "element => getComputedStyle(element).animationName"
            ) == "none"
            page.screenshot(path=str(FRONTEND / ".task31-connecting.png"), full_page=True)
            backend_state["connected"] = True
            page.get_by_role("link", name="Continue to your workspace").wait_for(timeout=12000)
            page.get_by_role("link", name="Continue to your workspace").click()
            page.wait_for_url("**/onboarding/shopify-ready")
            page.get_by_role("heading", name="Your Shopify store is ready").wait_for()
            page.screenshot(path=str(FRONTEND / ".task31-ready.png"), full_page=True)
            assert "forged" not in page.locator("body").inner_text()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.get_by_role("link", name="Open your workspace").click()
            page.wait_for_url("**/dashboard")

            backend_state["role"] = "admin"
            page.goto("http://localhost:3000/onboarding/shopify-ready", wait_until="domcontentloaded")
            page.wait_for_url("**/access-denied")
            backend_state["role"] = "store_owner"
            backend_state["connected"] = False
            page.goto("http://localhost:3000/onboarding/shopify-ready", wait_until="domcontentloaded")
            page.wait_for_url("**/onboarding/shopify-connecting")
            backend_state["connected"] = True

            for width in (768, 390):
                page.set_viewport_size({"width": width, "height": 900})
                for route, heading in (
                    ("verify-email", "Check your inbox"),
                    ("connect-shopify", "Connect your Shopify store"),
                    ("shopify-domain", "Enter your Shopify store address"),
                    ("shopify-connecting", "Connecting your store securely"),
                    ("shopify-ready", "Your Shopify store is ready"),
                ):
                    backend_state["connected"] = route == "shopify-ready"
                    page.goto(f"http://localhost:3000/onboarding/{route}", wait_until="domcontentloaded")
                    page.get_by_role("heading", name=heading).wait_for()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, route)

            storage = page.evaluate("({local: {...localStorage}, session: {...sessionStorage}})")
            assert all("shopify" not in key.lower() and "oauth" not in key.lower() for key in (*storage["local"], *storage["session"]))
            signed_out = browser.new_page()
            signed_out.goto("http://localhost:3000/onboarding/shopify-ready", wait_until="domcontentloaded")
            signed_out.wait_for_url("**/login")
            signed_out.close()
            print("Task 31 browser journey passed: verification, connect redirect, pending, confirmed success, workspace, tablet/mobile overflow")
            print("Trusted /auth/me checks:", backend_state["checks"])
            context.close()
            browser.close()
            for name in ("verify", "connect", "domain", "connecting", "ready"):
                (FRONTEND / f".task31-{name}.png").unlink(missing_ok=True)
    finally:
        backend.shutdown()
        backend.server_close()


if __name__ == "__main__":
    run()

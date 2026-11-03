import { afterEach, describe, expect, it, vi } from "vitest";

const { redirect } = vi.hoisted(() => ({
  redirect: vi.fn((location: string) => { throw new Error(`REDIRECT:${location}`); }),
}));
vi.mock("next/navigation", () => ({ redirect }));

import { startShopifyConnection } from "../../src/app/onboarding/shopify-domain/actions";

describe("authenticated Shopify connection start", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("sends only the normalized domain and bearer token to the existing backend route, then relays its redirect", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, {
      status: 307,
      headers: { Location: "https://your-store.myshopify.com/admin/oauth/authorize?state=server-owned" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(startShopifyConnection("Your-Store", "supabase-token")).rejects.toThrow("REDIRECT:https://your-store.myshopify.com/admin/oauth/authorize?state=server-owned");

    const [url, options] = fetchMock.mock.calls[0];
    expect(url.toString()).toBe("http://localhost:8000/shopify/connect?shop_domain=your-store.myshopify.com");
    expect(options).toMatchObject({ method: "GET", redirect: "manual", cache: "no-store", headers: { Authorization: "Bearer supabase-token" } });
    expect(redirect).toHaveBeenCalledOnce();
  });

  it.each([
    [400, "invalid-domain"],
    [401, "unauthorized"],
    [403, "forbidden"],
    [409, "conflict"],
  ] as const)("returns a safe %s error", async (status, error) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status })));
    await expect(startShopifyConnection("your-store", "supabase-token")).resolves.toEqual({ error });
    expect(redirect).not.toHaveBeenCalled();
  });

  it("rejects missing auth, invalid domains, and unexpected redirect locations", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(startShopifyConnection("example.com/path", "supabase-token")).resolves.toEqual({ error: "invalid-domain" });
    await expect(startShopifyConnection("your-store", "")).resolves.toEqual({ error: "unauthorized" });
    expect(fetchMock).not.toHaveBeenCalled();

    fetchMock.mockResolvedValue(new Response(null, {
      status: 307,
      headers: { Location: "https://unrelated.example/admin/oauth/authorize?state=unknown" },
    }));
    await expect(startShopifyConnection("your-store", "supabase-token")).resolves.toEqual({ error: "unavailable" });
    expect(redirect).not.toHaveBeenCalled();
  });
});

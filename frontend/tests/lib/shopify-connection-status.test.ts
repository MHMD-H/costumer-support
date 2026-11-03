import { afterEach, describe, expect, it, vi } from "vitest";

const { getAccessToken } = vi.hoisted(() => ({ getAccessToken: vi.fn() }));
vi.mock("../../src/lib/auth", () => ({ getAccessToken }));

import { pollShopifyConnection, readShopifyConnectionStatus } from "../../src/lib/shopify-connection-status";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("trusted Shopify connection status", () => {
  it("uses the existing current-user route and treats an unlinked owner as pending", async () => {
    getAccessToken.mockResolvedValue("session-token");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ role: "store_owner", tenant_id: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    expect(await readShopifyConnectionStatus()).toBe("pending");
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/auth/me", expect.objectContaining({
      method: "GET", cache: "no-store", headers: { Authorization: "Bearer session-token" },
    }));
  });

  it("resolves only from a linked store owner returned by the backend", async () => {
    getAccessToken.mockResolvedValue("session-token");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ role: "store_owner", tenant_id: "backend-tenant-id" }), { status: 200 })));
    expect(await readShopifyConnectionStatus()).toBe("connected");
  });

  it("handles expired sessions, non-owner users, and callback failure without assuming success", async () => {
    getAccessToken.mockResolvedValueOnce(null).mockResolvedValue("session-token");
    expect(await readShopifyConnectionStatus()).toBe("signed-out");
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ role: "admin", tenant_id: "tenant" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 400 }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await readShopifyConnectionStatus()).toBe("signed-out");
    expect(await readShopifyConnectionStatus()).toBe("forbidden");
    expect(await readShopifyConnectionStatus()).toBe("unavailable");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("stops immediately when backend state resolves", async () => {
    const onStatus = vi.fn();
    await pollShopifyConnection(new AbortController().signal, onStatus, vi.fn().mockResolvedValue("connected"));
    expect(onStatus).toHaveBeenCalledExactlyOnceWith("connected");
  });

  it("times out after bounded pending checks", async () => {
    vi.useFakeTimers();
    const onStatus = vi.fn();
    const readStatus = vi.fn().mockResolvedValue("pending");
    const run = pollShopifyConnection(new AbortController().signal, onStatus, readStatus);
    await vi.runAllTimersAsync();
    await run;
    expect(readStatus).toHaveBeenCalledTimes(7);
    expect(onStatus).toHaveBeenLastCalledWith("timeout");
  });

  it("cancels scheduled and in-flight checks without reporting completion", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const onStatus = vi.fn();
    const readStatus = vi.fn().mockResolvedValue("pending");
    const run = pollShopifyConnection(controller.signal, onStatus, readStatus);
    await Promise.resolve();
    controller.abort();
    await run;
    await vi.runAllTimersAsync();
    expect(readStatus).toHaveBeenCalledTimes(1);
    expect(onStatus).not.toHaveBeenCalledWith("connected");
    expect(onStatus).not.toHaveBeenCalledWith("timeout");
  });
});

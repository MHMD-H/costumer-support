import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));

import ShopifyReadyPage from "../../src/app/onboarding/shopify-ready/page";
import { ReadyContent } from "../../src/components/onboarding/shopify-store-ready";

describe("Shopify ready route", () => {
  it("keeps direct navigation neutral until trusted current-user state is checked", () => {
    const html = renderToStaticMarkup(<ShopifyReadyPage />);
    expect(html).toContain("Checking your store connection");
    expect(html).not.toContain("Your Shopify store is ready");
    expect(html).not.toContain("Connection complete");
    expect(html).not.toContain("Open your workspace");
    expect(html).not.toContain("shop_id");
    expect(html).not.toContain("access_token");
  });

  it("provides an accessible completed state and the existing workspace destination", () => {
    const html = renderToStaticMarkup(<ReadyContent />);
    expect(html).toContain("Your Shopify store is ready");
    expect(html).toContain('role="status"');
    expect(html).toContain("Store verified");
    expect(html).toContain("Data access configured");
    expect(html).toContain("Workspace created");
    expect(html).toContain('href="/dashboard"');
    expect(html).not.toContain('href="/settings"');
    expect(html).not.toContain("shop_id");
    expect(html).not.toContain("access_token");
  });
});

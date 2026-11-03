import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ShopifyConnectingPage from "../../src/app/onboarding/shopify-connecting/page";

describe("Shopify connecting page", () => {
  it("renders the approved progress shell without exposing OAuth values or claiming success by default", () => {
    const html = renderToStaticMarkup(<ShopifyConnectingPage />);
    expect(html).toContain("Connecting your store securely");
    expect(html).toContain("Verifying store ownership");
    expect(html).toContain("Securing data access");
    expect(html).toContain("Preparing your workspace");
    expect(html).toContain('aria-current="step"');
    expect(html).not.toContain("Connection confirmed");
    expect(html).not.toContain("oauth_state");
    expect(html).not.toContain("access_token");
  });
});

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ConnectShopifyPage from "../../src/app/onboarding/connect-shopify/page";
import ShopifyDomainPage from "../../src/app/onboarding/shopify-domain/page";
import { ConnectShopifyStore } from "../../src/components/onboarding/connect-shopify-store";
import { OnboardingShell } from "../../src/components/onboarding/onboarding-shell";
import { ShopifyDomainEntry } from "../../src/components/onboarding/shopify-domain-entry";

describe("Shopify connection onboarding screens", () => {
  it("shows ownership and data-access assurances with the connect-store progress step", () => {
    const html = renderToStaticMarkup(<OnboardingShell referenceId="connectShopifyStore"><ConnectShopifyStore /></OnboardingShell>);
    expect(html).toContain("Connect your Shopify store");
    expect(html).toContain("Verify your store ownership");
    expect(html).toContain("Keep your store data private");
    expect(html).toContain("Choose what your team can access");
    expect(html).toContain('href="/onboarding/shopify-domain"');
    expect(html).toContain('aria-current="step"');
  });

  it("renders a labeled split-domain form with inline guidance", () => {
    const html = renderToStaticMarkup(<OnboardingShell referenceId="enterShopifyDomain"><ShopifyDomainEntry /></OnboardingShell>);
    expect(html).toContain("Enter your Shopify store address");
    expect(html).toContain('for="shopify-store-name"');
    expect(html).toContain("https://");
    expect(html).toContain(".myshopify.com");
    expect(html).toContain("Continue to Shopify");
    expect(html).toContain("I don’t know my store address");
  });

  it("checks trusted account state before rendering direct onboarding routes", () => {
    expect(renderToStaticMarkup(<ConnectShopifyPage />)).toContain("Checking your account");
    expect(renderToStaticMarkup(<ShopifyDomainPage />)).toContain("Checking your account");
  });
});

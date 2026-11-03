import { describe, expect, it } from "vitest";

import { normalizeShopifyDomain } from "../../src/lib/shopify-domain";

describe("Shopify store domain normalization", () => {
  it.each([
    ["Your-Store", "your-store.myshopify.com"],
    [" your-store.myshopify.com ", "your-store.myshopify.com"],
    ["https://Your-Store.myshopify.com", "your-store.myshopify.com"],
  ])("normalizes %s to %s", (input, expected) => {
    expect(normalizeShopifyDomain(input)).toBe(expected);
  });

  it.each([
    "", "https://example.com", "http://your-store.myshopify.com",
    "your-store.myshopify.com/path", "your-store.myshopify.com.evil.test",
    "your-store.example.com", "-bad", "bad-", "bad name",
  ])("rejects unsafe or malformed input %s", (input) => {
    expect(normalizeShopifyDomain(input)).toBeNull();
  });
});

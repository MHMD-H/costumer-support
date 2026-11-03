const SHOP_SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

export function normalizeShopifyDomain(input: string): string | null {
  let value = input.trim().toLowerCase();

  if (value.startsWith("https://")) {
    value = value.slice("https://".length);
  }

  if (value.endsWith(".myshopify.com")) {
    value = value.slice(0, -".myshopify.com".length);
  }

  return SHOP_SLUG_PATTERN.test(value) ? `${value}.myshopify.com` : null;
}

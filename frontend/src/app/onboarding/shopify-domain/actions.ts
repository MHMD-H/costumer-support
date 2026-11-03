"use server";

import { redirect } from "next/navigation";

import { API_BASE_URL } from "../../../lib/api";
import { normalizeShopifyDomain } from "../../../lib/shopify-domain";

export type ShopifyConnectError = "invalid-domain" | "unauthorized" | "forbidden" | "conflict" | "unavailable";

export async function startShopifyConnection(
  domainInput: string,
  accessToken: string,
): Promise<{ error: ShopifyConnectError }> {
  const shopDomain = normalizeShopifyDomain(domainInput);
  if (!shopDomain) return { error: "invalid-domain" };
  if (!accessToken) return { error: "unauthorized" };

  let response: Response;
  try {
    const connectUrl = new URL("/shopify/connect", API_BASE_URL);
    connectUrl.searchParams.set("shop_domain", shopDomain);
    response = await fetch(connectUrl, {
      method: "GET",
      headers: { Authorization: `Bearer ${accessToken}` },
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return { error: "unavailable" };
  }

  if (response.status === 400) return { error: "invalid-domain" };
  if (response.status === 401) return { error: "unauthorized" };
  if (response.status === 403) return { error: "forbidden" };
  if (response.status === 409) return { error: "conflict" };

  const location = response.headers.get("location");
  if (![301, 302, 303, 307, 308].includes(response.status) || !location) {
    return { error: "unavailable" };
  }

  let authorizationUrl: URL;
  try {
    authorizationUrl = new URL(location);
  } catch {
    return { error: "unavailable" };
  }
  if (
    authorizationUrl.protocol !== "https:" ||
    authorizationUrl.hostname !== shopDomain ||
    authorizationUrl.pathname !== "/admin/oauth/authorize"
  ) {
    return { error: "unavailable" };
  }

  redirect(location);
}

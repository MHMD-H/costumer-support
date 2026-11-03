import type { ConnectionStatus } from "./shopify-connection-status";

export type AuthDestination =
  | "/access-denied"
  | "/dashboard"
  | "/login?session=expired"
  | "/onboarding/connect-shopify";

export function destinationForConnectionStatus(
  status: ConnectionStatus,
): AuthDestination | null {
  if (status === "connected") return "/dashboard";
  if (status === "pending") return "/onboarding/connect-shopify";
  if (status === "signed-out") return "/login?session=expired";
  if (status === "forbidden") return "/access-denied";
  return null;
}

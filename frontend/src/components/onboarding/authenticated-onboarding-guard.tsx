"use client";

import { type ReactNode, useEffect, useState } from "react";

import { destinationForConnectionStatus } from "../../lib/auth-routing";
import { readShopifyConnectionStatus, type ConnectionStatus } from "../../lib/shopify-connection-status";
import { ContourBackground } from "../ui/contour-background";

export function AuthenticatedOnboardingGuard({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus | "checking">("checking");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void readShopifyConnectionStatus(controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      if (result === "pending") {
        setStatus(result);
        return;
      }

      const destination = destinationForConnectionStatus(result);
      if (destination) {
        window.location.replace(destination);
        return;
      }
      setStatus("unavailable");
    }).catch(() => {
      if (!controller.signal.aborted) setStatus("unavailable");
    });
    return () => controller.abort();
  }, [retryKey]);

  if (status === "pending") return children;

  return (
    <div className="contour-shell shopify-ready__guard">
      <ContourBackground />
      <main aria-live="polite" className="shopify-ready__guard-content">
        <h1>{status === "unavailable" ? "We couldn’t confirm your account" : "Checking your account"}</h1>
        <p>{status === "unavailable" ? "Your signed-in account must be confirmed before Shopify onboarding can continue." : "Checking your trusted workspace status…"}</p>
        {status === "unavailable" ? (
          <button className="primary-button" onClick={() => { setStatus("checking"); setRetryKey((key) => key + 1); }} type="button">
            Try again
          </button>
        ) : null}
      </main>
    </div>
  );
}

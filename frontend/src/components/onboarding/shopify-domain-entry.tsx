"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { startShopifyConnection, type ShopifyConnectError } from "../../app/onboarding/shopify-domain/actions";
import { getAccessToken } from "../../lib/auth";
import { normalizeShopifyDomain } from "../../lib/shopify-domain";
import { OnboardingArrowIcon } from "./shopify-icons";

const ERROR_MESSAGES: Record<ShopifyConnectError, string> = {
  "invalid-domain": "Enter your store’s myshopify.com address without a path or other URL.",
  unauthorized: "Your session has ended. Sign in again before connecting your store.",
  forbidden: "Only an active store owner can connect a Shopify store. Ask your store owner for access.",
  conflict: "This store is already connected. Check your workspace or contact your store owner.",
  unavailable: "We couldn’t start the Shopify connection. Please try again.",
};

export function ShopifyDomainEntry() {
  const [storeAddress, setStoreAddress] = useState("");
  const [errorCode, setErrorCode] = useState<ShopifyConnectError | null>(null);
  const [busy, setBusy] = useState(false);

  function validate() {
    if (!storeAddress.trim()) {
      setErrorCode("invalid-domain");
      return null;
    }
    const domain = normalizeShopifyDomain(storeAddress);
    if (!domain) {
      setErrorCode("invalid-domain");
      return null;
    }
    setStoreAddress(domain.slice(0, -".myshopify.com".length));
    setErrorCode(null);
    return domain;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const domain = validate();
    if (!domain) return;

    setBusy(true);
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) {
        setErrorCode("unauthorized");
        return;
      }
      const result = await startShopifyConnection(domain, accessToken);
      setErrorCode(result.error);
    } catch {
      setErrorCode("unavailable");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="shopify-domain-title" className="shopify-domain onboarding-stage">
      <div className="onboarding-stage__intro">
        <p className="onboarding-stage__eyebrow">Find your store</p>
        <h1 id="shopify-domain-title">Enter your Shopify store address</h1>
        <p>We’ll take you to Shopify to securely approve the connection.</p>
      </div>

      <div className="shopify-domain__card onboarding-stage__card">
        <form noValidate onSubmit={handleSubmit}>
          <label className="shopify-domain__label" htmlFor="shopify-store-name">Your store URL</label>
          <div className={`shopify-domain__split${errorCode === "invalid-domain" ? " shopify-domain__split--invalid" : ""}`}>
            <span aria-hidden="true" className="shopify-domain__prefix">https://</span>
            <input
              aria-describedby={`shopify-domain-help${errorCode ? " shopify-domain-error" : ""}`}
              aria-invalid={errorCode === "invalid-domain"}
              autoCapitalize="none"
              autoComplete="off"
              id="shopify-store-name"
              maxLength={100}
              onBlur={() => { if (storeAddress) validate(); }}
              onChange={(event) => { setStoreAddress(event.target.value); setErrorCode(null); }}
              placeholder="your-store"
              spellCheck={false}
              type="text"
              value={storeAddress}
            />
            <span aria-hidden="true" className="shopify-domain__suffix">.myshopify.com</span>
          </div>
          <p className="shopify-domain__help" id="shopify-domain-help">Enter the name before .myshopify.com in your store’s assigned address.</p>
          {errorCode ? (
            <p className="shopify-domain__error" id="shopify-domain-error" role="alert">
              {ERROR_MESSAGES[errorCode]}{" "}
              {errorCode === "unauthorized" ? <Link href="/login">Go to sign in</Link> : null}
            </p>
          ) : null}

          <button aria-busy={busy} className="primary-button shopify-domain__submit" disabled={busy} type="submit">
            {busy ? "Connecting…" : "Continue to Shopify"}
            {!busy ? <OnboardingArrowIcon /> : null}
          </button>
        </form>

        <details className="shopify-domain__address-help">
          <summary>I don’t know my store address</summary>
          <p>Open your Shopify admin and check the address in your browser. Use the name before <strong>.myshopify.com</strong>.</p>
        </details>
      </div>
    </section>
  );
}

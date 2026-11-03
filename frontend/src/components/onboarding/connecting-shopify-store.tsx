"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { pollShopifyConnection, type ConnectionStatus } from "../../lib/shopify-connection-status";
import { ShopifyBagIcon } from "./shopify-icons";

type ViewStatus = ConnectionStatus | "checking" | "timeout";

function PlatformIcon() {
  return (
    <svg aria-hidden="true" className="shopify-connecting__platform" viewBox="0 0 96 96" fill="none">
      <circle cx="48" cy="48" r="48" fill="#e8f6ef" />
      <path d="M27 65 44 32c1.7-3.3 6.3-3.3 8 0l17 33M36 49h24" stroke="#008060" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="48" cy="65" r="5" fill="#008060" />
    </svg>
  );
}

function StatusIcon({ complete, active }: { complete: boolean; active: boolean }) {
  if (complete) {
    return <svg aria-hidden="true" className="shopify-connecting__check" viewBox="0 0 28 28" fill="none"><circle cx="14" cy="14" r="14" fill="#008060" /><path d="m7.5 14 4.3 4.2 8.7-8.5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
  }
  return <span aria-hidden="true" className={`shopify-connecting__status-mark${active ? " shopify-connecting__status-mark--active" : ""}`} />;
}

const MESSAGES: Partial<Record<ViewStatus, string>> = {
  "signed-out": "Your session has ended. Sign in again to check your store connection.",
  forbidden: "Only the store owner can finish connecting this store. Ask your store owner for access.",
  unavailable: "We couldn’t check your connection right now. Please try again.",
  timeout: "This is taking longer than expected. You can check again in a moment.",
};

export function ConnectingShopifyStore() {
  const [status, setStatus] = useState<ViewStatus>("checking");
  const controller = useRef<AbortController | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const current = new AbortController();
    controller.current = current;
    void pollShopifyConnection(current.signal, setStatus);
    return () => current.abort();
  }, [retryKey]);

  const connected = status === "connected";
  const active = status === "checking" || status === "pending";

  function retry() {
    controller.current?.abort();
    setStatus("checking");
    setRetryKey((key) => key + 1);
  }

  function cancel() {
    controller.current?.abort();
    window.location.assign("/onboarding/connect-shopify");
  }

  return (
    <section aria-labelledby="shopify-connecting-title" className="shopify-connecting onboarding-stage">
      <div className="onboarding-stage__intro">
        <p className="onboarding-stage__eyebrow">Finalizing your connection</p>
        <h1 id="shopify-connecting-title">Connecting your store securely</h1>
        <p>{connected ? "Your workspace is ready for the next step." : "We’re checking your store connection and preparing your workspace."}</p>
      </div>

      <div className="shopify-connecting__card onboarding-stage__card">
        <div aria-label="AI Commerce Copilot connecting to Shopify" className="shopify-connecting__visual" role="img">
          <PlatformIcon />
          <span aria-hidden="true" className="shopify-connecting__bridge"><i /><i /><i /></span>
          <ShopifyBagIcon />
        </div>
        <h2>{connected ? "Connection confirmed" : active ? "Checking with Shopify…" : "Connection needs attention"}</h2>
        <p className="shopify-connecting__summary">{connected ? "Your store is linked to your workspace." : active ? "This can take a little while. You can leave this page open." : MESSAGES[status]}</p>

        <ol aria-live="polite" className="shopify-connecting__statuses">
          <li><StatusIcon active={false} complete={connected} /><span>Verifying store ownership</span></li>
          <li><StatusIcon active={false} complete={connected} /><span>Securing data access</span></li>
          <li><StatusIcon active={active} complete={connected} /><span>Preparing your workspace</span></li>
        </ol>

        {active ? <p aria-live="polite" className="shopify-connecting__note">Checking your trusted account status securely…</p> : null}
        {connected ? <Link className="primary-button shopify-connecting__action" href="/onboarding/shopify-ready">Continue to your workspace <span aria-hidden="true">→</span></Link> : null}
        {status === "signed-out" ? <Link className="primary-button shopify-connecting__action" href="/login">Go to sign in <span aria-hidden="true">→</span></Link> : null}
        {status === "timeout" || status === "unavailable" ? <button className="primary-button shopify-connecting__action" onClick={retry} type="button">Check again <span aria-hidden="true">→</span></button> : null}
        {!connected ? <button className="shopify-connecting__cancel" onClick={cancel} type="button">{active ? "Cancel connection" : "Back to Shopify connection"}</button> : null}
      </div>
    </section>
  );
}

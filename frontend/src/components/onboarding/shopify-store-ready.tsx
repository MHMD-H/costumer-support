"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { readShopifyConnectionStatus, type ConnectionStatus } from "../../lib/shopify-connection-status";
import { OnboardingArrowIcon } from "./shopify-icons";
import { OnboardingShell } from "./onboarding-shell";
import { VerificationLogout } from "./verification-logout";
import { ContourBackground } from "../ui/contour-background";

const COMPLETED_STATUSES = ["Store verified", "Data access configured", "Workspace created"] as const;

function SuccessCheck({ large = false }: { large?: boolean }) {
  return (
    <svg aria-hidden="true" className={large ? "shopify-ready__large-check" : "shopify-ready__check"} fill="none" viewBox="0 0 96 96">
      {large ? <circle cx="48" cy="48" r="48" fill="#e8f6ef" /> : <circle cx="48" cy="48" r="46" fill="#008060" />}
      <path d="m27 48 14 14 29-31" stroke={large ? "#008060" : "#fff"} strokeLinecap="round" strokeLinejoin="round" strokeWidth={large ? "6" : "8"} />
    </svg>
  );
}

export function ReadyContent() {
  return (
    <section aria-labelledby="shopify-ready-title" className="shopify-ready onboarding-stage">
      <div className="onboarding-stage__intro">
        <p className="onboarding-stage__eyebrow">Your store is connected</p>
        <h1 id="shopify-ready-title">Your Shopify store is ready</h1>
        <p>Your store is linked securely. Your workspace is ready to bring<br className="onboarding-stage__desktop-break" /> products, orders, sales, and knowledge together.</p>
      </div>

      <div className="shopify-ready__card onboarding-stage__card">
        <p className="sr-only" role="status">Shopify connection complete. Your workspace is ready.</p>
        <SuccessCheck large />
        <h2>Connection complete</h2>
        <ul className="shopify-ready__statuses">
          {COMPLETED_STATUSES.map((status) => <li key={status}><SuccessCheck /><span>{status}</span></li>)}
        </ul>
        <p className="shopify-ready__sync-note">Your store data will appear in your workspace as it syncs.</p>
        <Link className="primary-button shopify-ready__open" href="/dashboard">
          Open your workspace <OnboardingArrowIcon />
        </Link>
        <p className="shopify-ready__settings-note">You can manage your connection later in settings.</p>
      </div>
    </section>
  );
}

export function ShopifyStoreReady() {
  const router = useRouter();
  const [status, setStatus] = useState<ConnectionStatus | "checking">("checking");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    function recheckOnRestore(event: PageTransitionEvent) {
      if (event.persisted) {
        setStatus("checking");
        setRetryKey((key) => key + 1);
      }
    }
    window.addEventListener("pageshow", recheckOnRestore);
    return () => window.removeEventListener("pageshow", recheckOnRestore);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void readShopifyConnectionStatus(controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      if (result === "pending") router.replace("/onboarding/shopify-connecting");
      else if (result === "signed-out") router.replace("/login");
      else if (result === "forbidden") router.replace("/access-denied");
      else setStatus(result);
    }).catch(() => {
      if (!controller.signal.aborted) setStatus("unavailable");
    });
    return () => controller.abort();
  }, [router, retryKey]);

  if (status === "connected") {
    return <OnboardingShell allStepsComplete logOutAction={<VerificationLogout />} referenceId="shopifyStoreReady"><ReadyContent /></OnboardingShell>;
  }

  return (
    <div className="contour-shell shopify-ready__guard">
      <ContourBackground />
      <main aria-live="polite" className="shopify-ready__guard-content">
        <h1>{status === "unavailable" ? "We couldn’t confirm your connection" : "Checking your store connection"}</h1>
        <p>{status === "unavailable" ? "Please try again. Your store status must be confirmed before this page opens." : "Checking your workspace with your account…"}</p>
        {status === "unavailable" ? <button className="primary-button" onClick={() => { setStatus("checking"); setRetryKey((key) => key + 1); }} type="button">Check again <OnboardingArrowIcon /></button> : null}
      </main>
    </div>
  );
}

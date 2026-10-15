"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { signUp } from "../../lib/auth";

import { BrandMark } from "../ui/brand-mark";
import { ContourBackground } from "../ui/contour-background";
import { FieldHelp } from "../ui/primitives";

type AuthView = "login" | "register" | "forgot" | "expired" | "denied";

const VIEW_CONTENT: Record<AuthView, { title: string; description: string }> = {
  login: {
    title: "Log in",
    description: "Welcome back. Sign in to access your store workspace.",
  },
  register: {
    title: "Create an account",
    description: "Use the email address associated with your Shopify store.",
  },
  forgot: {
    title: "Forgot password?",
    description: "Enter your email address and we’ll help you get back into your dashboard.",
  },
  expired: {
    title: "This reset link has expired",
    description: "For your security, password reset links can only be used for a limited time.",
  },
  denied: {
    title: "Dashboard access unavailable",
    description: "Your account doesn’t have permission to open this store dashboard. Contact your store administrator for help.",
  },
};

function ArrowIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
      <path d="M3.5 10h12m-5-5 5 5-5 5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
    </svg>
  );
}

function TrustIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
      <path d="M10 2.2 16 4.5v4.8c0 3.8-2.4 6.8-6 8.5-3.6-1.7-6-4.7-6-8.5V4.5l6-2.3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="m7.2 9.8 1.8 1.8 3.8-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
      <circle cx="10" cy="10" r="7.25" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10 9v4m0-6h.01" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function AuthExperience({ view }: { view: AuthView }) {
  const [isPreparing, setIsPreparing] = useState(false);
  const [notice, setNotice] = useState("");
  const content = VIEW_CONTENT[view];
  const hasForm = view === "login" || view === "register" || view === "forgot";

  useEffect(() => {
    if (view === "login" && new URLSearchParams(window.location.search).get("verification") === "expired") {
      setNotice("Your verification session is missing or expired. Sign in and request a new code to continue.");
    }
  }, [view]);

  async function handlePreviewSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsPreparing(true);
    setNotice("");

    if (view === "register") {
      const form = new FormData(event.currentTarget);
      const email = String(form.get("email") ?? "").trim().toLowerCase();
      const password = String(form.get("password") ?? "");
      try {
        await signUp(email, password);
        sessionStorage.setItem("pendingVerificationEmail", email);
        window.location.assign("/onboarding/verify-email");
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "We couldn't create your account. Please try again.");
      } finally {
        setIsPreparing(false);
      }
      return;
    }

    window.setTimeout(() => {
      setIsPreparing(false);
      setNotice(view === "login"
        ? "Preview complete. Your details were not sent and you are not signed in."
        : "Preview complete. No reset email was sent.");
    }, 300);
  }

  return (
    <div className="contour-shell auth-shell">
      <ContourBackground />
      <header className="auth-header">
        <BrandMark />
      </header>
      <main className="auth-main">
        <div className="auth-intro">
          <p className="auth-intro__positioning">Turn your store data into clearer, faster decisions.</p>
          {view === "login" ? <p className="auth-intro__description">Your AI workspace brings sales, orders, products, and team knowledge together — so you can spend less time searching and more time growing.</p> : null}
          {view === "login" ? (
            <p className="auth-intro__trust auth-intro__trust--verified"><TrustIcon /><span>Your business data stays private to your team.</span></p>
          ) : <p className="auth-intro__trust">Your business data stays private to your team.</p>}
        </div>

        <section aria-labelledby="auth-title" className="auth-card">
          <h1 id="auth-title">{content.title}</h1>
          <p className="auth-card__description">{content.description}</p>

          {view === "login" ? (
            <p className="auth-info-note" role="note">
              <span className="auth-info-note__icon"><InfoIcon /></span>
              <span>Use the email address associated with your Shopify store.</span>
            </p>
          ) : null}

          {view === "expired" ? (
            <div className="auth-notice auth-notice--error" role="alert">
              <p>This password reset link is invalid or expired. Request a new link to continue.</p>
            </div>
          ) : null}

          {view === "denied" ? (
            <div className="auth-notice auth-notice--error" role="alert">
              <p>If you think you should have access, ask your store administrator to check your team permissions.</p>
            </div>
          ) : null}

          {hasForm ? (
            <form className="auth-form" onSubmit={handlePreviewSubmit}>
              <div className="field-group">
                <label className="field-label" htmlFor="auth-email">Email address</label>
                <input
                  autoComplete="email"
                  className="field-control"
                  id="auth-email"
                  name="email"
                  required
                  type="email"
                />
                {view !== "forgot" ? <FieldHelp>For dashboard users on your store team.</FieldHelp> : null}
              </div>

              {view === "login" || view === "register" ? (
                <div className="field-group">
                  <label className="field-label" htmlFor="auth-password">Password</label>
                  <input
                    autoComplete={view === "login" ? "current-password" : "new-password"}
                    className="field-control"
                    id="auth-password"
                    minLength={8}
                    name="password"
                    required
                    type="password"
                  />
                  {view === "register" ? <FieldHelp>Use at least 8 characters.</FieldHelp> : null}
                </div>
              ) : null}

              {view === "login" ? (
                <div className="auth-form__forgot">
                  <Link className="text-link" href="/forgot-password">Forgot password?</Link>
                </div>
              ) : null}

              {notice ? (
                <p aria-live="polite" className={`auth-form__notice${view === "login" && notice.includes("verification session") ? " auth-form__notice--error" : ""}`} role="status">{notice}</p>
              ) : null}

              <button aria-busy={isPreparing} className="primary-button auth-submit" disabled={isPreparing} type="submit">
                <span>{isPreparing ? view === "register" ? "Creating account…" : "Preparing preview…" : view === "login" ? "Log in" : view === "register" ? "Create account" : "Send reset link"}</span>
                {!isPreparing && view === "login" ? <ArrowIcon /> : null}
              </button>
            </form>
          ) : null}

          <nav aria-label="Account options" className="auth-card__footer">
            {view === "login" ? (
              <>
                <p>New to AI Commerce Copilot?</p>
                <Link className="text-link" href="/register">Create an account</Link>
              </>
            ) : view === "register" ? (
              <p>Already have an account? <Link className="text-link" href="/login">Log in</Link></p>
            ) : view === "forgot" || view === "expired" ? (
              <Link className="auth-back-link" href="/login">Back to Log in</Link>
            ) : (
              <Link className="auth-back-link" href="/login">Return to Log in</Link>
            )}
            {view === "expired" ? <Link className="primary-button auth-secondary-action" href="/forgot-password">Request a new link</Link> : null}
          </nav>
        </section>
        <p className="auth-audience">AI Commerce Copilot accounts are for store teams. Shopify shoppers use the storefront chat without logging in.</p>
      </main>
    </div>
  );
}

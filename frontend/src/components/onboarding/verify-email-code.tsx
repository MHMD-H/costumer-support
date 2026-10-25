"use client";

import { type ClipboardEvent, type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { resendSignUpCode, verifySignUpCode } from "../../lib/auth";

const CODE_LENGTH = 6;
const RESEND_COOLDOWN_SECONDS = 30;

function ArrowIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
      <path d="M3.5 10h12m-5-5 5 5-5 5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
    </svg>
  );
}

export function VerifyEmailCode() {
  const inputs = useRef<Array<HTMLInputElement | null>>([]);
  const [email, setEmail] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    const pendingEmail = sessionStorage.getItem("pendingVerificationEmail");
    if (!pendingEmail) {
      window.location.replace("/login?verification=expired");
      return;
    }
    setEmail(pendingEmail);
  }, []);

  useEffect(() => {
    if (cooldown === 0) return;
    const timer = window.setTimeout(() => setCooldown((remaining) => remaining - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  function handleChange(index: number, value: string) {
    const digit = value.replace(/\D/g, "").slice(-1);
    if (inputs.current[index]) inputs.current[index]!.value = digit;
    setError("");
    if (digit && index < CODE_LENGTH - 1) inputs.current[index + 1]?.focus();
  }

  function handleKeyDown(index: number, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Backspace" && !event.currentTarget.value && index > 0) {
      inputs.current[index - 1]?.focus();
    } else if (event.key === "ArrowLeft" && index > 0) {
      event.preventDefault();
      inputs.current[index - 1]?.focus();
    } else if (event.key === "ArrowRight" && index < CODE_LENGTH - 1) {
      event.preventDefault();
      inputs.current[index + 1]?.focus();
    }
  }

  function handlePaste(event: ClipboardEvent<HTMLInputElement>) {
    const digits = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, CODE_LENGTH);
    if (!digits) return;
    event.preventDefault();
    inputs.current.forEach((input, index) => {
      if (input) input.value = digits[index] ?? "";
    });
    inputs.current[Math.min(digits.length, CODE_LENGTH - 1)]?.focus();
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = inputs.current.map((input) => input?.value ?? "").join("");
    if (token.length !== CODE_LENGTH) {
      setError("Enter all six digits from your verification email.");
      inputs.current.find((input) => !input?.value)?.focus();
      return;
    }
    setIsVerifying(true);
    setError("");
    try {
      await verifySignUpCode(email, token);
      sessionStorage.removeItem("pendingVerificationEmail");
      window.location.assign("/onboarding/connect-shopify");
    } catch (verificationError) {
      const message = verificationError instanceof Error ? verificationError.message.toLowerCase() : "";
      if (message.includes("session") || message.includes("refresh token")) {
        sessionStorage.removeItem("pendingVerificationEmail");
        window.location.replace("/login?verification=expired");
      } else if (message.includes("expired")) {
        setError("This code has expired. Resend a new code to continue.");
      } else if (message.includes("invalid") || message.includes("incorrect")) {
        setError("That code is incorrect. Check your email and try again.");
      } else {
        setError("We couldn't verify your email. Please try again.");
      }
    } finally {
      setIsVerifying(false);
    }
  }

  async function handleResend() {
    if (!email || cooldown > 0 || isResending) return;
    setIsResending(true);
    setError("");
    setStatus("");
    try {
      await resendSignUpCode(email);
      setCooldown(RESEND_COOLDOWN_SECONDS);
      setStatus("A new verification code is on its way. Check your inbox.");
    } catch (resendError) {
      const message = resendError instanceof Error ? resendError.message.toLowerCase() : "";
      setError(message.includes("rate") ? "Please wait before requesting another code." : "We couldn't resend the code. Please try again.");
    } finally {
      setIsResending(false);
    }
  }

  return (
    <section aria-labelledby="verify-email-title" className="verify-email">
      <div className="verify-email__intro">
        <p className="verify-email__eyebrow">Verify your email</p>
        <h1 id="verify-email-title">Check your inbox</h1>
        <p className="verify-email__description">We sent a verification code to <strong>{email || "your email address"}</strong>.</p>
      </div>

      <div className="verify-email__card">
        <form onSubmit={handleSubmit}>
          <fieldset className="verify-email__fieldset" disabled={isVerifying}>
            <legend>Enter verification code</legend>
            <div className="verify-email__digits" onPaste={handlePaste}>
              {Array.from({ length: CODE_LENGTH }, (_, index) => (
                <label className="verify-email__digit" key={index}>
                  <span className="sr-only">Digit {index + 1} of {CODE_LENGTH}</span>
                  <input
                    aria-describedby="verify-email-help"
                    autoComplete={index === 0 ? "one-time-code" : "off"}
                    inputMode="numeric"
                    maxLength={1}
                    onChange={(event) => handleChange(index, event.currentTarget.value)}
                    onKeyDown={(event) => handleKeyDown(index, event)}
                    pattern="[0-9]"
                    ref={(element) => { inputs.current[index] = element; }}
                    type="text"
                  />
                </label>
              ))}
            </div>
            <p id="verify-email-help">Enter the 6-digit code from your email.</p>
          </fieldset>

          {error ? <p className="verify-email__error" role="alert">{error}</p> : null}
          {status ? <p className="verify-email__status" role="status">{status}</p> : null}

          <button aria-busy={isVerifying} className="primary-button verify-email__submit" disabled={isVerifying || !email} type="submit">
            <span>{isVerifying ? "Verifying…" : "Verify email"}</span>
            {!isVerifying ? <ArrowIcon /> : null}
          </button>
        </form>

        <p className="verify-email__resend">
          Didn&apos;t receive a code?{" "}
          <button disabled={!email || cooldown > 0 || isResending} onClick={handleResend} type="button">
            {isResending ? "Sending…" : cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
          </button>
        </p>
      </div>
    </section>
  );
}

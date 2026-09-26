"use client";

import { type FormEvent, useState } from "react";

import { requestPasswordReset, signInWithPassword, signUp } from "../../lib/auth";

type AuthMode = "sign-in" | "sign-up" | "reset";

const MODE_COPY: Record<AuthMode, { heading: string; submitLabel: string }> = {
  "sign-in": { heading: "Sign in", submitLabel: "Sign in" },
  "sign-up": { heading: "Create your account", submitLabel: "Create account" },
  reset: { heading: "Reset your password", submitLabel: "Send reset link" },
};

export default function LoginPage() {
  const [mode, setMode] = useState<AuthMode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const copy = MODE_COPY[mode];

  function selectMode(nextMode: AuthMode) {
    setMode(nextMode);
    setError(null);
    setMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      if (mode === "sign-in") {
        await signInWithPassword(email, password);
        setMessage("Signed in successfully.");
      } else if (mode === "sign-up") {
        await signUp(email, password);
        setMessage("Account created. Check your email to confirm your account.");
      } else {
        await requestPasswordReset(email, `${window.location.origin}/reset-password`);
        setMessage("If an account exists for that email, a reset link has been sent.");
      }
    } catch {
      setError(
        mode === "sign-in"
          ? "We could not sign you in. Check your email and password and try again."
          : "We could not complete that request. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main>
      <h1>{copy.heading}</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="email">Email</label>
        <input autoComplete="email" disabled={isSubmitting} id="email" name="email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />

        {mode !== "reset" ? (
          <>
            <label htmlFor="password">Password</label>
            <input autoComplete={mode === "sign-in" ? "current-password" : "new-password"} disabled={isSubmitting} id="password" minLength={8} name="password" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
          </>
        ) : null}

        {error ? <p role="alert">{error}</p> : null}
        {message ? <p aria-live="polite">{message}</p> : null}

        <button disabled={isSubmitting} type="submit">{isSubmitting ? "Please wait…" : copy.submitLabel}</button>
      </form>

      {mode === "sign-in" ? (
        <p>
          <button onClick={() => selectMode("sign-up")} type="button">Create an account</button>
          <button onClick={() => selectMode("reset")} type="button">Forgot your password?</button>
        </p>
      ) : (
        <button onClick={() => selectMode("sign-in")} type="button">Back to sign in</button>
      )}
    </main>
  );
}

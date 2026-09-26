"use client";

import { type FormEvent, useState } from "react";

import { updatePassword } from "../../lib/auth";

export default function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      await updatePassword(password);
      setMessage("Your password has been updated. You can now sign in.");
      setPassword("");
    } catch {
      setError("This password reset link is invalid or expired. Request a new link and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main>
      <h1>Reset your password</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="password">New password</label>
        <input
          autoComplete="new-password"
          disabled={isSubmitting}
          id="password"
          minLength={8}
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
        {error ? <p role="alert">{error}</p> : null}
        {message ? <p aria-live="polite">{message}</p> : null}
        <button disabled={isSubmitting} type="submit">
          {isSubmitting ? "Please wait…" : "Update password"}
        </button>
      </form>
    </main>
  );
}

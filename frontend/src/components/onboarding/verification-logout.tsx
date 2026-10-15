"use client";

import { signOut } from "../../lib/auth";

export function VerificationLogout() {
  async function handleLogOut() {
    sessionStorage.removeItem("pendingVerificationEmail");
    try {
      await signOut();
    } catch {
      // A missing session still returns the user to sign-in.
    } finally {
      window.location.assign("/login");
    }
  }

  return <button onClick={handleLogOut} type="button">Log out</button>;
}

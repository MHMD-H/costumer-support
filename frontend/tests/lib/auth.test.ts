import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = {
  getSession: vi.fn(),
  resetPasswordForEmail: vi.fn(),
  signInWithPassword: vi.fn(),
  signOut: vi.fn(),
  signUp: vi.fn(),
  updateUser: vi.fn(),
};

vi.mock("@supabase/supabase-js", () => ({
  createClient: vi.fn(() => ({ auth })),
}));

import {
  getAccessToken,
  requestPasswordReset,
  signInWithPassword,
  signOut,
  signUp,
  updatePassword,
} from "../../src/lib/auth";

describe("Supabase dashboard authentication", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_test";
    vi.clearAllMocks();
  });

  it("delegates sign-in and signup credentials to Supabase Auth", async () => {
    auth.signInWithPassword.mockResolvedValue({ error: null });
    auth.signUp.mockResolvedValue({ error: null });

    await signInWithPassword("owner@example.com", "password123");
    await signUp("new@example.com", "password123");

    expect(auth.signInWithPassword).toHaveBeenCalledWith({
      email: "owner@example.com",
      password: "password123",
    });
    expect(auth.signUp).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "password123",
    });
  });

  it("propagates invalid-credential errors from Supabase Auth", async () => {
    const invalidCredentials = new Error("Invalid login credentials");
    auth.signInWithPassword.mockResolvedValue({ error: invalidCredentials });

    await expect(signInWithPassword("owner@example.com", "wrong-password")).rejects.toBe(
      invalidCredentials,
    );
  });

  it.each([
    ["expired recovery link", new Error("Auth session missing!")],
    ["invalid recovery token", new Error("Invalid Refresh Token")],
  ])("rejects a password update for an %s", async (_case, recoveryError) => {
    auth.updateUser.mockResolvedValue({ error: recoveryError });

    await expect(updatePassword("new-password-123")).rejects.toBe(recoveryError);
    expect(auth.updateUser).toHaveBeenCalledWith({ password: "new-password-123" });
  });

  it("updates the password through the authenticated Supabase session", async () => {
    auth.updateUser.mockResolvedValue({ error: null });

    await updatePassword("new-password-123");

    expect(auth.updateUser).toHaveBeenCalledWith({ password: "new-password-123" });
  });

  it("delegates reset, session access-token retrieval, and sign-out to Supabase Auth", async () => {
    auth.resetPasswordForEmail.mockResolvedValue({ error: null });
    auth.getSession.mockResolvedValue({ data: { session: { access_token: "access-token" } } });
    auth.signOut.mockResolvedValue({ error: null });

    await requestPasswordReset("owner@example.com", "http://localhost:3000/reset-password");
    await expect(getAccessToken()).resolves.toBe("access-token");
    await signOut();

    expect(auth.resetPasswordForEmail).toHaveBeenCalledWith("owner@example.com", {
      redirectTo: "http://localhost:3000/reset-password",
    });
    expect(auth.signOut).toHaveBeenCalledOnce();
  });
});

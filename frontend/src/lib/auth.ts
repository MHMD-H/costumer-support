import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | undefined;

function getSupabaseClient(): SupabaseClient {
  if (client) {
    return client;
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  if (!url || !publishableKey) {
    throw new Error("Supabase browser authentication is not configured.");
  }

  client = createClient(url, publishableKey);
  return client;
}

export async function signInWithPassword(email: string, password: string): Promise<void> {
  const { error } = await getSupabaseClient().auth.signInWithPassword({ email, password });

  if (error) {
    throw error;
  }
}

export async function signUp(email: string, password: string): Promise<void> {
  const { error } = await getSupabaseClient().auth.signUp({ email, password });

  if (error) {
    throw error;
  }
}

export async function verifySignUpCode(email: string, token: string): Promise<void> {
  const { data, error } = await getSupabaseClient().auth.verifyOtp({ email, token, type: "email" });

  if (error) throw error;
  if (!data.session || !data.user?.email_confirmed_at) {
    throw new Error("Your verification session has expired. Please sign in to continue.");
  }

  const { data: confirmed, error: userError } = await getSupabaseClient().auth.getUser();
  if (userError || !confirmed.user?.email_confirmed_at || confirmed.user.email !== email) {
    throw new Error("Your verification session has expired. Please sign in to continue.");
  }
}

export async function resendSignUpCode(email: string): Promise<void> {
  const { error } = await getSupabaseClient().auth.resend({ type: "signup", email });
  if (error) throw error;
}

export async function requestPasswordReset(email: string, redirectTo: string): Promise<void> {
  const { error } = await getSupabaseClient().auth.resetPasswordForEmail(email, { redirectTo });

  if (error) {
    throw error;
  }
}

export async function updatePassword(password: string): Promise<void> {
  const { error } = await getSupabaseClient().auth.updateUser({ password });

  if (error) {
    throw error;
  }
}

export async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await getSupabaseClient().auth.getSession();

  return session?.access_token ?? null;
}

export async function signOut(): Promise<void> {
  const { error } = await getSupabaseClient().auth.signOut();

  if (error) {
    throw error;
  }
}

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

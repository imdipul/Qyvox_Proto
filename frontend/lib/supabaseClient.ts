import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let browserClient: SupabaseClient | undefined;

function getBrowserClient(): SupabaseClient {
  if (browserClient) return browserClient;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !publishableKey) {
    throw new Error("Qyvox authentication is not configured.");
  }

  browserClient = createClient(url, publishableKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });
  return browserClient;
}

/**
 * Return a Supabase access token without asking for identity attributes.
 * Anonymous sign-ins must be enabled in the project's Auth settings.
 */
export async function getPrivateSessionToken(): Promise<string> {
  const client = getBrowserClient();
  const { data: sessionData, error: sessionError } = await client.auth.getSession();
  if (sessionError) {
    throw new Error("Qyvox could not restore its private authentication session.");
  }
  if (sessionData.session?.access_token) return sessionData.session.access_token;

  const { data, error } = await client.auth.signInAnonymously();
  if (error) {
    const anonymousSignInDisabled =
      error.message.toLowerCase().includes("anonymous") || error.status === 422;
    throw new Error(
      anonymousSignInDisabled
        ? "Private sign-in is disabled for this Supabase project. Enable Anonymous Sign-Ins in Authentication settings."
        : "Qyvox could not create a private authentication session. Please try again.",
    );
  }
  if (!data.session?.access_token) {
    throw new Error("Supabase did not create a private session.");
  }
  return data.session.access_token;
}

// Public Supabase project settings. These values are safe to expose in a browser;
// security is enforced by Row Level Security, never by hiding the anon/publishable key.
// Replace both placeholders with the values from Supabase Project Settings → API.
export const SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co";
export const SUPABASE_ANON_KEY = "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY";
export const SUPABASE_CONFIGURED =
  /^https:\/\/[^/]+\.supabase\.co$/.test(SUPABASE_URL) &&
  !SUPABASE_URL.includes("YOUR_PROJECT_REF") &&
  SUPABASE_ANON_KEY.length > 30 &&
  !SUPABASE_ANON_KEY.includes("YOUR_SUPABASE");

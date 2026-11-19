# Authentication and user-data setup

Forge 100K uses Supabase Auth for email/password authentication and Postgres Row Level Security for user isolation.

## What is implemented in the website

- Sign-in, sign-up, email verification flow and password-reset email.
- Persistent Supabase browser session with token refresh.
- Per-user saved-preset sync; local browser presets remain available offline.
- No service-role key is shipped to the browser.
- The auth UI stays in an explicit unconfigured state until project credentials are supplied.

## One-time project setup

1. Create a Supabase project.
2. Open Project Settings → API and copy the Project URL and publishable/anon key.
3. Put those two public values in `supabase-config.js`. Never place a service-role key in this file or any frontend bundle.
4. Run `supabase/schema.sql` in the Supabase SQL Editor.
5. In Authentication → URL Configuration, set the Site URL to the deployed GitHub Pages URL and add that exact URL to Redirect URLs.
6. Enable email confirmation. Configure SMTP for production deliverability; the default provider has sending limits.
7. Test with two distinct accounts: verify that each account can only read/write its own profile and presets.

## Security boundary

The browser key is public by design. RLS is the authorization boundary. Every user-owned row is tied to `auth.uid()`; do not add broad anon policies. Passwords are handled by Supabase Auth and are never stored in Forge tables. Production uploads need a private storage bucket, object-path policies, file-size/type limits, malware scanning and server-side GLB validation before public distribution. Do not use a service-role key in browser code.

## Remaining external prerequisites

The project URL/key, email SMTP configuration and actual Supabase project are owner-controlled. The repository contains no credentials and none are fabricated. GitHub Pages deployment does not provision a Supabase backend.

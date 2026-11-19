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
5. Run migrations `202611190001_platform_assets.sql` and `202611190002_worker_queue.sql` in order. They create the RLS-protected asset registry, private uploads, atomic queue leases and service-role-only worker RPCs.
6. In Project Settings → API → Data API, ensure the `public` schema is explicitly exposed for the REST Data API. New Supabase projects no longer automatically expose every new public table; the SQL grants and RLS policies are still required.
7. In Authentication → URL Configuration, set the Site URL to the deployed GitHub Pages URL and add that exact URL to Redirect URLs.
8. Enable email confirmation. Configure SMTP for production deliverability; the default provider has sending limits.
9. Test with two distinct accounts: verify that each account can only read/write its own profile and presets, that anonymous visitors can read only published assets, and that private uploads are isolated by user ID.

## Security boundary

The browser publishable key is public by design. RLS is the authorization boundary. Every user-owned row is tied to `auth.uid()`; do not add broad anon policies. Passwords are handled by Supabase Auth and are never stored in Forge tables. The browser must never receive a service-role or secret key. The generation worker uses that key only as a server-side secret. Production uploads need a private storage bucket, object-path policies, file-size/type limits, malware scanning and server-side GLB validation before public distribution.

## Remaining external prerequisites

The project URL/key, email SMTP configuration and actual Supabase project are owner-controlled. The repository contains no credentials and none are fabricated. GitHub Pages deployment does not provision a Supabase backend.


## Phase 5 database foundation

The platform migration deliberately keeps publication and worker completion server-controlled. Browser users can create drafts, submit pending versions, enqueue jobs and cancel only their own queued jobs. They cannot mark assets as published, mark jobs as succeeded, or update worker-owned status fields. Trusted workers must use server-side credentials stored only in the worker's secret manager. The private upload bucket is not a public asset CDN; a server worker must inspect and validate uploads before publishing immutable versions.


## Current Supabase platform changes

The Supabase changelog notes that new public tables are no longer automatically exposed through the Data API on new projects. Explicitly expose the `public` schema in Project Settings → API → Data API, then retain the least-privilege grants and RLS policies in the committed SQL. Supabase also recommends publishable keys for browser clients; legacy `anon` keys remain compatible but should not be confused with secret/service-role keys.

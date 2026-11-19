-- Forge 100K Phase 5 platform foundation.
-- Apply after supabase/schema.sql. Moderation/publication and worker transitions
-- are server-controlled; browser clients cannot publish assets or mark jobs done.
begin;

create table if not exists public.asset_catalog (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  owner_id uuid references auth.users(id) on delete set null,
  title text not null,
  description text not null default '',
  category text not null,
  visibility text not null default 'draft'
    check (visibility in ('draft','pending_review','published','rejected','archived')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (char_length(title) between 1 and 160),
  check (char_length(description) <= 4000),
  check (jsonb_typeof(metadata) = 'object')
);

create table if not exists public.asset_versions (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.asset_catalog(id) on delete cascade,
  owner_id uuid references auth.users(id) on delete set null,
  version integer not null check (version > 0),
  storage_path text not null,
  sha256 text not null check (sha256 ~ '^[a-f0-9]{64}$'),
  mime_type text not null check (mime_type in ('model/gltf-binary','model/gltf+json','application/octet-stream')),
  byte_size bigint not null check (byte_size between 1 and 52428800),
  validation_status text not null default 'pending'
    check (validation_status in ('pending','passed','failed','quarantined')),
  validation_report jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(asset_id, version),
  check (jsonb_typeof(validation_report) = 'object')
);

create table if not exists public.generation_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'queued'
    check (status in ('queued','running','succeeded','failed','cancelled')),
  job_type text not null check (job_type in ('character','garment','retopology','texture_bake','rigging','animation')),
  request jsonb not null,
  result_asset_id uuid references public.asset_catalog(id) on delete set null,
  error_code text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  check (jsonb_typeof(request) = 'object')
);

create index if not exists asset_catalog_public_idx
  on public.asset_catalog(category, created_at desc) where visibility = 'published';
create index if not exists asset_catalog_owner_idx
  on public.asset_catalog(owner_id, created_at desc);
create index if not exists asset_versions_asset_idx
  on public.asset_versions(asset_id, version desc);
create index if not exists generation_jobs_user_idx
  on public.generation_jobs(user_id, created_at desc);
create index if not exists generation_jobs_queue_idx
  on public.generation_jobs(created_at) where status = 'queued';

alter table public.asset_catalog enable row level security;
alter table public.asset_versions enable row level security;
alter table public.generation_jobs enable row level security;

drop trigger if exists asset_catalog_set_updated_at on public.asset_catalog;
create trigger asset_catalog_set_updated_at before update on public.asset_catalog
for each row execute function public.set_updated_at();

drop policy if exists "Published assets are readable by everyone" on public.asset_catalog;
create policy "Published assets are readable by everyone" on public.asset_catalog
for select to anon, authenticated using (visibility = 'published');

drop policy if exists "Owners can read their assets" on public.asset_catalog;
create policy "Owners can read their assets" on public.asset_catalog
for select to authenticated using ((select auth.uid()) = owner_id);

drop policy if exists "Users can create draft assets" on public.asset_catalog;
create policy "Users can create draft assets" on public.asset_catalog
for insert to authenticated with check (
  (select auth.uid()) = owner_id and visibility in ('draft','pending_review')
);

drop policy if exists "Owners can edit unpublished assets" on public.asset_catalog;
create policy "Owners can edit unpublished assets" on public.asset_catalog
for update to authenticated using (
  (select auth.uid()) = owner_id and visibility in ('draft','pending_review')
) with check (
  (select auth.uid()) = owner_id and visibility in ('draft','pending_review')
);

drop policy if exists "Published versions are readable" on public.asset_versions;
create policy "Published versions are readable" on public.asset_versions
for select to anon, authenticated using (
  exists (select 1 from public.asset_catalog a
    where a.id = asset_id and a.visibility = 'published')
);

drop policy if exists "Owners can read their asset versions" on public.asset_versions;
create policy "Owners can read their asset versions" on public.asset_versions
for select to authenticated using ((select auth.uid()) = owner_id);

drop policy if exists "Owners can add pending versions" on public.asset_versions;
create policy "Owners can add pending versions" on public.asset_versions
for insert to authenticated with check (
  (select auth.uid()) = owner_id and validation_status = 'pending'
  and split_part(storage_path, '/', 1) = (select auth.uid())::text
  and exists (select 1 from public.asset_catalog a
    where a.id = asset_id and a.owner_id = (select auth.uid())
      and a.visibility in ('draft','pending_review'))
);

drop policy if exists "Users can read own generation jobs" on public.generation_jobs;
create policy "Users can read own generation jobs" on public.generation_jobs
for select to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "Users can enqueue own jobs" on public.generation_jobs;
create policy "Users can enqueue own jobs" on public.generation_jobs
for insert to authenticated with check (
  (select auth.uid()) = user_id and status = 'queued'
  and result_asset_id is null and started_at is null and completed_at is null
);

revoke update on public.generation_jobs from anon, authenticated;
drop policy if exists "Users can cancel queued own jobs" on public.generation_jobs;

create or replace function public.cancel_own_generation_job(p_job_id uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $
declare
  changed integer;
begin
  update public.generation_jobs
     set status = 'cancelled', completed_at = now()
   where id = p_job_id
     and user_id = (select auth.uid())
     and status = 'queued';
  get diagnostics changed = row_count;
  return changed = 1;
end;
$;
revoke all on function public.cancel_own_generation_job(uuid) from public, anon;
grant execute on function public.cancel_own_generation_job(uuid) to authenticated;

-- Private source uploads. A trusted server worker validates GLB files and copies
-- approved immutable versions to a separate public delivery bucket.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('forge-private-uploads', 'forge-private-uploads', false, 52428800,
        array['model/gltf-binary','model/gltf+json','application/octet-stream'])
on conflict (id) do update set public = false, file_size_limit = 52428800,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Users upload only into their own private folder" on storage.objects;
create policy "Users upload only into their own private folder" on storage.objects
for insert to authenticated with check (
  bucket_id = 'forge-private-uploads'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "Users read only their private uploads" on storage.objects;
create policy "Users read only their private uploads" on storage.objects
for select to authenticated using (
  bucket_id = 'forge-private-uploads'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "Users delete only their private uploads" on storage.objects;
create policy "Users delete only their private uploads" on storage.objects
for delete to authenticated using (
  bucket_id = 'forge-private-uploads'
  and (storage.foldername(name))[1] = (select auth.uid())::text
);

commit;

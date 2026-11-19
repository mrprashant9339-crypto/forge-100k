-- Phase 5 worker leases and atomic queue operations.
begin;

alter table public.generation_jobs
  add column if not exists attempt_count integer not null default 0,
  add column if not exists max_attempts integer not null default 3,
  add column if not exists locked_at timestamptz,
  add column if not exists locked_by text,
  add column if not exists last_heartbeat_at timestamptz;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'generation_jobs_attempt_count_check') then
    alter table public.generation_jobs add constraint generation_jobs_attempt_count_check
      check (attempt_count >= 0 and attempt_count <= max_attempts);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'generation_jobs_max_attempts_check') then
    alter table public.generation_jobs add constraint generation_jobs_max_attempts_check
      check (max_attempts between 1 and 10);
  end if;
end $$;

create index if not exists generation_jobs_lease_idx
  on public.generation_jobs(status, locked_at) where status = 'running';

create or replace function public.claim_next_generation_job(p_worker_id text)
returns setof public.generation_jobs
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_job_id uuid;
begin
  if coalesce(length(trim(p_worker_id)), 0) not between 1 and 120 then
    raise exception 'worker_id must contain 1 to 120 characters';
  end if;

  update public.generation_jobs
     set status = 'failed',
         error_code = 'worker_lease_expired_max_attempts',
         completed_at = now(),
         locked_at = null,
         locked_by = null,
         last_heartbeat_at = null
   where status = 'running'
     and locked_at < now() - interval '15 minutes'
     and attempt_count >= max_attempts;

  select id into v_job_id
    from public.generation_jobs
   where status = 'queued'
      or (status = 'running'
          and locked_at < now() - interval '15 minutes'
          and attempt_count < max_attempts)
   order by created_at asc
   for update skip locked
   limit 1;

  if v_job_id is null then
    return;
  end if;

  return query
    update public.generation_jobs
       set status = 'running',
           attempt_count = attempt_count + 1,
           started_at = coalesce(started_at, now()),
           locked_at = now(),
           locked_by = p_worker_id,
           last_heartbeat_at = now(),
           error_code = null
     where id = v_job_id
    returning *;
end;
$$;

create or replace function public.heartbeat_generation_job(p_job_id uuid, p_worker_id text)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  changed integer;
begin
  update public.generation_jobs
     set locked_at = now(), last_heartbeat_at = now()
   where id = p_job_id and status = 'running' and locked_by = p_worker_id;
  get diagnostics changed = row_count;
  return changed = 1;
end;
$$;

create or replace function public.complete_generation_job(
  p_job_id uuid, p_worker_id text, p_result_asset_id uuid
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  changed integer;
begin
  update public.generation_jobs j
     set status = 'succeeded',
         result_asset_id = p_result_asset_id,
         completed_at = now(),
         locked_at = null,
         locked_by = null,
         last_heartbeat_at = null,
         error_code = null
    from public.asset_catalog a
   where j.id = p_job_id
     and j.locked_by = p_worker_id
     and j.status = 'running'
     and a.id = p_result_asset_id
     and a.owner_id = j.user_id;
  get diagnostics changed = row_count;
  return changed = 1;
end;
$$;

create or replace function public.fail_generation_job(
  p_job_id uuid, p_worker_id text, p_error_code text
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  changed integer;
begin
  update public.generation_jobs
     set status = case when attempt_count < max_attempts then 'queued' else 'failed' end,
         completed_at = case when attempt_count < max_attempts then null else now() end,
         error_code = left(coalesce(nullif(trim(p_error_code), ''), 'worker_error'), 100),
         locked_at = null,
         locked_by = null,
         last_heartbeat_at = null
   where id = p_job_id and status = 'running' and locked_by = p_worker_id;
  get diagnostics changed = row_count;
  return changed = 1;
end;
$$;

revoke all on function public.claim_next_generation_job(text) from public, anon, authenticated;
revoke all on function public.heartbeat_generation_job(uuid, text) from public, anon, authenticated;
revoke all on function public.complete_generation_job(uuid, text, uuid) from public, anon, authenticated;
revoke all on function public.fail_generation_job(uuid, text, text) from public, anon, authenticated;
grant execute on function public.claim_next_generation_job(text) to service_role;
grant execute on function public.heartbeat_generation_job(uuid, text) to service_role;
grant execute on function public.complete_generation_job(uuid, text, uuid) to service_role;
grant execute on function public.fail_generation_job(uuid, text, text) to service_role;

commit;

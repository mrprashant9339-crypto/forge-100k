-- Forge 100K: Supabase Auth profile + per-user saved presets.
-- Apply in Supabase SQL Editor. Never disable RLS on these tables.
begin;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint profiles_display_name_length check (char_length(display_name) <= 80)
);

create table if not exists public.saved_presets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  preset_id text not null,
  name text not null,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint saved_presets_name_length check (char_length(name) between 1 and 120),
  constraint saved_presets_config_object check (jsonb_typeof(config) = 'object'),
  constraint saved_presets_user_preset_unique unique (user_id, preset_id)
);

create index if not exists saved_presets_user_updated_idx
  on public.saved_presets (user_id, updated_at desc);

create or replace function public.set_updated_at()
returns trigger language plpgsql set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists saved_presets_set_updated_at on public.saved_presets;
create trigger saved_presets_set_updated_at before update on public.saved_presets
for each row execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, left(coalesce(new.raw_user_meta_data ->> 'full_name', ''), 80))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.saved_presets enable row level security;

drop policy if exists "Users can read own profile" on public.profiles;
create policy "Users can read own profile" on public.profiles
for select to authenticated using ((select auth.uid()) = id);

drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile" on public.profiles
for update to authenticated using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

drop policy if exists "Users can read own presets" on public.saved_presets;
create policy "Users can read own presets" on public.saved_presets
for select to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "Users can insert own presets" on public.saved_presets;
create policy "Users can insert own presets" on public.saved_presets
for insert to authenticated with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update own presets" on public.saved_presets;
create policy "Users can update own presets" on public.saved_presets
for update to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete own presets" on public.saved_presets;
create policy "Users can delete own presets" on public.saved_presets
for delete to authenticated using ((select auth.uid()) = user_id);

revoke all on public.profiles from anon, authenticated;
grant select, update on public.profiles to authenticated;
revoke all on public.saved_presets from anon, authenticated;
grant select, insert, update, delete on public.saved_presets to authenticated;

commit;

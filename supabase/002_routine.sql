-- Banana Quest: daily routine timers (25-min Maths / English sessions).
-- Run once in Supabase -> SQL Editor. Safe to re-run.
-- The routine plan itself lives in ar_settings.data.routine (no table needed); finished sessions are normal
-- ar_activities rows (kind 'maths' or 'english'), already approved. This table only keeps a running timer,
-- so it survives a page reload or a tablet going to sleep.

create table if not exists public.ar_routine_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.ar_profiles(id) on delete cascade,
  day date not null default current_date,
  block_id text not null,              -- id of the session in the routine plan
  kind text not null,                  -- maths | english
  title text,
  minutes int not null default 25,
  started_at timestamptz not null default now(),
  ends_at timestamptz not null,
  status text not null default 'running' check (status in ('running','done','cancelled')),
  closed_at timestamptz,
  created_at timestamptz default now()
);

alter table public.ar_routine_runs enable row level security;

drop policy if exists ar_routine_runs_select on public.ar_routine_runs;
create policy ar_routine_runs_select on public.ar_routine_runs for select using (public.ar_in_my_family(user_id));
drop policy if exists ar_routine_runs_insert on public.ar_routine_runs;
create policy ar_routine_runs_insert on public.ar_routine_runs for insert
  with check (user_id = auth.uid() or (public.ar_is_parent() and public.ar_in_my_family(user_id)));
drop policy if exists ar_routine_runs_update on public.ar_routine_runs;
create policy ar_routine_runs_update on public.ar_routine_runs for update
  using (user_id = auth.uid() or (public.ar_is_parent() and public.ar_in_my_family(user_id)));
drop policy if exists ar_routine_runs_delete on public.ar_routine_runs;
create policy ar_routine_runs_delete on public.ar_routine_runs for delete
  using (user_id = auth.uid() or (public.ar_is_parent() and public.ar_in_my_family(user_id)));

create index if not exists idx_ar_routine_runs_user on public.ar_routine_runs(user_id, status);

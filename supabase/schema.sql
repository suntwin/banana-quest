-- Banana Quest (Aadiv's rewards app): Supabase schema
-- Every table is prefixed ar_ so it can sit in the SAME Supabase project as
-- Selective Brain without touching Siyonah's tables.
-- Run once in Supabase -> SQL Editor. Safe to re-run.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------
-- Families & profiles
-- ---------------------------------------------------------------
create table if not exists public.ar_families (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz default now()
);

create table if not exists public.ar_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  family_id uuid not null references public.ar_families(id) on delete cascade,
  display_name text not null,
  role text not null check (role in ('child','parent')),
  avatar text default '🍌',
  email text,
  goal_reward_id uuid,                 -- the reward he is saving for
  created_at timestamptz default now()
);

create or replace function public.ar_my_family() returns uuid
language sql stable security definer set search_path = public as $$
  select family_id from public.ar_profiles where id = auth.uid()
$$;

create or replace function public.ar_is_parent() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select role = 'parent' from public.ar_profiles where id = auth.uid()), false)
$$;

create or replace function public.ar_in_my_family(uid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.ar_profiles p
                 where p.id = uid and p.family_id = public.ar_my_family())
$$;

-- ---------------------------------------------------------------
-- Family settings (XP rules, weekly goals, screen-time rules, approval mode)
-- ---------------------------------------------------------------
create table if not exists public.ar_settings (
  family_id uuid primary key references public.ar_families(id) on delete cascade,
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz default now()
);

-- ---------------------------------------------------------------
-- Activity log: sport, maths, writing
-- ---------------------------------------------------------------
create table if not exists public.ar_activities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.ar_profiles(id) on delete cascade,
  day date not null,
  area text not null check (area in ('sport','maths','writing')),
  kind text not null,                  -- basketball | tennis | swimming | maths | writing
  session_type text,
  minutes int default 0,
  effort int,
  details jsonb default '{}'::jsonb,   -- stats, xp breakdown, personal bests, writing text
  note text,
  xp int not null default 0,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  parent_note text,
  reviewed_at timestamptz,
  created_at timestamptz default now()
);

-- ---------------------------------------------------------------
-- XP earned (positive, or a parent adjustment). Spending lives in ar_redemptions.
-- ---------------------------------------------------------------
create table if not exists public.ar_xp_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.ar_profiles(id) on delete cascade,
  amount int not null,
  reason text not null,
  source_id text,                      -- activity id, or week:<date>:<goal> for weekly bonuses
  created_at timestamptz default now()
);

-- ---------------------------------------------------------------
-- Reward catalogue (parent-configured) and redemptions (rewards + screen time)
-- ---------------------------------------------------------------
create table if not exists public.ar_rewards (
  id uuid primary key default gen_random_uuid(),
  family_id uuid not null references public.ar_families(id) on delete cascade,
  name text not null,
  emoji text default '🎁',
  cost int not null check (cost > 0),
  description text,
  active boolean not null default true,
  created_at timestamptz default now()
);

create table if not exists public.ar_redemptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.ar_profiles(id) on delete cascade,
  kind text not null check (kind in ('reward','screen')),
  reward_id uuid references public.ar_rewards(id) on delete set null,
  title text not null,
  cost int not null default 0,
  minutes int,                         -- screen time only
  day date not null default current_date,
  status text not null check (status in ('requested','delivered','rejected','ready','running','used','cancelled')),
  started_at timestamptz,
  closed_at timestamptz,
  created_at timestamptz default now()
);

create table if not exists public.ar_badges (
  user_id uuid not null references public.ar_profiles(id) on delete cascade,
  badge_key text not null,
  earned_at timestamptz default now(),
  seen boolean not null default false,
  primary key (user_id, badge_key)
);

-- ---------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------
alter table public.ar_families    enable row level security;
alter table public.ar_profiles    enable row level security;
alter table public.ar_settings    enable row level security;
alter table public.ar_activities  enable row level security;
alter table public.ar_xp_events   enable row level security;
alter table public.ar_rewards     enable row level security;
alter table public.ar_redemptions enable row level security;
alter table public.ar_badges      enable row level security;

drop policy if exists ar_fam_select on public.ar_families;
create policy ar_fam_select on public.ar_families for select using (id = public.ar_my_family());

drop policy if exists ar_prof_select on public.ar_profiles;
create policy ar_prof_select on public.ar_profiles for select using (family_id = public.ar_my_family());
drop policy if exists ar_prof_update on public.ar_profiles;
create policy ar_prof_update on public.ar_profiles for update using (id = auth.uid());

-- family-level tables: everyone in the family reads, only the parent writes
do $$
declare t text;
begin
  foreach t in array array['ar_settings','ar_rewards'] loop
    execute format('drop policy if exists %1$s_select on public.%1$s', t);
    execute format('create policy %1$s_select on public.%1$s for select using (family_id = public.ar_my_family())', t);
    execute format('drop policy if exists %1$s_write on public.%1$s', t);
    execute format('create policy %1$s_write on public.%1$s for all using (family_id = public.ar_my_family() and public.ar_is_parent()) with check (family_id = public.ar_my_family() and public.ar_is_parent())', t);
  end loop;
end $$;

-- per-user tables: read the family; write your own rows, and the parent can write the child's rows
do $$
declare t text;
begin
  foreach t in array array['ar_activities','ar_xp_events','ar_redemptions','ar_badges'] loop
    execute format('drop policy if exists %1$s_select on public.%1$s', t);
    execute format('create policy %1$s_select on public.%1$s for select using (public.ar_in_my_family(user_id))', t);
    execute format('drop policy if exists %1$s_insert on public.%1$s', t);
    execute format('create policy %1$s_insert on public.%1$s for insert with check (user_id = auth.uid() or (public.ar_is_parent() and public.ar_in_my_family(user_id)))', t);
    execute format('drop policy if exists %1$s_update on public.%1$s', t);
    execute format('create policy %1$s_update on public.%1$s for update using (user_id = auth.uid() or (public.ar_is_parent() and public.ar_in_my_family(user_id)))', t);
    execute format('drop policy if exists %1$s_delete on public.%1$s', t);
    execute format('create policy %1$s_delete on public.%1$s for delete using (user_id = auth.uid() or (public.ar_is_parent() and public.ar_in_my_family(user_id)))', t);
  end loop;
end $$;

create index if not exists idx_ar_act_user on public.ar_activities(user_id, created_at);
create index if not exists idx_ar_xp_user on public.ar_xp_events(user_id);
create index if not exists idx_ar_red_user on public.ar_redemptions(user_id, created_at);

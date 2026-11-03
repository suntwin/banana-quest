-- Banana Words: a daily vocabulary trainer for Aadiv (Year 2-4 word bank, spaced reviews).
-- Run once in Supabase -> SQL Editor (same project as Selective Brain; every table is prefixed ar_). Safe to re-run.

create table if not exists public.ar_vocab_words (
  family_id uuid not null references public.ar_families(id) on delete cascade,
  id text not null,                       -- slug of the word, e.g. 'curious'
  word text not null,
  pos text,
  definition text not null,
  example text,
  synonyms jsonb not null default '[]'::jsonb,
  antonyms jsonb not null default '[]'::jsonb,
  hook text,
  confusable text,
  level int not null default 1,           -- 1 = Year 2, 2 = Year 3, 3 = Year 4 stretch
  ord int not null,                       -- the order new words are introduced
  active boolean not null default true,
  created_at timestamptz default now(),
  primary key (family_id, id)
);

create table if not exists public.ar_vocab_progress (
  user_id uuid not null references public.ar_profiles(id) on delete cascade,
  word_id text not null,
  stage int not null default 1,           -- 1 meaning, 2 reverse, 3 sentence, 4 synonym/opposite, 5 spelling, 6 mastered
  next_due date not null default current_date,
  introduced_on date not null default current_date,
  correct int not null default 0,
  wrong int not null default 0,
  lapses int not null default 0,
  leech boolean not null default false,
  last_seen timestamptz,
  created_at timestamptz default now(),
  primary key (user_id, word_id)
);

create table if not exists public.ar_vocab_reviews (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.ar_profiles(id) on delete cascade,
  word_id text not null,
  mode text not null,
  correct boolean not null,
  day date not null default current_date,
  created_at timestamptz default now()
);

alter table public.ar_vocab_words enable row level security;
alter table public.ar_vocab_progress enable row level security;
alter table public.ar_vocab_reviews enable row level security;

drop policy if exists ar_vocab_words_select on public.ar_vocab_words;
create policy ar_vocab_words_select on public.ar_vocab_words for select using (family_id = public.ar_my_family());
drop policy if exists ar_vocab_words_write on public.ar_vocab_words;
create policy ar_vocab_words_write on public.ar_vocab_words for all
  using (family_id = public.ar_my_family() and public.ar_is_parent())
  with check (family_id = public.ar_my_family() and public.ar_is_parent());

do $$
declare t text;
begin
  foreach t in array array['ar_vocab_progress','ar_vocab_reviews'] loop
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

create index if not exists idx_ar_vocab_words_ord on public.ar_vocab_words(family_id, ord);
create index if not exists idx_ar_vocab_progress_due on public.ar_vocab_progress(user_id, next_due);
create index if not exists idx_ar_vocab_reviews_user on public.ar_vocab_reviews(user_id, day);

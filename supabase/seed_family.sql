-- Run AFTER schema.sql, and after Aadiv's login exists:
--   Supabase -> Authentication -> Users -> Add user -> chawlaaadiv@gmail.com (tick "Auto Confirm User").
-- Papa's login (niteshchawla81@gmail.com) already exists if this is the Selective Brain project;
-- otherwise add it the same way first.

with fam as (
  insert into public.ar_families (name) values ('Chawla family') returning id
),
people as (
  insert into public.ar_profiles (id, family_id, display_name, role, avatar, email)
  select u.id, fam.id,
         case when u.email = 'chawlaaadiv@gmail.com' then 'Aadiv' else 'Papa' end,
         case when u.email = 'chawlaaadiv@gmail.com' then 'child' else 'parent' end,
         case when u.email = 'chawlaaadiv@gmail.com' then '🍌' else '🧭' end,
         u.email
  from auth.users u, fam
  where u.email in ('chawlaaadiv@gmail.com', 'niteshchawla81@gmail.com')
  returning family_id
)
insert into public.ar_rewards (family_id, name, emoji, cost, description)
select f.family_id, r.name, r.emoji, r.cost, r.description
from (select distinct family_id from people) f,
     (values
       ('Stay up 30 min late', '🌙', 200, 'Friday or Saturday night only.'),
       ('Ice-cream trip', '🍦', 250, 'One scoop (or two!) at the shop of your choice.'),
       ('Pick the family movie', '🎬', 300, 'You choose, everyone watches.'),
       ('Pizza night pick', '🍕', 400, 'Choose the pizza for family night.'),
       ('Beyblade', '🌀', 800, 'A new Beyblade top of your choice (up to $25).'),
       ('Trampoline park', '🤸', 1000, 'A session at the trampoline / play centre.'),
       ('New basketball', '🏀', 1200, 'A new ball for the driveway hoop.'),
       ('LEGO small set', '🧱', 1500, 'A LEGO set up to $40.'),
       ('LEGO big set', '🏗️', 4000, 'The big one, up to $120.')
     ) as r(name, emoji, cost, description);

-- Check: should list Aadiv (child) and Papa (parent), plus 9 rewards
select p.display_name, p.role, p.email from public.ar_profiles p;
select name, cost from public.ar_rewards order by cost;

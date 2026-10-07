-- Test family for Banana Quest: a tester can try BOTH sides (kid + parent) without
-- touching Aadiv's real XP, logs or rewards. RLS keeps the two families fully separate.
--
-- BEFORE running: Supabase -> Authentication -> Users -> Add user (tick "Auto Confirm User"):
--   testkid@example.com     (password of your choice)  -> plays as the child
--   testparent@example.com  (password of your choice)  -> sees the Parent Hub
-- Change the two e-mails below (in BOTH places) if you used different ones.

with fam as (
  insert into public.ar_families (name) values ('Test family') returning id
),
people as (
  insert into public.ar_profiles (id, family_id, display_name, role, avatar, email)
  select u.id, fam.id,
         case when u.email = 'testkid@example.com' then 'Test Kid' else 'Test Parent' end,
         case when u.email = 'testkid@example.com' then 'child' else 'parent' end,
         case when u.email = 'testkid@example.com' then '🍌' else '🧪' end,
         u.email
  from auth.users u, fam
  where u.email in ('testkid@example.com', 'testparent@example.com')
  returning family_id
)
insert into public.ar_rewards (family_id, name, emoji, cost, description)
select f.family_id, r.name, r.emoji, r.cost, r.description
from (select distinct family_id from people) f,
     (values
       ('Stay up 30 min late', '🌙', 200, 'Friday or Saturday night only.'),
       ('Ice-cream trip', '🍦', 250, 'One scoop (or two!) at the shop of your choice.'),
       ('Pick the family movie', '🎬', 300, 'You choose, everyone watches.'),
       ('Beyblade', '🌀', 800, 'A new Beyblade top of your choice (up to $25).'),
       ('LEGO small set', '🧱', 1500, 'A LEGO set up to $40.')
     ) as r(name, emoji, cost, description);

-- Check: two test profiles in their own family
select f.name as family, p.display_name, p.role, p.email
from public.ar_profiles p join public.ar_families f on f.id = p.family_id
order by f.name, p.role;

-- To remove the test family later (deletes its profiles, logs, XP and rewards):
-- delete from public.ar_families where name = 'Test family';
-- then delete the two users in Authentication -> Users.

# 🍌 Banana Quest

Aadiv's rewards app. Built on the same pattern as Selective Brain (Streamlit + Supabase + GitHub + Streamlit Cloud), with a yellow-and-denim banana theme.

**The loop**
1. **Log it (1 min):** after basketball, tennis, swimming, maths or writing, Aadiv logs the session: minutes, effort and stats (free throws, points, serves, rally, distance, 50 m time, maths score, word count). He sees the XP he'll earn before he saves.
2. **Papa checks it:** Parent Hub → ✅ To approve. Approve (adjust the XP if needed, give ⭐ for great writing) or "Don't count it". There's an "Approve all" button, or switch to auto-approve in Settings.
3. **Weekly missions:** goals per activity (default basketball 120 min, tennis 90, swimming 90, maths 90, writing 2 pieces). +30 XP for each goal hit, and +50 if he hits all three sports goals.
4. **Spend it:**
   - 🎁 **Reward Shop:** Beyblade, LEGO and so on. He taps Swap!, the XP is held, and Papa marks it "Given" or "Decline" (which refunds the XP). He can pin one reward as his ⭐ goal to show a savings bar on Home.
   - 📺 **Screen time:** buy 15/30/45/60-minute tickets (default 3 XP per minute), up to a daily limit (60 min on school days, 120 at weekends). By default, screen time only unlocks after something has been logged that day. Tapping Start runs a countdown, and "Stop early" saves the unused minutes. Unused tickets are refunded the next day.
5. **Trophy Room:** 19 badges, personal bests per sport (new PBs earn +25 XP), minutes-per-week chart, 50 m time chart and 11 levels (Banana Sprout → Supreme Banana King). Levels use lifetime XP, so spending never drops a level.

## XP rules (defaults, all editable in Parent Hub → Settings → Advanced)
| What | XP |
|---|---|
| Sport | 1 per minute (cap 120), +10 lesson/squad, +20 game/match, +30 race/carnival |
| Sport stats | +2 per 5 free throws / serves in, +1 per basketball point, +2 per 100 m swum, +15 tennis win, +25 per personal best |
| Maths | 1 per minute (cap 60), +10 for 80%+, +20 for 100% |
| Writing | 10 per piece, +5 per 50 words (cap 600 words), +10 per parent ⭐ (up to 3) |
| Effort 4 / 5 | +5 / +10 |
| Weekly goal | +30 each, +50 for all three sports |

With these defaults, a solid week earns roughly 500 to 800 XP. That puts a Beyblade (800) at about a week, and a small LEGO set (1,500) at about two weeks.

---

## One-time setup (about 15 minutes)

### 1. Supabase (reuse the Selective Brain project)
All tables are prefixed `ar_`, so nothing clashes with Siyonah's app, and your existing parent login works in both apps.
1. **SQL Editor → New query**: paste all of `supabase/schema.sql` and **Run**.
2. **Authentication → Users → Add user**: `chawlaaadiv@gmail.com` with a password he can type. Tick **Auto Confirm User**.
3. **SQL Editor**: paste `supabase/seed_family.sql` and **Run**. The output should list Aadiv and Papa, plus 9 rewards.
4. Copy the same **Project URL** and **anon public** key you used for Selective Brain.

(If you want a separate Supabase project instead, run both SQL files there and add the parent login first.)

### 2. GitHub (PowerShell, one command per line)
```
cd "C:\Obsidian Vault\AadivRewards"
git init
git add .
git commit -m "Banana Quest v1"
gh repo create banana-quest --private --source . --push
```

### 3. Streamlit Community Cloud
1. https://share.streamlit.io → **Create app** → repo `banana-quest`, branch `main`, file `app.py`.
2. **Advanced settings → Secrets**:
   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_ANON_KEY = "eyJ..."
   ```
3. Deploy, then bookmark it on Aadiv's device.

## Run locally / demo mode
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Without Supabase secrets the app stops with a "Supabase isn't connected yet" message, so it never runs on throwaway local data.
To try it offline with fake data, switch demo mode on explicitly in PowerShell:
```
$env:AR_DEMO="1"
streamlit run app.py
```
Demo mode shows two buttons (Aadiv / Papa) and stores data in `.demo_data.json`.

## Test user
`supabase/seed_test_family.sql` creates a separate **Test family** with a test kid and a test parent, so someone can try both sides without touching Aadiv's XP. First add `testkid@example.com` and `testparent@example.com` in Authentication → Users (tick Auto Confirm), then run the script. Delete the family afterwards with the line at the bottom of the script.

## Files
- `app.py`: login and navigation (child: Home, Log it!, Reward Shop, Trophy Room; parent: Parent Hub plus the same views)
- `ar/gamify.py`: sports catalogue, XP calculator, PBs, levels, streak, weekly goals, badges, default rewards
- `ar/data.py`: reads and writes (wallet, approvals, weekly bonuses, rewards, screen-time tickets)
- `ar/store.py`: Supabase (`ar_` tables) or local JSON
- `ar/style.py`: banana theme
- `views/`: home, log, shop, trophies, parent
- `supabase/`: schema and seed

## Ideas for later
Coach or parent photo proof, a monthly "Most Improved" trophy, sibling leaderboard with Siyonah, push reminders, tennis match score detail, swim times per stroke and distance, a printable weekly certificate.

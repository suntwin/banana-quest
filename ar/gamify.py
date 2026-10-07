"""Sports catalogue, XP rules, levels, streaks, weekly goals and badges.

All pure functions over plain rows so they are easy to test.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Australia/Melbourne")

# ---------------------------------------------------------------- catalogue
# Each activity "kind" belongs to an area: sport, maths or writing.
# fields: (key, label, type[, options])  type = int | float | text | select
SPORTS = {
    "basketball": {
        "name": "Basketball", "icon": "🏀", "area": "sport",
        "types": ["Training", "Coaching / lesson", "Game", "Shooting practice"],
        "fields": [
            ("ft_made", "Free throws made", "int"),
            ("ft_att", "Free throws tried", "int"),
            ("points", "Points I scored (game)", "int"),
            ("skill", "Skill I worked on (dribble, layup, defence...)", "text"),
        ],
    },
    "tennis": {
        "name": "Tennis", "icon": "🎾", "area": "sport",
        "types": ["Lesson", "Practice hit", "Match", "Serve practice"],
        "fields": [
            ("serves_in", "Serves in", "int"),
            ("serves_att", "Serves tried", "int"),
            ("longest_rally", "Longest rally (shots)", "int"),
            ("result", "Match result", "select", ["", "Won", "Lost", "Close loss"]),
            ("skill", "Skill I worked on (forehand, backhand, volley...)", "text"),
        ],
    },
    "swimming": {
        "name": "Swimming", "icon": "🏊", "area": "sport",
        "types": ["Squad training", "Lesson", "Race / carnival", "Free swim"],
        "fields": [
            ("distance_m", "Distance swum (metres)", "int"),
            ("stroke", "Main stroke", "select", ["Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Mixed"]),
            ("best50_sec", "Best 50 m time (seconds)", "float"),
            ("skill", "Skill I worked on (turns, dives, kick...)", "text"),
        ],
    },
}
OTHER = {
    "maths": {"name": "Maths", "icon": "🔢", "area": "maths"},
    "writing": {"name": "English writing", "icon": "✍️", "area": "writing"},
}
KINDS = {**SPORTS, **OTHER}
MATHS_TOPICS = ["Times tables", "Mental maths", "Fractions & decimals", "Problem solving",
                "Measurement & geometry", "Homework", "Other"]
MATHS_SOURCES = ["Worksheet", "Maths app", "Tutor / class homework", "Workbook", "Other"]
WRITING_GENRES = ["Story (narrative)", "Persuasive", "Information report", "Recount / journal",
                  "Poem", "Book review", "Other"]

# which session types earn which bonus
LESSON_TYPES = {"Coaching / lesson", "Lesson", "Squad training"}
MATCH_TYPES = {"Game", "Match"}
RACE_TYPES = {"Race / carnival"}

# ---------------------------------------------------------------- default settings
DEFAULT_RULES = {
    # sport (the main focus)
    "sport_per_min": 1, "sport_cap_min": 120,
    "lesson_bonus": 10, "match_bonus": 20, "race_bonus": 30,
    "effort4_bonus": 5, "effort5_bonus": 10,
    "per_5_makes": 2,        # every 5 free throws made / serves in
    "per_point": 1,          # basketball points in a game
    "per_100m": 2,           # swimming distance
    "win_bonus": 15,
    "pb_bonus": 25,          # personal best (beats an earlier record)
    # maths
    "maths_per_min": 1, "maths_cap_min": 60, "maths_80_bonus": 10, "maths_100_bonus": 20,
    # writing
    "writing_base": 10, "writing_per_50_words": 5, "writing_cap_words": 600, "writing_star": 10,
    # weekly goals
    "weekly_goal_bonus": 30, "triple_threat_bonus": 50,
}
DEFAULT_GOALS = {"basketball": 120, "tennis": 90, "swimming": 90, "maths": 90, "writing": 2}
DEFAULT_SCREEN = {"xp_per_min": 3, "cap_weekday": 60, "cap_weekend": 120,
                  "need_activity": True, "options": [15, 30, 45, 60]}
DEFAULT_TIPS = [
    "🏀 Free throws: same routine every time. Bounce, breathe, bend the knees, follow through.",
    "🎾 Watch the ball onto the strings. Eyes on the ball, not the other player.",
    "🏊 Long and strong: reach far in front and kick from the hips, not the knees.",
    "🏀 Dribble with your fingertips and keep your eyes up. Look at the court, not the ball.",
    "🎾 Split-step every time your opponent hits. Tiny hop, then go!",
    "🏊 Breathe out under water so you only need a quick breath in.",
    "💧 Drink water before, during and after training. Bananas are great fuel too 🍌",
    "🔢 Times tables are like free throws: a few minutes every day makes them automatic.",
    "✍️ Great stories have a problem. What goes wrong for your character?",
    "😴 Sleep is when muscles grow. Champions go to bed on time.",
]
ACTIVITY_ORDER = ["basketball", "tennis", "swimming", "maths", "writing"]
DEFAULT_SETTINGS = {"rules": DEFAULT_RULES, "goals": DEFAULT_GOALS, "screen": DEFAULT_SCREEN,
                    "approval": "parent", "tips": DEFAULT_TIPS}


def active_kinds(sett: dict) -> list[str]:
    """Activities Aadiv can log: a weekly goal of 0 switches an activity off
    (hidden from Home and Log it!). Past logs and records stay in the Trophy Room."""
    goals = sett.get("goals") or {}
    return [k for k in ACTIVITY_ORDER if int(goals.get(k, 0) or 0) > 0]

DEFAULT_REWARDS = [
    {"name": "Ice-cream trip", "emoji": "🍦", "cost": 250, "description": "One scoop (or two!) at the shop of your choice."},
    {"name": "Stay up 30 min late", "emoji": "🌙", "cost": 200, "description": "Friday or Saturday night only."},
    {"name": "Pick the family movie", "emoji": "🎬", "cost": 300, "description": "You choose, everyone watches."},
    {"name": "Pizza night pick", "emoji": "🍕", "cost": 400, "description": "Choose the pizza for family night."},
    {"name": "Beyblade", "emoji": "🌀", "cost": 800, "description": "A new Beyblade top of your choice (up to $25)."},
    {"name": "Trampoline park", "emoji": "🤸", "cost": 1000, "description": "A session at the trampoline / play centre."},
    {"name": "New basketball", "emoji": "🏀", "cost": 1200, "description": "A new ball for the driveway hoop."},
    {"name": "LEGO small set", "emoji": "🧱", "cost": 1500, "description": "A LEGO set up to $40."},
    {"name": "LEGO big set", "emoji": "🏗️", "cost": 4000, "description": "The big one, up to $120."},
]


def merged_settings(saved: dict | None) -> dict:
    s = copy.deepcopy(DEFAULT_SETTINGS)
    for k, v in (saved or {}).items():
        if isinstance(v, dict) and isinstance(s.get(k), dict):
            s[k].update(v)
        else:
            s[k] = v
    return s


# ---------------------------------------------------------------- levels (lifetime XP)
LEVELS = [
    (0, "Banana Sprout", "🍌"),
    (200, "Goggle Rookie", "🥽"),
    (500, "Overall Ace", "👖"),
    (1000, "Banana Baller", "🏀"),
    (1700, "Court Captain", "🎾"),
    (2600, "Pool Rocket", "🚀"),
    (3800, "Gadget Genius", "🔧"),
    (5300, "Mega Minion", "💛"),
    (7200, "Banana Legend", "⭐"),
    (9500, "Big Boss Banana", "😎"),
    (12500, "Supreme Banana King", "👑"),
]


def level_for(xp: int) -> dict:
    idx = 0
    for i, (need, _, _) in enumerate(LEVELS):
        if xp >= need:
            idx = i
    need, name, icon = LEVELS[idx]
    nxt = LEVELS[idx + 1][0] if idx + 1 < len(LEVELS) else None
    pct = 1.0 if nxt is None else (xp - need) / (nxt - need)
    return {"num": idx + 1, "name": name, "icon": icon, "xp": xp, "floor": need,
            "next": nxt, "pct": max(0.0, min(1.0, pct)),
            "to_next": None if nxt is None else nxt - xp}


# ---------------------------------------------------------------- time helpers
def today() -> date:
    return datetime.now(TZ).date()


def week_start(d: date | None = None) -> date:
    d = d or today()
    return d - timedelta(days=d.weekday())


def to_date(v) -> date | None:
    if not v:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    s = str(v).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return date.fromisoformat(s[:10])
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(TZ).date()


def is_weekend(d: date | None = None) -> bool:
    return (d or today()).weekday() >= 5


# ---------------------------------------------------------------- personal bests
def _num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def metrics(kind: str, det: dict) -> dict:
    """Record-able numbers for one activity. Higher is better unless the key ends in _low."""
    det = det or {}
    m = {}
    if kind == "basketball":
        made, att = _num(det.get("ft_made")), _num(det.get("ft_att"))
        if made is not None:
            m["Most free throws made"] = made
        if made is not None and att and att >= 10:
            m["Best free-throw %"] = round(100 * made / att, 1)
        if _num(det.get("points")) is not None:
            m["Most points in a game"] = _num(det.get("points"))
    elif kind == "tennis":
        si, sa = _num(det.get("serves_in")), _num(det.get("serves_att"))
        if si is not None and sa and sa >= 10:
            m["Best serve %"] = round(100 * si / sa, 1)
        if _num(det.get("longest_rally")) is not None:
            m["Longest rally"] = _num(det.get("longest_rally"))
    elif kind == "swimming":
        if _num(det.get("distance_m")) is not None:
            m["Longest swim (m)"] = _num(det.get("distance_m"))
        t = _num(det.get("best50_sec"))
        if t:
            m["Fastest 50 m (s)_low"] = t
    return {k: v for k, v in m.items() if v}


def bests(kind: str, history: list[dict]) -> dict:
    """Current records for a sport from earlier activities: {metric: (value, day)}."""
    out = {}
    for a in history:
        if a.get("kind") != kind or a.get("status") == "rejected":
            continue
        for k, v in metrics(kind, a.get("details")).items():
            low = k.endswith("_low")
            cur = out.get(k)
            if cur is None or (v < cur[0] if low else v > cur[0]):
                out[k] = (v, a.get("day"))
    return out


def label(metric_key: str) -> str:
    return metric_key.replace("_low", "")


# ---------------------------------------------------------------- XP calculator
def calc_xp(kind: str, session_type: str, minutes: int, effort: int, det: dict,
            history: list[dict], rules: dict) -> tuple[int, list, list]:
    """Return (total XP, [(line, xp)], [personal-best labels])."""
    r = {**DEFAULT_RULES, **(rules or {})}
    det = det or {}
    lines, pbs = [], []
    minutes = int(minutes or 0)
    if kind in SPORTS:
        m = min(minutes, int(r["sport_cap_min"]))
        lines.append((f"{m} min of {SPORTS[kind]['name'].lower()}", m * r["sport_per_min"]))
        if session_type in LESSON_TYPES:
            lines.append(("Lesson / squad bonus", r["lesson_bonus"]))
        if session_type in MATCH_TYPES:
            lines.append(("Game day bonus", r["match_bonus"]))
        if session_type in RACE_TYPES:
            lines.append(("Race day bonus", r["race_bonus"]))
        makes = int(_num(det.get("ft_made")) or 0) + int(_num(det.get("serves_in")) or 0)
        if makes >= 5:
            lines.append((f"{makes} shots / serves made", (makes // 5) * r["per_5_makes"]))
        pts = int(_num(det.get("points")) or 0)
        if pts:
            lines.append((f"{pts} points scored", pts * r["per_point"]))
        dist = int(_num(det.get("distance_m")) or 0)
        if dist >= 100:
            lines.append((f"{dist} m swum", (dist // 100) * r["per_100m"]))
        if det.get("result") == "Won":
            lines.append(("Match won!", r["win_bonus"]))
        old = bests(kind, history)
        for k, v in metrics(kind, det).items():
            if k in old:
                prev = old[k][0]
                if (v < prev) if k.endswith("_low") else (v > prev):
                    pbs.append(label(k))
        for p in pbs:
            lines.append((f"Personal best: {p}", r["pb_bonus"]))
    elif kind == "maths":
        m = min(minutes, int(r["maths_cap_min"]))
        lines.append((f"{m} min of maths", m * r["maths_per_min"]))
        c, t = _num(det.get("correct")), _num(det.get("total"))
        if c is not None and t:
            pct = c / t
            if pct >= 1:
                lines.append(("100% score!", r["maths_100_bonus"]))
            elif pct >= 0.8:
                lines.append(("80%+ score", r["maths_80_bonus"]))
    elif kind == "writing":
        lines.append(("Finished a piece of writing", r["writing_base"]))
        w = min(int(_num(det.get("words")) or 0), int(r["writing_cap_words"]))
        if w >= 50:
            lines.append((f"{w} words", (w // 50) * r["writing_per_50_words"]))
    if effort == 5:
        lines.append(("Gave it 100% effort", r["effort5_bonus"]))
    elif effort == 4:
        lines.append(("Big effort", r["effort4_bonus"]))
    lines = [(t, int(x)) for t, x in lines if x]
    return sum(x for _, x in lines), lines, pbs


# ---------------------------------------------------------------- streak & weekly goals
def streak(activities: list[dict]) -> dict:
    days = sorted({to_date(a.get("day")) for a in activities if a.get("status") != "rejected"} - {None})
    best = run = 0
    prev = None
    for d in days:
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    cur = 0
    if days and (today() - days[-1]).days <= 1:
        s = set(days)
        d = days[-1]
        while d in s:
            cur += 1
            d -= timedelta(days=1)
    return {"current": cur, "best": best, "days": len(days)}


def week_progress(activities: list[dict], goals: dict, wk: date | None = None,
                  approved_only: bool = False) -> dict:
    """{kind: {"done": n, "goal": g, "pct": p, "unit": "min"|"pieces"}} for one week."""
    wk = wk or week_start()
    end = wk + timedelta(days=7)
    out = {}
    for kind, goal in goals.items():
        done = 0
        for a in activities:
            d = to_date(a.get("day"))
            if a.get("kind") != kind or not d or not (wk <= d < end):
                continue
            if a.get("status") == "rejected" or (approved_only and a.get("status") != "approved"):
                continue
            done += 1 if kind == "writing" else int(a.get("minutes") or 0)
        goal = int(goal or 0)
        out[kind] = {"done": done, "goal": goal, "pct": (done / goal) if goal else 0,
                     "unit": "pieces" if kind == "writing" else "min"}
    return out


# ---------------------------------------------------------------- badges
BADGES = [
    ("first_bounce", "🏀", "First Bounce", "Log your first basketball session"),
    ("first_serve", "🎾", "First Serve", "Log your first tennis session"),
    ("first_splash", "🏊", "First Splash", "Log your first swim"),
    ("triple_threat", "🔱", "Triple Threat", "Basketball, tennis AND swimming in one week"),
    ("streak3", "🔥", "On Fire", "Active 3 days in a row"),
    ("streak7", "🌋", "Volcano", "Active 7 days in a row"),
    ("streak14", "☄️", "Unstoppable", "Active 14 days in a row"),
    ("sharpshooter", "🎯", "Sharpshooter", "10+ free throws made in one session"),
    ("ten_points", "🔟", "Double Digits", "Score 10+ points in a basketball game"),
    ("match_winner", "🏆", "Match Winner", "Win a tennis match"),
    ("rally20", "🔁", "Rally Machine", "A 20-shot rally"),
    ("km_fish", "🐟", "Kilometre Fish", "Swim 1,000 m in one session"),
    ("pb_hunter", "📈", "PB Hunter", "Beat 5 personal bests"),
    ("sport_10h", "⏱️", "10-Hour Hero", "10 hours of sport in total"),
    ("maths_ace", "🧮", "Maths Ace", "Get 100% on a maths practice"),
    ("writer_1000", "📜", "Word Wizard", "Write 1,000 words in total"),
    ("first_reward", "🎁", "Treat Yourself", "Swap XP for your first reward"),
    ("saver", "🏦", "Banana Bank", "Save up 1,000 XP without spending"),
    ("goal_week", "✅", "Goal Getter", "Hit every weekly goal in one week"),
]
BADGE_MAP = {k: (ic, name, desc) for k, ic, name, desc in BADGES}


def earned_badges(ctx: dict) -> list[str]:
    acts = [a for a in ctx["activities"] if a.get("status") == "approved"]
    got = []
    kinds = {a["kind"] for a in acts}
    if "basketball" in kinds:
        got.append("first_bounce")
    if "tennis" in kinds:
        got.append("first_serve")
    if "swimming" in kinds:
        got.append("first_splash")
    weeks = {}
    for a in acts:
        d = to_date(a.get("day"))
        if d and a["kind"] in SPORTS:
            weeks.setdefault(week_start(d), set()).add(a["kind"])
    if any(len(v) == 3 for v in weeks.values()):
        got.append("triple_threat")
    s = streak(acts)
    for n, k in ((3, "streak3"), (7, "streak7"), (14, "streak14")):
        if s["best"] >= n:
            got.append(k)
    det = lambda a, k: _num((a.get("details") or {}).get(k)) or 0  # noqa: E731
    if any(det(a, "ft_made") >= 10 for a in acts):
        got.append("sharpshooter")
    if any(a["kind"] == "basketball" and det(a, "points") >= 10 for a in acts):
        got.append("ten_points")
    if any((a.get("details") or {}).get("result") == "Won" for a in acts):
        got.append("match_winner")
    if any(det(a, "longest_rally") >= 20 for a in acts):
        got.append("rally20")
    if any(det(a, "distance_m") >= 1000 for a in acts):
        got.append("km_fish")
    if sum(len((a.get("details") or {}).get("pbs") or []) for a in acts) >= 5:
        got.append("pb_hunter")
    if sum(int(a.get("minutes") or 0) for a in acts if a["kind"] in SPORTS) >= 600:
        got.append("sport_10h")
    if any(a["kind"] == "maths" and det(a, "total") and det(a, "correct") >= det(a, "total") for a in acts):
        got.append("maths_ace")
    if sum(det(a, "words") for a in acts if a["kind"] == "writing") >= 1000:
        got.append("writer_1000")
    if any(r.get("kind") == "reward" and r.get("status") in ("requested", "delivered") for r in ctx["redemptions"]):
        got.append("first_reward")
    if ctx.get("balance", 0) >= 1000:
        got.append("saver")
    if ctx.get("all_goals_week"):
        got.append("goal_week")
    return got

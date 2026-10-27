"""Daily routine: short focused Maths and English sessions with a built-in timer.

- The routine itself (which sessions, how long, which days, rough time) lives in the family settings
  (``ar_settings.data["routine"]``), so Papa edits it in Parent Hub and no extra table is needed for it.
- A running timer is a row in ``ar_routine_runs`` (supabase/002_routine.sql), so it survives a reload or a
  phone going to sleep. Without that table the timer still works, but only in the open browser tab.
- Finishing a session writes a normal, already-approved activity (kind ``maths`` or ``english``), so it
  counts for the streak, the weekly maths goal, screen-time unlock and the Trophy Room charts. XP lands
  straight away; Papa can take it back in Parent Hub → 🗓️ Routine.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import streamlit as st

from . import data, gamify as g
from .store import now_iso

SQL_FILE = "supabase/002_routine.sql"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SUBJECTS = {"maths": ("🔢", "Maths"), "english": ("📖", "English")}
TOPICS = {
    "maths": ["Times tables", "Mental maths", "Fractions & decimals", "Problem solving", "Measurement & geometry",
              "Homework", "Maths app / workbook", "Other"],
    "english": ["Reading", "Spelling", "Grammar & punctuation", "Comprehension", "Vocabulary", "Writing",
                "Homework", "Other"],
}
MIN_EARLY = 5          # a session stopped early still counts if it lasted at least this many minutes

DEFAULT_ROUTINE = [
    {"id": "maths", "kind": "maths", "title": "Maths", "minutes": 25, "time": "16:30", "days": [0, 1, 2, 3, 4, 5, 6]},
    {"id": "english", "kind": "english", "title": "English", "minutes": 25, "time": "17:00",
     "days": [0, 1, 2, 3, 4, 5, 6]},
]


# ---------------------------------------------------------------- plan
def blocks(sett: dict | None = None) -> list[dict]:
    sett = sett or data.settings()
    rows = sett.get("routine")
    if rows is None:
        rows = DEFAULT_ROUTINE
    out = []
    for b in rows:
        if b.get("kind") not in SUBJECTS:
            continue
        out.append({"id": str(b.get("id") or uuid.uuid4().hex[:8]), "kind": b["kind"],
                    "title": str(b.get("title") or SUBJECTS[b["kind"]][1]),
                    "minutes": max(5, int(b.get("minutes") or 25)), "time": str(b.get("time") or ""),
                    "days": sorted({int(d) for d in (b.get("days") or []) if 0 <= int(d) <= 6})})
    return sorted(out, key=lambda b: (b["time"] or "99", b["title"]))


def save_blocks(rows: list[dict]):
    data.save_settings({"routine": rows})


def day_blocks(day: date, bl=None) -> list[dict]:
    return [b for b in (bl if bl is not None else blocks()) if day.weekday() in b["days"]]


def time_label(t: str) -> str:
    if not t:
        return "any time"
    h, m = (int(x) for x in t[:5].split(":"))
    suf = "am" if h < 12 else "pm"
    return f"{h % 12 or 12}:{m:02d}{suf}" if m else f"{h % 12 or 12}{suf}"


def xp_for(kind: str, minutes: int, rules: dict | None = None) -> int:
    r = {**g.DEFAULT_RULES, **(rules or data.settings()["rules"])}
    if kind == "maths":
        return min(int(minutes), int(r["maths_cap_min"])) * int(r["maths_per_min"])
    return min(int(minutes), int(r["english_cap_min"])) * int(r["english_per_min"])


# ---------------------------------------------------------------- sessions done (activities)
def sessions(uid=None, start: date | None = None, end: date | None = None) -> list[dict]:
    out = []
    for a in data.activities(uid):
        det = a.get("details") or {}
        if not det.get("routine_block") or a.get("status") == "rejected":
            continue
        d = g.to_date(a.get("day"))
        if (start and d < start) or (end and d > end):
            continue
        out.append(a)
    return out


def done_map(uid=None, start=None, end=None) -> dict:
    """{(block_id, 'YYYY-MM-DD'): activity} – full sessions win over early stops."""
    out = {}
    for a in sessions(uid, start, end):
        key = (a["details"]["routine_block"], str(a["day"])[:10])
        if key not in out or (a["details"].get("full") and not out[key]["details"].get("full")):
            out[key] = a
    return out


def day_complete(day: date, dm: dict, bl) -> bool | None:
    """True when every session planned that day was done in full. None = nothing planned."""
    todays = day_blocks(day, bl)
    if not todays:
        return None
    return all((dm.get((b["id"], str(day))) or {}).get("details", {}).get("full") for b in todays)


# ---------------------------------------------------------------- timer (ar_routine_runs)
def _runs_ok() -> bool:
    if "routine_runs_ok" not in st.session_state:
        try:
            data.store().select("routine_runs", eq={"user_id": data.child()["id"]}, limit=1)
            st.session_state.routine_runs_ok = True
        except Exception:
            st.session_state.routine_runs_ok = False
    return st.session_state.routine_runs_ok


def running(uid=None) -> dict | None:
    uid = uid or data.child()["id"]
    if _runs_ok():
        rows = [r for r in data.store().select("routine_runs", eq={"user_id": uid}) if r.get("status") == "running"]
        rows.sort(key=lambda r: str(r.get("started_at")))
        return rows[-1] if rows else None
    r = st.session_state.get("routine_run_local")
    return r if r and r.get("user_id") == uid else None


def start(b: dict) -> dict:
    now = datetime.now(timezone.utc)
    row = {"user_id": data.me()["id"], "day": str(g.today()), "block_id": b["id"], "kind": b["kind"],
           "title": b["title"], "minutes": int(b["minutes"]), "started_at": now.isoformat(),
           "ends_at": (now + timedelta(minutes=int(b["minutes"]))).isoformat(), "status": "running"}
    if _runs_ok():
        return data.store().insert("routine_runs", row)
    row["id"] = uuid.uuid4().hex
    row["local"] = True
    st.session_state.routine_run_local = row
    return row


def _parse(ts) -> datetime:
    d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def seconds_left(run: dict) -> int:
    return max(0, int((_parse(run["ends_at"]) - datetime.now(timezone.utc)).total_seconds()))


def minutes_done(run: dict) -> int:
    return min(int(run["minutes"]), int((datetime.now(timezone.utc) - _parse(run["started_at"])).total_seconds() // 60))


def _close(run: dict, status: str):
    if not run.get("local"):
        data.store().update("routine_runs", {"id": run["id"]}, {"status": status, "closed_at": now_iso()})
    st.session_state.pop("routine_run_local", None)


def cancel(run: dict):
    _close(run, "cancelled")


def finish(run: dict, topic: str = "", note: str = "", early_reason: str = "") -> list[str]:
    """Write the session as an approved activity, pay XP and any routine bonus. Returns messages."""
    full = seconds_left(run) == 0 and not early_reason
    mins = int(run["minutes"]) if full else minutes_done(run)
    if not full and mins < MIN_EARLY:
        _close(run, "cancelled")
        return [f"Only {mins} min, so it didn't count. Try again when you're ready!"]
    sett = data.settings()
    kind = run["kind"]
    xp = xp_for(kind, mins, sett["rules"])
    det = {"routine_block": run["block_id"], "full": full, "topic": topic, "routine_minutes": int(run["minutes"]),
           "early_reason": early_reason or None, "xp_lines": [[f"{mins} min of {SUBJECTS[kind][1].lower()}", xp]]}
    act = data.store().insert("activities", {
        "user_id": run["user_id"], "day": str(run["day"]), "area": "maths" if kind == "maths" else "writing",
        "kind": kind, "session_type": "Daily routine" + ("" if full else " (stopped early)"), "minutes": mins,
        "effort": 0, "details": det, "note": note.strip(), "xp": xp, "status": "approved", "reviewed_at": now_iso()})
    icon, name = SUBJECTS[kind]
    data.add_xp(run["user_id"], xp, f"{icon} {name} routine: {mins} min" + ("" if full else " (stopped early)"),
                act["id"])
    _close(run, "done")
    msgs = [f"+{xp} XP · {name}"]
    msgs += check_bonuses(run["user_id"], g.to_date(run["day"]), sett)
    data.weekly_bonuses(run["user_id"], g.to_date(run["day"]))
    data.award_badges(run["user_id"])
    return msgs


# ---------------------------------------------------------------- bonuses
def _net(uid, source_id) -> int:
    ev = [e for e in data.xp_events(uid) if e.get("source_id") in (source_id, source_id + ":back")]
    return sum(1 if e["source_id"] == source_id else -1 for e in ev)


def check_bonuses(uid, day: date, sett=None) -> list[str]:
    sett = sett or data.settings()
    r, bl = sett["rules"], blocks(sett)
    ws = g.week_start(day)
    dm = done_map(uid, ws, ws + timedelta(days=6))
    msgs = []
    key = f"routine:day:{day}"
    if day_complete(day, dm, bl) and int(r["routine_day_bonus"]) and _net(uid, key) <= 0:
        data.add_xp(uid, int(r["routine_day_bonus"]), "🗓️ Whole routine done today!", key)
        msgs.append(f"+{r['routine_day_bonus']} XP · whole routine done today 🌟")
    week = [day_complete(ws + timedelta(days=i), dm, bl) for i in range(7)]
    key = f"routine:week:{ws}"
    if any(w is not None for w in week) and all(w in (True, None) for w in week) and int(r["routine_week_bonus"]) \
            and _net(uid, key) <= 0:
        data.add_xp(uid, int(r["routine_week_bonus"]), "🏆 Every routine session this week!", key)
        msgs.append(f"+{r['routine_week_bonus']} XP · the WHOLE week 🏆")
    return msgs


def take_back(act: dict, note: str = ""):
    """Papa: that session didn't really happen. XP comes off, and any routine bonus that no longer holds."""
    uid = act["user_id"]
    data.store().update("activities", {"id": act["id"]}, {"status": "rejected", "parent_note": note.strip(),
                                                         "reviewed_at": now_iso()})
    data.add_xp(uid, -int(act.get("xp") or 0), f"↩️ Taken back: {SUBJECTS[act['kind']][1]} routine", act["id"] + ":back")
    day = g.to_date(act["day"])
    sett = data.settings()
    bl = blocks(sett)
    ws = g.week_start(day)
    dm = done_map(uid, ws, ws + timedelta(days=6))
    for key, ok, amt in ((f"routine:day:{day}", day_complete(day, dm, bl), sett["rules"]["routine_day_bonus"]),
                         (f"routine:week:{ws}", all(day_complete(ws + timedelta(days=i), dm, bl) in (True, None)
                                                    for i in range(7)), sett["rules"]["routine_week_bonus"])):
        if not ok and _net(uid, key) > 0:
            paid = next((int(e["amount"]) for e in data.xp_events(uid)[::-1] if e.get("source_id") == key), int(amt))
            data.add_xp(uid, -paid, "↩️ Routine bonus taken back", key + ":back")


# ---------------------------------------------------------------- summaries
def week_summary(uid, ws: date, sett=None) -> dict:
    sett = sett or data.settings()
    bl = blocks(sett)
    dm = done_map(uid, ws, ws + timedelta(days=6))
    planned = [(b, ws + timedelta(days=i)) for i in range(7) for b in day_blocks(ws + timedelta(days=i), bl)]
    full = sum(1 for b, d in planned if (dm.get((b["id"], str(d))) or {}).get("details", {}).get("full"))
    xp = sum(int(a.get("xp") or 0) for a in dm.values())
    days_full = sum(1 for i in range(7) if day_complete(ws + timedelta(days=i), dm, bl))
    pot = sum(xp_for(b["kind"], b["minutes"], sett["rules"]) for b, _ in planned) \
        + sum(1 for i in range(7) if day_blocks(ws + timedelta(days=i), bl)) * int(sett["rules"]["routine_day_bonus"]) \
        + (int(sett["rules"]["routine_week_bonus"]) if planned else 0)
    return {"planned": len(planned), "full": full, "xp": xp, "days_full": days_full, "map": dm, "blocks": bl,
            "potential": pot}


def badge_ctx(uid, acts) -> dict:
    """For badges: full sessions, best run of complete routine days, full weeks."""
    full = [a for a in acts if (a.get("details") or {}).get("routine_block") and a.get("status") == "approved"
            and a["details"].get("full")]
    if not full:
        return {"routine_full": 0, "routine_best_run": 0, "routine_weeks": 0}
    bl = blocks()
    dm = {}
    for a in full:
        dm[(a["details"]["routine_block"], str(a["day"])[:10])] = a
    first = min(g.to_date(a["day"]) for a in full)
    run = best = 0
    d = first
    while d <= g.today():
        c = day_complete(d, dm, bl)
        if c:
            run += 1
            best = max(best, run)
        elif c is False:
            run = 0
        d += timedelta(days=1)
    weeks = sum(1 for e in data.xp_events(uid) if str(e.get("source_id") or "").startswith("routine:week:")
                and not str(e["source_id"]).endswith(":back"))
    return {"routine_full": len(full), "routine_best_run": best, "routine_weeks": weeks}

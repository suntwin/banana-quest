"""High-level data helpers used by the views."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import streamlit as st

from . import gamify as g
from .store import get_store, now_iso

SPENT_STATUSES = {"requested", "delivered", "ready", "running", "used"}


def store():
    return get_store()


def me() -> dict:
    return st.session_state["profile"]


def is_child() -> bool:
    return me()["role"] == "child"


def child() -> dict:
    """The kid whose data we show. For a parent: the family's child."""
    p = me()
    if p["role"] == "child":
        return p
    kids = [r for r in store().select("profiles", eq={"family_id": p["family_id"]}) if r["role"] == "child"]
    return kids[0] if kids else p


def fresh_child() -> dict:
    rows = store().select("profiles", eq={"id": child()["id"]})
    return rows[0] if rows else child()


# ---------------------------------------------------------------- settings
def settings() -> dict:
    rows = store().select("settings", eq={"family_id": me()["family_id"]})
    return g.merged_settings(rows[0].get("data") if rows else None)


def save_settings(s: dict):
    store().upsert("settings", {"family_id": me()["family_id"], "data": s, "updated_at": now_iso()},
                   on_conflict="family_id")


# ---------------------------------------------------------------- reads
def activities(uid=None):
    return store().select("activities", eq={"user_id": uid or child()["id"]}, order="created_at")


def xp_events(uid=None):
    return store().select("xp_events", eq={"user_id": uid or child()["id"]}, order="created_at")


def redemptions(uid=None):
    return store().select("redemptions", eq={"user_id": uid or child()["id"]}, order="created_at", desc=True)


def rewards(active_only=True):
    rows = store().select("rewards", eq={"family_id": me()["family_id"]}, order="cost")
    rows.sort(key=lambda r: int(r.get("cost") or 0))
    return [r for r in rows if r.get("active", True)] if active_only else rows


def badges(uid=None):
    return {b["badge_key"]: b for b in store().select("badges", eq={"user_id": uid or child()["id"]})}


def wallet(uid=None) -> dict:
    uid = uid or child()["id"]
    earned = sum(int(e["amount"]) for e in xp_events(uid))
    reds = redemptions(uid)
    spent = sum(int(r.get("cost") or 0) for r in reds if r.get("status") in SPENT_STATUSES)
    pending = sum(int(a.get("xp") or 0) for a in activities(uid) if a.get("status") == "pending")
    return {"earned": earned, "spent": spent, "balance": earned - spent, "pending": pending}


def stats(uid=None) -> dict:
    uid = uid or child()["id"]
    acts = activities(uid)
    w = wallet(uid)
    return {"activities": acts, "wallet": w, "level": g.level_for(w["earned"]),
            "streak": g.streak(acts)}


# ---------------------------------------------------------------- XP writes
def add_xp(uid, amount: int, reason: str, source_id: str | None = None):
    if not amount:
        return
    store().insert("xp_events", {"user_id": uid, "amount": int(amount), "reason": reason,
                                 "source_id": source_id})
    if is_child():
        st.session_state.setdefault("xp_toasts", []).append((int(amount), reason))


def log_activity(kind, day, session_type, minutes, effort, details, note) -> dict:
    kid = child()
    sett = settings()
    history = activities(kid["id"])
    xp, lines, pbs = g.calc_xp(kind, session_type, minutes, effort, details, history, sett["rules"])
    det = dict(details or {})
    det["xp_lines"] = lines
    det["pbs"] = pbs
    row = store().insert("activities", {
        "user_id": kid["id"], "day": str(day), "area": g.KINDS[kind]["area"], "kind": kind,
        "session_type": session_type, "minutes": int(minutes or 0), "effort": int(effort or 0),
        "details": det, "note": note, "xp": xp, "status": "pending"})
    if sett.get("approval") == "auto":
        approve(row, xp)
    return row


def approve(act: dict, xp: int | None = None, stars: int = 0, parent_note: str = ""):
    sett = settings()
    xp = int(act.get("xp") or 0) if xp is None else int(xp)
    det = dict(act.get("details") or {})
    if stars:
        det["stars"] = int(stars)
        xp += int(stars) * int(sett["rules"]["writing_star"])
    store().update("activities", {"id": act["id"]}, {
        "status": "approved", "xp": xp, "details": det, "parent_note": parent_note,
        "reviewed_at": now_iso()})
    name = g.KINDS[act["kind"]]["name"]
    add_xp(act["user_id"], xp, f"{g.KINDS[act['kind']]['icon']} {name}: {act.get('session_type') or 'session'}",
           act["id"])
    act.update({"status": "approved", "xp": xp, "details": det})
    weekly_bonuses(act["user_id"], g.to_date(act.get("day")))
    award_badges(act["user_id"])


def reject(act: dict, parent_note: str = ""):
    store().update("activities", {"id": act["id"]}, {"status": "rejected", "parent_note": parent_note,
                                                     "reviewed_at": now_iso()})


def weekly_bonuses(uid, day=None):
    """Award each weekly goal bonus once (deduped by source_id)."""
    sett = settings()
    wk = g.week_start(day or g.today())
    acts = activities(uid)
    prog = g.week_progress(acts, sett["goals"], wk, approved_only=True)
    have = {e.get("source_id") for e in xp_events(uid)}
    bonus = int(sett["rules"]["weekly_goal_bonus"])
    for kind, p in prog.items():
        key = f"week:{wk}:{kind}"
        if p["goal"] and p["done"] >= p["goal"] and key not in have:
            add_xp(uid, bonus, f"🎯 Weekly goal smashed: {g.KINDS[kind]['name']}", key)
    sports_done = all(prog[k]["goal"] and prog[k]["done"] >= prog[k]["goal"] for k in g.SPORTS if k in prog)
    key = f"week:{wk}:triple"
    if sports_done and key not in have:
        add_xp(uid, int(sett["rules"]["triple_threat_bonus"]), "🔱 All three sports goals this week!", key)


def manual_bonus(amount: int, reason: str):
    kid = child()
    add_xp(kid["id"], int(amount), f"🎉 Bonus from {me()['display_name']}: {reason}")
    award_badges(kid["id"])


def award_badges(uid) -> list[str]:
    acts = activities(uid)
    sett = settings()
    w = wallet(uid)
    weeks = {g.week_start(g.to_date(a["day"])) for a in acts if a.get("status") == "approved" and a.get("day")}
    all_goals = any(all(p["goal"] == 0 or p["done"] >= p["goal"]
                        for p in g.week_progress(acts, sett["goals"], wk, approved_only=True).values())
                    for wk in weeks)
    ctx = {"activities": acts, "redemptions": redemptions(uid), "balance": w["balance"],
           "all_goals_week": all_goals}
    have = badges(uid)
    new = [k for k in g.earned_badges(ctx) if k not in have]
    for k in new:
        store().upsert("badges", {"user_id": uid, "badge_key": k, "earned_at": now_iso(), "seen": False},
                       on_conflict="user_id,badge_key")
    return new


def unseen_badges() -> list[str]:
    return [k for k, b in badges().items() if not b.get("seen")]


def mark_badges_seen(keys):
    for k in keys:
        store().update("badges", {"user_id": me()["id"], "badge_key": k}, {"seen": True})


# ---------------------------------------------------------------- rewards shop
def set_goal(reward_id):
    store().update("profiles", {"id": me()["id"]}, {"goal_reward_id": reward_id})
    st.session_state.profile["goal_reward_id"] = reward_id


def redeem_reward(r: dict) -> str | None:
    w = wallet()
    if w["balance"] < int(r["cost"]):
        return "Not enough XP yet. Keep going!"
    store().insert("redemptions", {"user_id": me()["id"], "kind": "reward", "reward_id": r["id"],
                                   "title": f"{r.get('emoji', '🎁')} {r['name']}", "cost": int(r["cost"]),
                                   "day": str(g.today()), "status": "requested"})
    award_badges(me()["id"])
    return None


def deliver(red: dict):
    store().update("redemptions", {"id": red["id"]}, {"status": "delivered", "closed_at": now_iso()})


def refund(red: dict, why="declined"):
    """Decline a reward request / cancel a screen ticket. XP comes back automatically."""
    store().update("redemptions", {"id": red["id"]}, {"status": "rejected" if why == "declined" else "cancelled",
                                                      "closed_at": now_iso()})


def save_reward(r: dict):
    r = dict(r)
    r["family_id"] = me()["family_id"]
    if r.get("id"):
        store().update("rewards", {"id": r["id"]}, {k: v for k, v in r.items() if k != "id"})
    else:
        r.pop("id", None)
        store().insert("rewards", r)


# ---------------------------------------------------------------- screen time
def screen_tickets(uid=None):
    return [r for r in redemptions(uid) if r.get("kind") == "screen"]


def _ends(t) -> datetime | None:
    if not t.get("started_at"):
        return None
    st_ = datetime.fromisoformat(str(t["started_at"]).replace("Z", "+00:00"))
    if st_.tzinfo is None:
        st_ = st_.replace(tzinfo=timezone.utc)
    return st_ + timedelta(minutes=int(t.get("minutes") or 0))


def refresh_tickets(uid=None) -> list[dict]:
    """Close running tickets whose time is up; return all screen tickets."""
    out = []
    for t in screen_tickets(uid):
        end = _ends(t)
        if t.get("status") == "ready" and str(t.get("day")) < str(g.today()):
            # unused ticket from an earlier day: refund it automatically
            store().update("redemptions", {"id": t["id"]}, {"status": "cancelled", "closed_at": now_iso()})
            t["status"] = "cancelled"
        if t.get("status") == "running" and end and datetime.now(timezone.utc) >= end:
            store().update("redemptions", {"id": t["id"]}, {"status": "used", "closed_at": end.isoformat()})
            t["status"] = "used"
        out.append(t)
    return out


def seconds_left(t) -> int:
    end = _ends(t)
    return max(0, int((end - datetime.now(timezone.utc)).total_seconds())) if end else int(t.get("minutes", 0)) * 60


def screen_today(uid=None) -> dict:
    sett = settings()["screen"]
    t = str(g.today())
    tickets = [x for x in refresh_tickets(uid) if str(x.get("day")) == t and x.get("status") in SPENT_STATUSES]
    bought = sum(int(x.get("minutes") or 0) for x in tickets)
    cap = int(sett["cap_weekend"] if g.is_weekend() else sett["cap_weekday"])
    active_today = any(str(a.get("day")) == t and a.get("status") != "rejected" for a in activities(uid))
    return {"bought": bought, "cap": cap, "left": max(0, cap - bought), "tickets": tickets,
            "active_today": active_today, "rate": int(sett["xp_per_min"]),
            "need_activity": bool(sett.get("need_activity", True)), "options": sett.get("options") or [15, 30, 45, 60]}

def buy_screen(minutes: int) -> str | None:
    s = screen_today()
    cost = int(minutes) * s["rate"]
    if s["need_activity"] and not s["active_today"]:
        return "Log some sport, maths or writing today first, then screen time unlocks!"
    if minutes > s["left"]:
        return f"Today's limit is {s['cap']} min and you have {s['left']} min left."
    if wallet()["balance"] < cost:
        return "Not enough XP for that one yet."
    store().insert("redemptions", {"user_id": me()["id"], "kind": "screen", "title": f"📺 {minutes} min screen time",
                                   "minutes": int(minutes), "cost": cost, "day": str(g.today()), "status": "ready"})
    return None


def start_ticket(t: dict):
    store().update("redemptions", {"id": t["id"]}, {"status": "running", "started_at": now_iso()})


def stop_ticket(t: dict):
    """Finish early. Unused whole minutes go back as a new ready ticket for today."""
    left_min = seconds_left(t) // 60
    used = int(t.get("minutes") or 0) - left_min
    store().update("redemptions", {"id": t["id"]}, {
        "status": "used", "closed_at": now_iso(), "minutes": used,
        "cost": used * int(round(int(t["cost"]) / max(1, int(t["minutes"]))))})
    if left_min > 0:
        rate = int(round(int(t["cost"]) / max(1, int(t["minutes"]))))
        store().insert("redemptions", {"user_id": t["user_id"], "kind": "screen",
                                       "title": f"📺 {left_min} min screen time (saved)", "minutes": left_min,
                                       "cost": left_min * rate, "day": str(t.get("day")), "status": "ready"})


# ---------------------------------------------------------------- parent tools
def reset_child_data():
    uid = child()["id"]
    for t in ("activities", "xp_events", "redemptions", "badges"):
        store().delete(t, {"user_id": uid})

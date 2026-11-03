"""Banana Words: Aadiv's daily vocabulary trainer (same engine as Selective Brain's Word Power, sized for Year 2-4).

Tables (supabase/003_vocab.sql, all prefixed ar_ by the store):
  vocab_words     the family's word bank (Parent Hub -> 🔤 Words loads vocab/vocab_bank_aadiv_*.json)
  vocab_progress  one row per word he has started: stage, next_due, correct/wrong, lapses, tricky
  vocab_reviews   one row per answer
Finishing today's words also writes an approved activity (kind 'words'), so it counts for his streak
and unlocks screen time like any other activity.

Stages: 1 meaning (next day) -> 2 pick the word (3 days) -> 3 fill the gap (7) -> 4 same/opposite (14)
        -> 5 spell it (30) -> 6 mastered (60, then 90). Wrong answer: back to stage 1. 3 slips = tricky word.
"""
from __future__ import annotations

import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

from . import data, gamify as g
from .store import now_iso

SQL_FILE = "supabase/003_vocab.sql"
BANK_DIR = Path(__file__).resolve().parent.parent / "vocab"

DEFAULT_NEW_PER_DAY = 5
GAP = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30, 6: 60}
MASTERED_GAP = 90
STAGE_MODE = {1: "meaning", 2: "reverse", 3: "sentence", 4: "synonym", 5: "spell"}
STAGE_LABEL = {1: "🌱 Just met", 2: "🌿 Growing", 3: "🌳 Getting there", 4: "💪 Strong", 5: "✍️ Spelling",
               6: "🏅 Mastered"}
MODE_LABEL = {"meaning": "What does it mean?", "reverse": "Which word is it?", "sentence": "Fill the gap",
              "synonym": "Means the same", "opposite": "The opposite", "spell": "Spell it"}
LEVEL_LABEL = {1: "Year 2", 2: "Year 3", 3: "Year 4 stretch"}
LEECH_LAPSES = 3
TEST_SIZE = 10

XP = {"new": 2, "review": 1, "spell": 2, "practice": 1, "day": 10, "test": 15}
ICON = "🔤"
DONE_KIND = "words"


class NotReady(Exception):
    """The vocab tables don't exist yet (003_vocab.sql not run)."""


def _safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        raise NotReady(str(e)) from e


def _today() -> date:
    return g.today()


def _d(x) -> date | None:
    if not x:
        return None
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def _xp(amount: int, reason: str, source_id: str | None = None):
    data.add_xp(data.me()["id"], amount, f"{ICON} {reason}", source_id)


# ---------------------------------------------------------------- word bank
def bundled_bank() -> dict | None:
    files = sorted(BANK_DIR.glob("vocab_bank_*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def validate_bank(b: dict) -> list[str]:
    if not isinstance(b, dict) or b.get("kind") != "vocab_bank":
        return ["This isn't a vocab bank file (it needs \"kind\": \"vocab_bank\")."]
    errs, seen = [], set()
    for i, w in enumerate(b.get("words") or [], 1):
        for k in ("id", "word", "definition"):
            if not w.get(k):
                errs.append(f"word {i}: missing '{k}'")
        if w.get("id") in seen:
            errs.append(f"word {i}: duplicate id {w.get('id')}")
        seen.add(w.get("id"))
    if not seen:
        errs.append("no words")
    return errs


def bank_rows(bank: dict, family_id: str) -> list[dict]:
    rows = []
    for n, w in enumerate(bank["words"], 1):
        rows.append({"family_id": family_id, "id": w["id"], "word": w["word"], "pos": w.get("pos"),
                     "definition": w["definition"], "example": w.get("example"),
                     "synonyms": list(w.get("synonyms") or []), "antonyms": list(w.get("antonyms") or []),
                     "hook": w.get("hook") or "", "confusable": w.get("confusable") or "",
                     "level": int(w.get("level") or w.get("priority") or 1), "ord": int(w.get("order") or n),
                     "active": True})
    return rows


def load_bank(bank: dict):
    import streamlit as st
    _safe(data.store().upsert_many, "vocab_words", bank_rows(bank, data.me()["family_id"]),
          on_conflict="family_id,id")
    st.session_state.pop("ar_vocab_cache", None)


def words() -> list[dict]:
    import streamlit as st
    fam = data.me()["family_id"]
    cache = st.session_state.get("ar_vocab_cache")
    if cache and cache[0] == fam:
        return cache[1]
    rows = _safe(data.store().select_all, "vocab_words", eq={"family_id": fam}, order="ord")
    rows = sorted([r for r in rows if r.get("active", True)], key=lambda r: int(r.get("ord") or 0))
    for r in rows:
        for k in ("synonyms", "antonyms"):
            if isinstance(r.get(k), str):
                try:
                    r[k] = json.loads(r[k])
                except Exception:
                    r[k] = []
    if rows:
        st.session_state.ar_vocab_cache = (fam, rows)
    return rows


def word_map() -> dict:
    return {w["id"]: w for w in words()}


# ---------------------------------------------------------------- settings (ar_settings.data.vocab)
def settings() -> dict:
    s = {"new_per_day": DEFAULT_NEW_PER_DAY}
    s.update({k: v for k, v in (data.settings().get("vocab") or {}).items() if k in s})
    return s


def save_settings(new: dict):
    data.save_settings({"vocab": new})


# ---------------------------------------------------------------- progress
def progress(uid=None) -> dict:
    rows = _safe(data.store().select_all, "vocab_progress", eq={"user_id": uid or data.child()["id"]})
    return {r["word_id"]: r for r in rows}


def reviews(uid=None, days: int = 60) -> list[dict]:
    since = str(_today() - timedelta(days=days))
    return _safe(data.store().select_all, "vocab_reviews", eq={"user_id": uid or data.child()["id"]},
                 gte={"day": since})


def due_ids(prog: dict) -> list[str]:
    t = _today()
    due = [p for p in prog.values() if _d(p.get("next_due")) and _d(p["next_due"]) <= t]
    due.sort(key=lambda p: (str(p.get("next_due")), int(p.get("stage") or 1)))
    return [p["word_id"] for p in due]


def new_allowance(prog: dict, n_due: int, per_day: int) -> int:
    """Fewer new words when reviews pile up, so a session stays short."""
    if n_due > 40:
        base = min(per_day, 2)
    elif n_due > 25:
        base = min(per_day, 3)
    else:
        base = per_day
    started_today = sum(1 for p in prog.values() if _d(p.get("introduced_on")) == _today())
    return max(0, base - started_today)


def plan_today(uid=None) -> dict:
    prog = progress(uid)
    due = due_ids(prog)
    per_day = int(settings()["new_per_day"])
    allow = new_allowance(prog, len(due), per_day)
    started_today = sum(1 for p in prog.values() if _d(p.get("introduced_on")) == _today())
    new = [w["id"] for w in words() if w["id"] not in prog][:allow]
    return {"due": due, "new": new, "allow": allow, "per_day": per_day, "started_today": started_today,
            "prog": prog}


# ---------------------------------------------------------------- questions
def _seed(*parts) -> random.Random:
    return random.Random("|".join(str(p) for p in parts))


def _first_syn(w) -> str | None:
    syn = [s for s in (w.get("synonyms") or []) if s and s.lower() != w["word"].lower()]
    one = [s for s in syn if " " not in s]
    return (one or syn or [None])[0]


def _pool(w: dict, wm: dict) -> list[dict]:
    same = [x for x in wm.values() if x["id"] != w["id"] and x.get("pos") == w.get("pos")]
    return same if len(same) >= 6 else [x for x in wm.values() if x["id"] != w["id"]]


def blank_sentence(w: dict) -> str | None:
    ex = w.get("example") or ""
    pat = re.compile(r"\b" + re.escape(w["word"]) + r"\b", re.I)
    if not pat.search(ex):
        return None
    return pat.sub("_____", ex, count=1)


def make_question(w: dict, mode: str, wm: dict, salt="") -> dict:
    r = _seed(w["id"], mode, _today(), salt)
    pool = _pool(w, wm)
    r.shuffle(pool)
    if mode == "sentence" and not blank_sentence(w):
        mode = "reverse"
    if mode in ("synonym", "opposite"):
        if mode == "opposite" and not [a for a in (w.get("antonyms") or []) if a]:
            mode = "synonym"
        if mode == "synonym" and not _first_syn(w):
            mode = "reverse"
    if mode == "spell":
        word = w["word"]
        return {"mode": mode, "prompt": w["definition"], "sentence": blank_sentence(w), "answer_text": word,
                "hint": f"{word[0].upper()} {' '.join(['_'] * (len(word) - 1))}  ({len(word)} letters)"}
    if mode == "meaning":
        right, wrong = w["definition"], []
        for x in pool:
            if x["definition"] != right and x["definition"] not in wrong:
                wrong.append(x["definition"])
            if len(wrong) == 2:
                break
        prompt = f"What does **{w['word'].lower()}** mean?"
    elif mode in ("reverse", "sentence"):
        right, wrong = w["word"].lower(), []
        for x in pool:
            if x["word"].lower() != right and x["word"].lower() not in wrong:
                wrong.append(x["word"].lower())
            if len(wrong) == 2:
                break
        prompt = (f"Which word means: *{w['definition']}*?" if mode == "reverse"
                  else f"Which word fills the gap?\n\n> {blank_sentence(w)}")
    elif mode == "synonym":
        right = _first_syn(w)
        avoid = {s.lower() for s in (w.get("synonyms") or []) + (w.get("antonyms") or [])} | {w["word"].lower()}
        wrong = []
        for x in pool:
            s = _first_syn(x)
            if s and s.lower() not in avoid and s not in wrong:
                wrong.append(s)
            if len(wrong) == 2:
                break
        prompt = f"Which word **means the same** as **{w['word'].lower()}**?"
    else:
        right = [a for a in w["antonyms"] if a][0]
        wrong = [s for s in (w.get("synonyms") or [])[:1]]
        avoid = {a.lower() for a in w["antonyms"]} | {w["word"].lower()} | {s.lower() for s in wrong}
        for x in pool:
            s = _first_syn(x)
            if s and s.lower() not in avoid and s not in wrong:
                wrong.append(s)
            if len(wrong) == 2:
                break
        prompt = f"Which is the **opposite** of **{w['word'].lower()}**?"
    opts = [right] + wrong[:2]              # 3 choices: easier to read for a 7-year-old
    r.shuffle(opts)
    return {"mode": mode, "prompt": prompt, "options": opts, "answer": opts.index(right)}


def mode_for(p: dict | None, w: dict, salt="") -> str:
    stage = int((p or {}).get("stage") or 1)
    if stage >= 6:
        return _seed(w["id"], "mastered", _today(), salt).choice(["reverse", "sentence", "synonym", "spell"])
    mode = STAGE_MODE.get(stage, "meaning")
    if mode == "synonym" and (w.get("antonyms") or []) and _seed(w["id"], "opp", _today()).random() < 0.4:
        mode = "opposite"
    return mode


def check_spelling(given: str, word: str) -> tuple[bool, bool]:
    a, b = (given or "").strip().lower(), word.strip().lower()
    if a == b:
        return True, False
    return False, _lev(a, b) <= 1


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------- writes
def _log(word_id: str, mode: str, correct: bool):
    data.store().insert("vocab_reviews", {"user_id": data.me()["id"], "word_id": word_id, "mode": mode,
                                          "correct": bool(correct), "day": str(_today())})


def introduce(word_id: str, correct: bool) -> dict:
    row = {"user_id": data.me()["id"], "word_id": word_id, "stage": 1,
           "next_due": str(_today() + timedelta(days=GAP[1])), "introduced_on": str(_today()),
           "correct": int(bool(correct)), "wrong": int(not correct), "lapses": 0, "leech": False,
           "last_seen": now_iso()}
    _safe(data.store().upsert, "vocab_progress", row, on_conflict="user_id,word_id")
    _log(word_id, "learn", correct)
    if correct:
        _xp(XP["new"], "Words: learned a new word")
    return row


def answer(p: dict, mode: str, correct: bool, test=False) -> dict:
    stage = int(p.get("stage") or 1)
    f = {"last_seen": now_iso(), "correct": int(p.get("correct") or 0) + int(bool(correct)),
         "wrong": int(p.get("wrong") or 0) + int(not correct)}
    if correct and not test:
        if stage >= 6:
            f.update({"stage": 6, "next_due": str(_today() + timedelta(days=MASTERED_GAP))})
        else:
            f.update({"stage": stage + 1, "next_due": str(_today() + timedelta(days=GAP[stage + 1]))})
    elif not correct:
        lapses = int(p.get("lapses") or 0) + 1
        f.update({"stage": 1, "next_due": str(_today() + timedelta(days=1)), "lapses": lapses,
                  "leech": lapses >= LEECH_LAPSES})
    _safe(data.store().update, "vocab_progress", {"user_id": p["user_id"], "word_id": p["word_id"]}, f)
    p.update(f)
    _log(p["word_id"], ("test_" if test else "") + mode, correct)
    if correct:
        _xp(XP["spell"] if mode == "spell" else XP["review"],
            "Words: spelled a word" if mode == "spell" else "Words: remembered a word")
    return p


def practice_log(word_id: str, mode: str, correct: bool):
    _log(word_id, "practice_" + mode, correct)
    if correct:
        _xp(XP["practice"], "Words: practice")


def _done_days(uid=None) -> set:
    return {g.to_date(a.get("day")) for a in data.activities(uid)
            if a.get("kind") == DONE_KIND and a.get("status") == "approved"}


def done_today(uid=None) -> bool:
    return _today() in _done_days(uid)


def finish_day(n_new: int = 0, n_due: int = 0, right: int = 0, asked: int = 0):
    """Today's words are done: an approved 'words' activity (streak, screen-time unlock) + the day XP."""
    if done_today():
        return
    kid = data.me()
    row = data.store().insert("activities", {
        "user_id": kid["id"], "day": str(_today()), "area": "writing", "kind": DONE_KIND,
        "session_type": "Today's words", "minutes": max(3, round((n_due * 12 + n_new * 45) / 60)), "effort": 0,
        "details": {"new": n_new, "reviewed": n_due, "right": right, "asked": asked}, "note": "",
        "xp": XP["day"], "status": "approved", "reviewed_at": now_iso()})
    _xp(XP["day"], "Words: today's words done", row.get("id"))
    data.award_badges(kid["id"])


def word_streak(uid=None) -> dict:
    days = _done_days(uid)
    t = _today()
    d = t if t in days else t - timedelta(days=1)
    cur = 0
    while d in days:
        cur += 1
        d -= timedelta(days=1)
    best, run = 0, 0
    if days:
        x, hi = min(days), max(days)
        while x <= hi:
            run = run + 1 if x in days else 0
            best = max(best, run)
            x += timedelta(days=1)
    return {"current": cur, "best": max(best, cur), "done_today": t in days}


# ---------------------------------------------------------------- weekly test
def last_test_day(revs: list[dict]) -> date | None:
    days = [_d(r["day"]) for r in revs if str(r.get("mode", "")).startswith("test_")]
    return max(days) if days else None


def test_ready(prog: dict, revs: list[dict]) -> tuple[bool, str]:
    if len(prog) < 15:
        return False, f"The weekly test opens once you've met 15 words ({len(prog)} so far)."
    last = last_test_day(revs)
    if last and (_today() - last).days < 7:
        return False, f"Next weekly test opens on {(last + timedelta(days=7)).strftime('%a %d %b')}."
    return True, ""


def build_test(prog: dict, n: int = TEST_SIZE) -> list[dict]:
    t = _today()
    r = _seed("test", t)
    recent = [p for p in prog.values() if _d(p.get("introduced_on")) and (t - _d(p["introduced_on"])).days <= 7]
    older = [p for p in prog.values() if p not in recent]
    r.shuffle(recent)
    r.shuffle(older)
    pick = recent[:7] + older[: max(0, n - min(7, len(recent)))]
    if len(pick) < n:
        pick += recent[7:7 + n - len(pick)]
    modes = ["meaning", "reverse", "sentence", "synonym", "spell"]
    return [{"wid": p["word_id"], "mode": modes[i % len(modes)]} for i, p in enumerate(pick[:n])]


def finish_test(n_right: int, n: int):
    _xp(XP["test"] + n_right, f"Words: weekly test ({n_right}/{n})")
    data.award_badges(data.me()["id"])


# ---------------------------------------------------------------- parent
def reset_progress(uid: str):
    st_ = data.store()
    _safe(st_.delete, "vocab_progress", {"user_id": uid})
    _safe(st_.delete, "vocab_reviews", {"user_id": uid})
    for a in data.activities(uid):
        if a.get("kind") == DONE_KIND:
            st_.delete("activities", {"id": a["id"]})
    for e in data.xp_events(uid):
        if str(e.get("reason", "")).startswith(f"{ICON} Words:"):
            st_.delete("xp_events", {"id": e["id"]})
    for k in list(data.badges(uid)):
        if k.startswith("words_"):
            st_.delete("badges", {"user_id": uid, "badge_key": k})


def summary(prog: dict, total: int) -> dict:
    stages = [int(p.get("stage") or 1) for p in prog.values()]
    return {"total": total, "started": len(prog), "growing": sum(1 for s in stages if 2 <= s <= 3),
            "strong": sum(1 for s in stages if 4 <= s <= 5), "mastered": sum(1 for s in stages if s >= 6),
            "tricky": sum(1 for p in prog.values() if p.get("leech")), "not_started": max(0, total - len(prog))}


def finish_date(not_started: int, per_day: int) -> date:
    return _today() + timedelta(days=-(-not_started // max(1, per_day)))


def badge_ctx(uid) -> dict:
    try:
        prog = progress(uid)
    except NotReady:
        return {"words_learned": 0, "words_mastered": 0, "words_streak": 0}
    return {"words_learned": sum(1 for p in prog.values() if int(p.get("stage") or 1) >= 2),
            "words_mastered": sum(1 for p in prog.values() if int(p.get("stage") or 1) >= 6),
            "words_streak": word_streak(uid)["best"]}

"""Times tables 1-15: question rounds, XP and mastery (pure functions)."""
from __future__ import annotations

import random

TABLES = list(range(1, 16))
ROUND = 12            # questions per round


# XP per correct answer by how HARD a table is (not just how big):
# 1, 2, 5, 10 and 11 follow easy patterns, so they pay the least.
DIFFICULTY = {1: 1, 2: 1, 5: 1, 10: 1, 11: 1,
              3: 2, 4: 2,
              6: 3, 9: 3, 12: 3,
              7: 4, 8: 4,
              13: 5, 14: 5, 15: 5}
REPEAT = [1.0, 0.5, 0.0]   # same table, same day: 1st round full XP, 2nd half, 3rd+ none
MASTERED_FACTOR = 0.5      # a table already mastered still pays, but half
FOCUS_FACTOR = 2           # Papa's focus tables pay double


def xp_per_correct(n: int) -> int:
    return DIFFICULTY.get(int(n), 1)


def repeat_factor(rounds_today: int) -> float:
    return REPEAT[min(int(rounds_today), len(REPEAT) - 1)]


def q_value(n: int, mastered_set: set, focus: set) -> float:
    v = float(xp_per_correct(n))
    if n in mastered_set:
        v *= MASTERED_FACTOR
    if n in focus:
        v *= FOCUS_FACTOR
    return v


def rounds_today(activities: list[dict], table, today: str) -> int:
    key = int(table) if table else None
    n = 0
    for a in activities:
        d = a.get("details") or {}
        if a.get("kind") == "tables" and str(a.get("day")) == today:
            t = int(d["table"]) if d.get("table") else None
            if t == key:
                n += 1
    return n


def time_target(n: int | None) -> int:
    """Seconds for a full round to count as fast / mastered."""
    return 60 if n is not None and n <= 10 else 90


def make_round(table: int | None, seed=None) -> list[list[int]]:
    """[[table, k], ...]. A single table asks n x 1..12 in a shuffled order (some flipped as k x n).
    table=None makes a mixed round across 2..15."""
    rnd = random.Random(seed)
    qs = []
    if table:
        ks = list(range(1, 13))
        rnd.shuffle(ks)
        qs = [[table, k] for k in ks[:ROUND]]
    else:
        for _ in range(ROUND):
            qs.append([rnd.randint(2, 15), rnd.randint(2, 12)])
    for q in qs:
        q.append(1 if rnd.random() < 0.4 else 0)   # 1 = show flipped (k x n)
    return qs


def score_round(table: int | None, questions: list, answers: list, seconds: float, rules: dict,
                already_mastered: set, xp_today: int, focus: set | None = None, repeats: int = 0) -> dict:
    """XP for a finished round: hardness x (mastered half, focus double) x repeat factor, then daily cap."""
    focus = set(focus or [])
    right = [q for q, a in zip(questions, answers) if a is not None and a == q[0] * q[1]]
    wrong = [(q, a) for q, a in zip(questions, answers) if a is None or a != q[0] * q[1]]
    f = repeat_factor(repeats)
    lines = []
    base = round(sum(q_value(q[0], already_mastered, focus) for q in right) * f)
    if right:
        lines.append((f"{len(right)} right", base))
    perfect = len(right) == len(questions)
    fast = seconds <= time_target(table)
    if perfect:
        lines.append(("Perfect round!", round(int(rules["tables_perfect_bonus"]) * f)))
    if perfect and fast:
        lines.append((f"Speedy (under {time_target(table)} s)", round(int(rules["tables_speed_bonus"]) * f)))
    new_master = bool(table) and perfect and fast and table not in already_mastered
    if new_master:
        lines.append((f"Mastered the {table}x table!", int(rules["tables_master_bonus"])))
    if f < 1:
        lines.append(("Round " + str(repeats + 1) + " of this table today: " +
                      ("half XP" if f > 0 else "no XP, try a different table!"), 0))
    raw = sum(x for _, x in lines)
    left = max(0, int(rules["tables_daily_cap"]) - int(xp_today))
    xp = min(raw, left)
    return {"right": len(right), "total": len(questions), "wrong": wrong, "lines": lines,
            "raw": raw, "xp": xp, "capped": xp < raw, "perfect": perfect, "fast": fast,
            "new_master": new_master, "repeat_factor": f}


def mastered(activities: list[dict]) -> set[int]:
    out = set()
    for a in activities:
        d = a.get("details") or {}
        if a.get("kind") == "tables" and d.get("mastered") and d.get("table"):
            out.add(int(d["table"]))
    return out


def best_by_table(activities: list[dict]) -> dict:
    """{table: {"rounds": n, "best": right, "fastest": seconds of a perfect round}}"""
    out = {}
    for a in activities:
        d = a.get("details") or {}
        if a.get("kind") != "tables" or not d.get("table"):
            continue
        t = int(d["table"])
        b = out.setdefault(t, {"rounds": 0, "best": 0, "fastest": None})
        b["rounds"] += 1
        b["best"] = max(b["best"], int(d.get("right") or 0))
        if d.get("right") == d.get("total") and d.get("seconds"):
            s = float(d["seconds"])
            b["fastest"] = s if b["fastest"] is None else min(b["fastest"], s)
    return out

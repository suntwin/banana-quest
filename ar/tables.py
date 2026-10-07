"""Times tables 1-15: question rounds, XP and mastery (pure functions)."""
from __future__ import annotations

import random

TABLES = list(range(1, 16))
ROUND = 12            # questions per round


def xp_per_correct(n: int) -> int:
    """Higher tables earn more: 1-3 -> 1, 4-6 -> 2, 7-9 -> 3, 10-12 -> 4, 13-15 -> 5."""
    return 1 + (int(n) - 1) // 3


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
                already_mastered: set, xp_today: int) -> dict:
    """XP for a finished round, respecting the daily cap."""
    right = [q for q, a in zip(questions, answers) if a is not None and a == q[0] * q[1]]
    wrong = [(q, a) for q, a in zip(questions, answers) if a is None or a != q[0] * q[1]]
    lines = []
    base = sum(xp_per_correct(q[0]) for q in right)
    if right:
        lines.append((f"{len(right)} right", base))
    perfect = len(right) == len(questions)
    fast = seconds <= time_target(table)
    if perfect:
        lines.append(("Perfect round!", int(rules["tables_perfect_bonus"])))
    if perfect and fast:
        lines.append((f"Speedy (under {time_target(table)} s)", int(rules["tables_speed_bonus"])))
    new_master = bool(table) and perfect and fast and table not in already_mastered
    if new_master:
        lines.append((f"Mastered the {table}x table!", int(rules["tables_master_bonus"])))
    raw = sum(x for _, x in lines)
    left = max(0, int(rules["tables_daily_cap"]) - int(xp_today))
    xp = min(raw, left)
    return {"right": len(right), "total": len(questions), "wrong": wrong, "lines": lines,
            "raw": raw, "xp": xp, "capped": xp < raw, "perfect": perfect, "fast": fast,
            "new_master": new_master}


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

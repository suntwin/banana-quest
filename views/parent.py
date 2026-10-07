from datetime import timedelta

import streamlit as st

from ar import data, gamify as g, style
from ar.style import esc

DET_LABELS = {f[0]: f[1] for sp in g.SPORTS.values() for f in sp["fields"]}
DET_LABELS.update({"topic": "Topic", "source": "Source", "correct": "Right", "total": "Total",
                   "title": "Title", "genre": "Type", "words": "Words"})


def render():
    if data.is_child():
        st.warning("Parent Hub is for grown-ups 🙂")
        return
    kid = data.fresh_child()
    s = data.stats(kid["id"])
    w = s["wallet"]
    pend = [a for a in s["activities"] if a.get("status") == "pending"]
    reqs = [r for r in data.redemptions(kid["id"]) if r.get("kind") == "reward" and r.get("status") == "requested"]

    st.markdown("# 🧭 Parent Hub")
    st.markdown(
        '<div class="ar-stat">'
        f'<div class="box"><div class="big">✅ {len(pend)}</div><div class="lbl">logs to check</div></div>'
        f'<div class="box"><div class="big">🎁 {len(reqs)}</div><div class="lbl">reward requests</div></div>'
        f'<div class="box money"><div class="big">🍌 {w["balance"]}</div><div class="lbl">Aadiv\'s XP balance</div></div>'
        f'<div class="box"><div class="big">{s["level"]["icon"]} {s["level"]["num"]}</div><div class="lbl">level · {w["earned"]} XP lifetime</div></div>'
        '</div>', unsafe_allow_html=True)
    st.write("")
    tabs = st.tabs([f"✅ To approve ({len(pend)})", f"🎁 Rewards ({len(reqs)})", "📺 Screen time",
                    "📊 This week", "🎉 Bonus XP", "💡 Tips", "⚙️ Settings"])
    with tabs[0]:
        _approvals(pend)
    with tabs[1]:
        _rewards(reqs)
    with tabs[2]:
        _screen(kid)
    with tabs[3]:
        _week(s)
    with tabs[4]:
        _bonus()
    with tabs[5]:
        _tips()
    with tabs[6]:
        _settings()


# ---------------------------------------------------------------- approvals
def _approvals(pend):
    if not pend:
        st.success("All caught up. Nothing waiting. 🍌")
        return
    sett = data.settings()
    simple = [a for a in pend if a["kind"] != "writing"]
    if len(simple) > 1 and st.button(f"✅ Approve all {len(simple)} sport & maths logs as claimed",
                                     use_container_width=True):
        for a in simple:
            data.approve(a)
        st.rerun()
    for a in sorted(pend, key=lambda x: str(x.get("day"))):
        k = g.KINDS[a["kind"]]
        det = a.get("details") or {}
        stats = " · ".join(f"{DET_LABELS.get(key, key)}: {esc(v)}" for key, v in det.items()
                           if key in DET_LABELS and v not in (None, "") and key not in ("title",))
        lines = "".join(style.pill(f"{t} +{x}", "den") for t, x in det.get("xp_lines", []))
        pb = "".join(style.pill(f"🏅 PB: {p}", "ok") for p in det.get("pbs", []))
        title = f' · "{esc(det.get("title"))}"' if det.get("title") else ""
        st.markdown(
            f'<div class="ar-sport {a["kind"]}" style="margin-bottom:0;border-radius:22px 22px 0 0">'
            f'{k["icon"]} {esc(k["name"])} · {esc(a.get("session_type"))}{title} · {esc(str(a.get("day")))} · '
            f'{a.get("minutes")} min · effort {a.get("effort")}/5</div>', unsafe_allow_html=True)
        with st.container(border=True):
            if stats:
                st.markdown(f'<div class="ar-small">{stats}</div>', unsafe_allow_html=True)
            if a.get("note"):
                st.markdown(f'💬 _{esc(a["note"])}_')
            st.markdown(lines + pb, unsafe_allow_html=True)
            if det.get("text"):
                with st.expander("📖 Read the writing"):
                    st.text(det["text"])
            c1, c2, c3 = st.columns([1, 1, 2])
            xp = c1.number_input("XP to give", min_value=0, max_value=1000, value=int(a.get("xp") or 0), step=5,
                                 key=f"xp_{a['id']}")
            stars = 0
            if a["kind"] == "writing":
                stars = c2.select_slider("Writing stars", options=[0, 1, 2, 3], value=0, key=f"stars_{a['id']}",
                                         format_func=lambda v: "⭐" * v if v else "none",
                                         help=f"+{sett['rules']['writing_star']} XP per star")
            note = c3.text_input("Note for Aadiv (optional)", key=f"note_{a['id']}")
            b1, b2 = st.columns(2)
            if b1.button("✅ Approve", key=f"ok_{a['id']}", use_container_width=True):
                data.approve(a, xp, stars, note)
                st.rerun()
            if b2.button("✖ Don't count it", key=f"no_{a['id']}", type="tertiary", use_container_width=True):
                data.reject(a, note)
                st.rerun()
        st.write("")


# ---------------------------------------------------------------- rewards
def _rewards(reqs):
    st.markdown("#### Requests to hand over")
    if not reqs:
        st.caption("No reward requests right now.")
    for r in reqs:
        c1, c2, c3 = st.columns([2.6, 1.3, 1.1])
        c1.markdown(f'**{esc(r["title"])}** · 🍌 {r["cost"]} XP · asked {esc(str(r.get("day")))}')
        if c2.button("🎉 Given", key=f"dl_{r['id']}", use_container_width=True):
            data.deliver(r)
            st.rerun()
        if c3.button("↩️ Decline", key=f"dc_{r['id']}", type="tertiary", use_container_width=True,
                     help="XP goes back to Aadiv"):
            data.refund(r, "declined")
            st.rerun()

    st.markdown("#### Reward catalogue")
    st.caption("Set prices in XP. Rough guide with default rules: a solid training week earns about 500 to 700 XP.")
    for r in data.rewards(active_only=False):
        lab = f'{r.get("emoji", "🎁")} {r["name"]} · {r["cost"]} XP' + ("" if r.get("active", True) else " (hidden)")
        with st.expander(lab):
            _reward_form(r)
    with st.expander("➕ Add a new reward"):
        _reward_form({})


def _reward_form(r):
    rid = r.get("id") or "new"
    with st.form(f"rw_{rid}"):
        c1, c2, c3 = st.columns([1, 3, 1.4])
        emoji = c1.text_input("Emoji", r.get("emoji", "🎁"))
        name = c2.text_input("Name", r.get("name", ""))
        cost = c3.number_input("Cost (XP)", min_value=10, max_value=50000, value=int(r.get("cost") or 500), step=50)
        desc = st.text_input("Description", r.get("description") or "")
        active = st.checkbox("Show in the shop", value=r.get("active", True))
        if st.form_submit_button("Save reward", use_container_width=True):
            if not name.strip():
                st.error("Give it a name.")
            else:
                data.save_reward({"id": r.get("id"), "emoji": emoji.strip() or "🎁", "name": name.strip(),
                                  "cost": int(cost), "description": desc.strip(), "active": active})
                st.rerun()
    if r.get("id"):
        c1, c2 = st.columns([2, 1])
        sure = c1.checkbox("Yes, delete this reward for good", key=f"delok_{rid}",
                           help="Tip: untick 'Show in the shop' instead if you only want to hide it for now.")
        if c2.button("🗑️ Delete reward", key=f"del_{rid}", type="tertiary", disabled=not sure,
                     use_container_width=True):
            data.delete_reward(r)
            st.rerun()


# ---------------------------------------------------------------- screen time
def _screen(kid):
    s = data.screen_today(kid["id"])
    wk = data.screen_summary(kid["id"], 7)
    share = f"{round(100 * wk['xp'] / wk['earned'])}%" if wk["earned"] else "–"
    st.markdown(
        '<div class="ar-stat">'
        f'<div class="box"><div class="big">📺 {s["bought"]}</div><div class="lbl">min today (cap {s["cap"]})</div></div>'
        f'<div class="box"><div class="big">⏱️ {wk["minutes"] // 60}h {wk["minutes"] % 60}m</div><div class="lbl">screens last 7 days</div></div>'
        f'<div class="box money"><div class="big">🍌 {wk["xp"]}</div><div class="lbl">XP spent on screens (7 days)</div></div>'
        f'<div class="box"><div class="big">{share}</div><div class="lbl">of the {wk["earned"]} XP he earned</div></div>'
        '</div>', unsafe_allow_html=True)
    split = " · ".join(f"{data.SCREEN_TYPES[k]} {v} min" for k, v in wk["by_type"].items() if v)
    st.caption(f"Last 7 days by screen: {split or 'none yet'}. Rate {s['rate']} XP per minute · unlock rule "
               f"{'on' if s['need_activity'] else 'off'} · "
               f"{'active today' if s['active_today'] else 'nothing logged today yet'}.")

    live = [t for t in s["tickets"] if t.get("status") in ("ready", "running")]
    if live:
        st.markdown("#### Tickets right now")
    for t in live:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"{esc(t['title'])} · {t['status']}" +
                    (f" · {data.seconds_left(t) // 60} min left" if t["status"] == "running" else ""))
        if c2.button("Cancel + refund", key=f"rf_{t['id']}", type="tertiary", use_container_width=True):
            data.refund(t, "cancelled")
            st.rerun()

    with st.expander("➕ Add screen time he watched without a ticket"):
        with st.form("add_screen", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            kind = c1.selectbox("Screen", list(data.SCREEN_TYPES), format_func=lambda k: data.SCREEN_TYPES[k])
            mins = c2.number_input("Minutes", min_value=5, max_value=600, value=30, step=5)
            day = c3.date_input("Day", value=g.today(), max_value=g.today(), format="DD/MM/YYYY")
            charge = st.checkbox(f"Take the XP for it ({s['rate']} XP per minute)", value=True,
                                 help="Untick to just record it (e.g. a family movie night). Taking XP can push his balance below zero, which he then earns back.")
            if st.form_submit_button("Add it", use_container_width=True):
                data.add_screen_by_parent(kind, int(mins), day, charge)
                st.success("Recorded.")
                st.rerun()

    st.markdown("#### Last 14 days")
    full = data.screen_summary(kid["id"], 14)
    heads = "".join(f'<th class="n">{data.SCREEN_TYPES[k]}</th>' for k in data.SCREEN_TYPES)
    rows = ""
    for i in range(14):
        d = g.today() - timedelta(days=i)
        r = full["by_day"].get(str(d), {"min": 0, "xp": 0, **{k: 0 for k in data.SCREEN_TYPES}})
        cells = "".join(f'<td class="n">{r[k] or ""}</td>' for k in data.SCREEN_TYPES)
        rows += (f'<tr><td>{d.strftime("%a %d %b")}</td>{cells}<td class="n"><b>{r["min"]} min</b></td>'
                 f'<td class="n">🍌 {r["xp"]}</td></tr>')
    style.card(f'<table class="ar-table"><tr><th>Day</th>{heads}<th class="n">Total</th><th class="n">XP spent</th></tr>'
               f'{rows}</table><div class="ar-small" style="margin-top:6px">Counts screen time that was used or is '
               f'running. Tickets bought but not started yet are not counted.</div>')


# ---------------------------------------------------------------- this week
def _week(s):
    sett = data.settings()
    acts = s["activities"]
    prog = g.week_progress(acts, sett["goals"])
    for kind, p in prog.items():
        k = g.KINDS[kind]
        st.markdown(f'{k["icon"]} **{k["name"]}**: {p["done"]} / {p["goal"]} {p["unit"]}')
        st.markdown(style.bar(p["pct"], "ok" if p["pct"] >= 1 else ""), unsafe_allow_html=True)
    wk = g.week_start()
    ev = [e for e in data.xp_events() if g.to_date(e.get("created_at")) and g.to_date(e["created_at"]) >= wk]
    st.markdown(f"**XP earned this week:** {sum(int(e['amount']) for e in ev)}")
    week_acts = [a for a in acts if g.to_date(a["day"]) >= wk]
    rows = "".join(
        f'<tr><td>{esc(str(a["day"])[5:])}</td><td>{g.KINDS[a["kind"]]["icon"]} {esc(a.get("session_type"))}</td>'
        f'<td class="n">{a.get("minutes")} min</td><td class="n">+{a.get("xp")}</td><td>{esc(a.get("status"))}</td></tr>'
        for a in sorted(week_acts, key=lambda x: str(x["day"])))
    if rows:
        style.card(f'<table class="ar-table"><tr><th>Day</th><th>What</th><th class="n">Time</th>'
                   f'<th class="n">XP</th><th>Status</th></tr>{rows}</table>')


# ---------------------------------------------------------------- bonus
def _bonus():
    st.caption("Reward things the app can't see: a great attitude at training, helping a teammate, reading a book.")
    with st.form("bonus"):
        c1, c2 = st.columns([1, 3])
        amt = c1.number_input("XP", min_value=-500, max_value=1000, value=20, step=5,
                              help="Negative takes XP away. Use sparingly!")
        why = c2.text_input("Why?", placeholder="Awesome sportsmanship at Saturday's game")
        if st.form_submit_button("Give XP 🍌", use_container_width=True):
            if not why.strip() or not amt:
                st.error("Add an amount and a reason.")
            else:
                data.manual_bonus(int(amt), why.strip())
                st.success(f"{'+' if amt > 0 else ''}{amt} XP sent to Aadiv.")


# ---------------------------------------------------------------- tips
def _tips():
    st.caption("One tip shows on Aadiv's Home page each day, rotating through this list.")
    items = data.tips()
    if items:
        today = items[g.today().toordinal() % len(items)]
        style.card(f'<div class="ar-title" style="font-size:1.05rem">💡 Showing today</div>'
                   f'<div style="font-weight:700">{esc(today)}</div>', "ar-card ar-tip")
    with st.form("add_tip", clear_on_submit=True):
        new = st.text_input("Add a tip", placeholder="🏀 Bend your knees on every shot")
        if st.form_submit_button("➕ Add tip", use_container_width=True):
            if new.strip():
                data.save_tips(items + [new.strip()])
                st.rerun()
            st.error("Type a tip first.")
    if not items:
        st.info("No tips yet, so the tip card is hidden on Home.")
    for i, t in enumerate(items):
        c1, c2 = st.columns([6, 1])
        c1.markdown(f"{i + 1}. {esc(t)}")
        if c2.button("🗑️", key=f"tipdel_{i}", type="tertiary", help="Remove this tip", use_container_width=True):
            data.save_tips(items[:i] + items[i + 1:])
            st.rerun()
    if st.button("↩️ Restore the starter tips", type="tertiary"):
        data.save_tips(list(dict.fromkeys(items + g.DEFAULT_TIPS)))
        st.rerun()


# ---------------------------------------------------------------- settings
def _settings():
    sett = data.settings()
    with st.form("settings"):
        st.markdown("#### Approval")
        appr = st.radio("When Aadiv logs something...", ["parent", "auto"],
                        index=0 if sett["approval"] == "parent" else 1, horizontal=True,
                        format_func=lambda v: "I check it first (XP waits)" if v == "parent" else "XP lands straight away")
        st.markdown("#### Weekly goals")
        st.caption("Set a goal to 0 to switch that activity off: it disappears from Home and Log it! "
                   "(past logs and records stay in the Trophy Room).")
        gc = st.columns(5)
        goals = {}
        for col, kind in zip(gc, ["basketball", "tennis", "swimming", "maths", "writing"]):
            unit = "pieces" if kind == "writing" else "min"
            goals[kind] = col.number_input(f'{g.KINDS[kind]["icon"]} {unit}', min_value=0, max_value=2000,
                                           value=int(sett["goals"].get(kind, 0)), step=1 if kind == "writing" else 15)
        st.markdown("#### Screen time")
        sc = sett["screen"]
        a, b, c = st.columns(3)
        rate = a.number_input("XP per minute", min_value=1, max_value=50, value=int(sc["xp_per_min"]))
        wd = b.number_input("Max min on school days", min_value=0, max_value=600, value=int(sc["cap_weekday"]), step=15)
        we = c.number_input("Max min on weekends", min_value=0, max_value=600, value=int(sc["cap_weekend"]), step=15)
        need = st.checkbox("Screen time only unlocks after something is logged that day", value=bool(sc["need_activity"]))
        opts = st.text_input("Ticket sizes (minutes, comma separated)", ", ".join(str(x) for x in sc["options"]))
        st.markdown("#### Times tables")
        focus = st.multiselect("🎯 Focus tables (double XP, shown at the top of his Times Tables page)",
                               list(range(1, 16)), default=[int(x) for x in sett.get("tables_focus") or []],
                               format_func=lambda n: f"{n}×")
        with st.expander("Advanced: XP rules"):
            rules = {}
            rc = st.columns(3)
            for i, (key, val) in enumerate(sett["rules"].items()):
                rules[key] = rc[i % 3].number_input(key.replace("_", " "), min_value=0, max_value=1000,
                                                    value=int(val), step=1, key=f"rule_{key}")
        if st.form_submit_button("Save settings", use_container_width=True):
            try:
                options = sorted({int(x) for x in opts.replace(" ", "").split(",") if x})
            except ValueError:
                options = sc["options"]
            data.save_settings({"approval": appr, "goals": {k: int(v) for k, v in goals.items()},
                                "screen": {"xp_per_min": int(rate), "cap_weekday": int(wd), "cap_weekend": int(we),
                                           "need_activity": need, "options": options or [15, 30]},
                                "rules": {k: int(v) for k, v in rules.items()},
                                "tables_focus": [int(x) for x in focus]})
            st.success("Saved ✅")

    st.markdown("#### Reset test data")
    st.caption("Wipes Aadiv's logs, XP, badges and shop history. Rewards and settings stay.")
    ok = st.checkbox("Yes, I really want to wipe Aadiv's data")
    if st.button("🧹 Wipe Aadiv's data", type="tertiary", disabled=not ok):
        data.reset_child_data()
        st.success("Wiped. Fresh start!")

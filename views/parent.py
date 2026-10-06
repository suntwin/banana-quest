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
                    "📊 This week", "🎉 Bonus XP", "⚙️ Settings"])
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


# ---------------------------------------------------------------- screen time
def _screen(kid):
    s = data.screen_today(kid["id"])
    st.markdown(f"**Today:** {s['bought']} of {s['cap']} min booked or used · rate {s['rate']} XP/min · "
                f"unlock rule {'on' if s['need_activity'] else 'off'} · "
                f"{'✅ active today' if s['active_today'] else '⏸ nothing logged today yet'}")
    live = [t for t in s["tickets"] if t.get("status") in ("ready", "running")]
    for t in live:
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"{esc(t['title'])} · {t['status']}" +
                    (f" · {data.seconds_left(t) // 60} min left" if t["status"] == "running" else ""))
        if c2.button("Cancel + refund", key=f"rf_{t['id']}", type="tertiary", use_container_width=True):
            data.refund(t, "cancelled")
            st.rerun()
    st.markdown("#### Last 14 days")
    tickets = data.refresh_tickets(kid["id"])
    rows = ""
    for i in range(14):
        d = g.today() - timedelta(days=i)
        ts = [t for t in tickets if str(t.get("day")) == str(d) and t.get("status") in data.SPENT_STATUSES]
        mins = sum(int(t.get("minutes") or 0) for t in ts)
        xp = sum(int(t.get("cost") or 0) for t in ts)
        rows += f'<tr><td>{d.strftime("%a %d %b")}</td><td class="n">{mins} min</td><td class="n">🍌 {xp}</td></tr>'
    style.card(f'<table class="ar-table"><tr><th>Day</th><th class="n">Screen time</th><th class="n">XP spent</th></tr>{rows}</table>')


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


# ---------------------------------------------------------------- settings
def _settings():
    sett = data.settings()
    with st.form("settings"):
        st.markdown("#### Approval")
        appr = st.radio("When Aadiv logs something...", ["parent", "auto"],
                        index=0 if sett["approval"] == "parent" else 1, horizontal=True,
                        format_func=lambda v: "I check it first (XP waits)" if v == "parent" else "XP lands straight away")
        st.markdown("#### Weekly goals")
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
                                "rules": {k: int(v) for k, v in rules.items()}})
            st.success("Saved ✅")

    st.markdown("#### Reset test data")
    st.caption("Wipes Aadiv's logs, XP, badges and shop history. Rewards and settings stay.")
    ok = st.checkbox("Yes, I really want to wipe Aadiv's data")
    if st.button("🧹 Wipe Aadiv's data", type="tertiary", disabled=not ok):
        data.reset_child_data()
        st.success("Wiped. Fresh start!")

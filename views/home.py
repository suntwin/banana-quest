import streamlit as st

from ar import data, gamify as g, nav, style
from ar.style import esc

STATUS = {"pending": ("⏳ waiting for Papa", "yel"), "approved": ("✅ approved", "ok"),
          "rejected": ("✖ not counted", "bad")}


def render():
    me, kid = data.me(), data.fresh_child()
    is_child = me["role"] == "child"
    s = data.stats(kid["id"])
    lvl, stk, w = s["level"], s["streak"], s["wallet"]
    sett = data.settings()
    hour = __import__("datetime").datetime.now(g.TZ).hour
    hello = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

    nxt = f"{lvl['to_next']} XP to Level {lvl['num'] + 1}" if lvl["next"] else "Top level! 👑"
    style.card(
        f'<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">'
        f'<div><h1>{hello}, {esc(kid["display_name"])}!</h1>'
        f'<div class="sub">Level {lvl["num"]} · {lvl["icon"]} {lvl["name"]} · {w["earned"]} XP earned</div></div>'
        f'<div style="font-size:56px">{lvl["icon"]}</div></div>'
        f'<div class="bar-wrap">{style.bar(lvl["pct"])}</div>'
        f'<div class="band">{nxt}</div>', "ar-hero")

    if is_child:
        new = data.unseen_badges()
        if new:
            style.banana_burst()
            items = "".join(f'<div class="ar-badge new"><div class="ic">{g.BADGE_MAP[k][0]}</div>'
                            f'{esc(g.BADGE_MAP[k][1])}</div>' for k in new if k in g.BADGE_MAP)
            style.card(f'<div class="ar-title" style="font-size:1.3rem">🎉 New badge{"s" if len(new) > 1 else ""}!</div>{items}')
            data.mark_badges_seen(new)

    scr = data.screen_today(kid["id"])
    fire = "🔥" if stk["current"] else "🌱"
    st.markdown(
        '<div class="ar-stat">'
        f'<div class="box money"><div class="big">🍌 {w["balance"]}</div><div class="lbl">XP to spend</div></div>'
        f'<div class="box"><div class="big">⏳ {w["pending"]}</div><div class="lbl">XP waiting for Papa</div></div>'
        f'<div class="box"><div class="big">{fire} {stk["current"]}</div><div class="lbl">day streak · best {stk["best"]}</div></div>'
        f'<div class="box"><div class="big">📺 {scr["left"]}</div><div class="lbl">screen min left today</div></div>'
        '</div>', unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("### 🎯 This week's missions")
        prog = g.week_progress(s["activities"], sett["goals"])
        active = g.active_kinds(sett)
        for kind in active:
            p = prog.get(kind)
            if not p or not p["goal"]:
                continue
            k = g.KINDS[kind]
            done = p["pct"] >= 1
            tick = " ✅" if done else ""
            st.markdown(
                f'<div class="ar-sport {kind}"><div style="display:flex;justify-content:space-between">'
                f'<span style="font-size:1.1rem">{k["icon"]} {k["name"]}{tick}</span>'
                f'<span>{p["done"]} / {p["goal"]} {p["unit"]}</span></div>'
                f'<div style="margin-top:6px">{style.bar(p["pct"], "ok" if done else "")}</div></div>',
                unsafe_allow_html=True)
        st.caption(f"Each goal you hit = +{sett['rules']['weekly_goal_bonus']} XP. Every sports goal = "
                   f"+{sett['rules']['triple_threat_bonus']} more. Week starts Monday.")
        if is_child:
            cols = st.columns(max(1, len(active)))
            for col, kind in zip(cols, active):
                if col.button(g.KINDS[kind]["icon"], key=f"go_{kind}", help=f"Log {g.KINDS[kind]['name']}",
                              use_container_width=True):
                    st.session_state.log_kind = kind
                    nav.go("log")

    with right:
        _goal_card(kid, w)
        tips = data.tips()
        if tips:
            tip = tips[g.today().toordinal() % len(tips)]
            style.card(f'<div class="ar-title" style="font-size:1.15rem">💡 Coach\'s tip</div>'
                       f'<div style="margin-top:6px;font-weight:700">{esc(tip)}</div>', "ar-card ar-tip")
        _recent(s["activities"])


def _goal_card(kid, w):
    rs = {r["id"]: r for r in data.rewards()}
    goal = rs.get(kid.get("goal_reward_id"))
    if not goal:
        style.card('<div class="ar-title" style="font-size:1.15rem">🎁 Saving for...</div>'
                   '<div class="ar-small">Pick a goal in the Reward Shop and watch your bananas pile up!</div>')
        return
    cost = int(goal["cost"])
    pct = w["balance"] / cost if cost else 1
    msg = "You can get it now! 🎉" if pct >= 1 else f"{cost - w['balance']} XP to go"
    style.card(f'<div class="ar-title" style="font-size:1.15rem">🎁 Saving for...</div>'
               f'<div style="display:flex;gap:12px;align-items:center;margin:6px 0">'
               f'<div style="font-size:2.4rem">{esc(goal.get("emoji", "🎁"))}</div>'
               f'<div><b>{esc(goal["name"])}</b><div class="ar-small">{cost} XP · {msg}</div></div></div>'
               f'{style.bar(pct, "den")}')


def _recent(acts):
    rows = sorted(acts, key=lambda a: str(a.get("created_at")), reverse=True)[:6]
    if not rows:
        style.card('<div class="ar-title" style="font-size:1.15rem">📋 Recent</div>'
                   '<div class="ar-small">Nothing logged yet. Hit ➕ Log it! after your next training.</div>')
        return
    body = ""
    for a in rows:
        k = g.KINDS.get(a["kind"], {"icon": "•", "name": a["kind"]})
        lab, col = STATUS.get(a.get("status"), ("", "grey"))
        mins = f" · {a['minutes']} min" if a.get("minutes") else ""
        body += (f'<div style="padding:6px 0;border-bottom:1px solid #f3e3a1">'
                 f'<b>{k["icon"]} {esc(k["name"])}</b> <span class="ar-small">{esc(a.get("session_type") or "")}{mins} · '
                 f'{esc(str(a.get("day"))[5:])}</span><br>{style.pill("+" + str(a.get("xp", 0)) + " XP", "yel")}'
                 f'{style.pill(lab, col)}</div>')
    style.card(f'<div class="ar-title" style="font-size:1.15rem">📋 Recent</div>{body}')

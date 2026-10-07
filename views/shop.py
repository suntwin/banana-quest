from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

from ar import data, gamify as g, style
from ar.style import esc

RED_STATUS = {"requested": ("⏳ waiting for Papa", "yel"), "delivered": ("🎉 got it!", "ok"),
              "rejected": ("↩️ declined, XP refunded", "bad"), "ready": ("🎟️ ready to use", "den"),
              "running": ("▶️ running now", "ok"), "used": ("✔ used", "grey"),
              "cancelled": ("↩️ cancelled, XP refunded", "grey")}


def render():
    is_child = data.is_child()
    kid = data.fresh_child()
    w = data.wallet(kid["id"])
    st.markdown("# 🎁 Reward Shop")
    st.markdown(
        '<div class="ar-stat">'
        f'<div class="box money"><div class="big">🍌 {w["balance"]}</div><div class="lbl">XP to spend</div></div>'
        f'<div class="box"><div class="big">⏳ {w["pending"]}</div><div class="lbl">XP waiting for Papa</div></div>'
        f'<div class="box"><div class="big">🛍️ {w["spent"]}</div><div class="lbl">XP spent so far</div></div>'
        '</div>', unsafe_allow_html=True)
    st.write("")
    t1, t2, t3 = st.tabs(["🎁 Rewards", "📺 Screen time", "🧾 My history"])
    with t1:
        _rewards(kid, w, is_child)
    with t2:
        _screen(kid, w, is_child)
    with t3:
        _history(kid)


# ---------------------------------------------------------------- rewards
def _rewards(kid, w, is_child):
    waiting = [r for r in data.redemptions(kid["id"]) if r.get("kind") == "reward" and r.get("status") == "requested"]
    if waiting:
        style.card('<div class="ar-title" style="font-size:1.1rem">⏳ On the way</div>'
                   + "".join(style.pill(r["title"], "yel") for r in waiting)
                   + '<div class="ar-small">Papa will hand these over soon. If he says no, the XP comes back.</div>',
                   "ar-card ar-tip")
    rs = data.rewards()
    if not rs:
        st.info("No rewards yet. Papa can add some in Parent Hub → Rewards.")
        return
    goal_id = kid.get("goal_reward_id")
    cols = st.columns(3)
    for i, r in enumerate(rs):
        cost = int(r["cost"])
        pct = w["balance"] / cost if cost else 1
        is_goal = r["id"] == goal_id
        with cols[i % 3]:
            need = "Ready to swap! 🎉" if pct >= 1 else f"{cost - w['balance']} XP to go"
            st.markdown(
                f'<div class="ar-reward {"goal" if is_goal else ""}"><div class="em">{esc(r.get("emoji", "🎁"))}</div>'
                f'<div class="nm">{esc(r["name"])}</div><div class="cost">🍌 {cost} XP</div>'
                f'<div class="ar-small" style="min-height:2.4em">{esc(r.get("description") or "")}</div>'
                f'<div style="margin:.4rem 0">{style.bar(pct, "den" if pct < 1 else "ok")}</div>'
                f'<div class="ar-small">{"⭐ My goal · " if is_goal else ""}{need}</div></div>',
                unsafe_allow_html=True)
            if is_child:
                ck = f"confirm_{r['id']}"
                if st.session_state.get(ck):
                    st.warning(f"Swap {cost} XP for {r['name']}?")
                    a, b = st.columns(2)
                    if a.button("Yes!", key=f"yes_{r['id']}", use_container_width=True):
                        err = data.redeem_reward(r)
                        st.session_state.pop(ck, None)
                        if err:
                            st.error(err)
                        else:
                            st.session_state.shop_msg = f"🎉 You asked for {r['name']}! Papa will hand it over."
                            st.rerun()
                    if b.button("No", key=f"no_{r['id']}", type="tertiary", use_container_width=True):
                        st.session_state.pop(ck, None)
                        st.rerun()
                else:
                    a, b = st.columns(2)
                    if a.button("Swap!", key=f"buy_{r['id']}", disabled=pct < 1, use_container_width=True):
                        st.session_state[ck] = True
                        st.rerun()
                    if b.button("⭐ Goal" if not is_goal else "★ Goal", key=f"goal_{r['id']}", type="tertiary",
                                use_container_width=True, disabled=is_goal):
                        data.set_goal(r["id"])
                        st.rerun()
            st.write("")
    msg = st.session_state.pop("shop_msg", None)
    if msg:
        style.banana_burst()
        st.success(msg)


# ---------------------------------------------------------------- screen time
def _screen(kid, w, is_child):
    s = data.screen_today(kid["id"])
    day_kind = "weekend" if g.is_weekend() else "school day"
    style.card(
        f'<div class="ar-title" style="font-size:1.2rem">📺 Earn your screen time</div>'
        f'<div style="font-weight:700">Every minute costs <b>{s["rate"]} XP</b>. Today is a {day_kind}: '
        f'up to <b>{s["cap"]} min</b> ({s["left"]} min left).</div>'
        f'<div style="margin-top:8px">{style.bar(s["bought"] / s["cap"] if s["cap"] else 1, "den")}</div>'
        f'<div class="ar-small" style="margin-top:4px">{s["bought"]} of {s["cap"]} min used or booked today</div>')
    locked = s["need_activity"] and not s["active_today"]
    if locked:
        style.card("🔒 <b>Screen time is locked.</b> Log some sport, maths or writing today and it unlocks!",
                   "ar-card ar-bad")

    # live tickets
    tickets = [t for t in s["tickets"] if t.get("status") in ("ready", "running")]
    for t in tickets:
        if t["status"] == "running":
            _countdown(t)
            if is_child and st.button("⏹ Stop early and save the rest", key=f"stop_{t['id']}", type="tertiary",
                                      use_container_width=True):
                data.stop_ticket(t)
                st.rerun()
        else:
            style.card(f'<div class="ar-title" style="font-size:1.1rem">{esc(t["title"])}: ready</div>'
                       '<div class="ar-small">Tap start when you sit down to play. The timer counts down.</div>')
            if is_child:
                a, b = st.columns([2, 1])
                if a.button("▶ Start my timer", key=f"start_{t['id']}", use_container_width=True):
                    data.start_ticket(t)
                    st.rerun()
                if b.button("Cancel (refund)", key=f"cancel_{t['id']}", type="tertiary", use_container_width=True):
                    data.refund(t, "cancelled")
                    st.rerun()

    if is_child:
        st.markdown("#### Buy a screen-time ticket")
        kind = st.radio("What for?", list(data.SCREEN_TYPES), horizontal=True, key="scr_kind",
                        format_func=lambda k: data.SCREEN_TYPES[k])
        cols = st.columns(len(s["options"]))
        for col, m in zip(cols, s["options"]):
            cost = int(m) * s["rate"]
            dis = locked or m > s["left"] or w["balance"] < cost
            if col.button(f"{m} min\n🍌 {cost}", key=f"scr_{m}", disabled=dis, use_container_width=True):
                err = data.buy_screen(int(m), kind)
                if err:
                    st.error(err)
                else:
                    st.rerun()
        st.caption("Tickets are for today only. Unused tickets are refunded automatically tomorrow, or cancel one any time.")
    else:
        st.caption("Change the XP rate, daily limits and the unlock rule in Parent Hub → Settings.")
    wk = data.screen_summary(kid["id"], 7)
    split = " · ".join(f"{data.SCREEN_TYPES[k]} {v} min" for k, v in wk["by_type"].items() if v) or "none yet"
    style.card(f'<div class="ar-title" style="font-size:1.05rem">📊 Last 7 days</div>'
               f'<div style="font-weight:700">{wk["minutes"]} min of screens ({split})</div>'
               f'<div class="ar-small">🍌 {wk["xp"]} XP spent on screens · {wk["earned"]} XP earned</div>')


def _countdown(t):
    secs = data.seconds_left(t)
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000) + secs * 1000
    components.html(f"""
<div style="font-family:'Luckiest Guy',Nunito,sans-serif;text-align:center;background:#fff;border:3px solid #ffd60a;
 border-radius:24px;padding:14px">
<link href="https://fonts.googleapis.com/css2?family=Luckiest+Guy&display=swap" rel="stylesheet">
<div style="font-family:Nunito,sans-serif;font-weight:800;color:#55678a">{esc(t['title'])}</div>
<div id="t" style="font-size:56px;color:#1f4f8f;letter-spacing:2px">--:--</div>
<div id="m" style="font-family:Nunito,sans-serif;font-weight:800;color:#1f3358"></div></div>
<script>
const end={end_ms};
function tick(){{
  const s=Math.max(0,Math.round((end-Date.now())/1000));
  const mm=String(Math.floor(s/60)).padStart(2,'0'), ss=String(s%60).padStart(2,'0');
  document.getElementById('t').textContent=mm+':'+ss;
  if(s<=60&&s>0){{document.getElementById('m').textContent='One minute left! Find a good place to stop.';}}
  if(s===0){{document.getElementById('t').textContent="TIME'S UP!";
    document.getElementById('m').textContent='Great job. Screens off, go bounce a ball 🏀';return;}}
  setTimeout(tick,500);
}}
tick();
</script>""", height=150)


# ---------------------------------------------------------------- history
def _history(kid):
    reds = data.redemptions(kid["id"])
    if not reds:
        st.info("Nothing swapped yet.")
        return
    rows = ""
    for r in reds[:60]:
        lab, col = RED_STATUS.get(r.get("status"), (r.get("status"), "grey"))
        rows += (f'<tr><td>{esc(str(r.get("day") or "")[5:])}</td><td>{esc(r["title"])}</td>'
                 f'<td class="n">🍌 {int(r.get("cost") or 0)}</td><td>{style.pill(lab, col)}</td></tr>')
    style.card(f'<table class="ar-table"><tr><th>Day</th><th>What</th><th class="n">XP</th><th>Status</th></tr>{rows}</table>')

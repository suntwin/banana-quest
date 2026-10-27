"""🗓️ Daily Routine: 25-minute Maths and English sessions with a timer. XP lands the moment a session is done."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ar import data, gamify as g, nav, routine as rq, style
from ar.style import esc

EARLY_REASONS = ["Finished my work early", "Had to stop (dinner, going out…)", "Didn't feel well", "Other"]


# ---------------------------------------------------------------- his page
def render():
    me, kid = data.me(), data.fresh_child()
    is_child = me["role"] == "child"
    sett = data.settings()
    bl = rq.blocks(sett)
    day = g.today()
    todays = rq.day_blocks(day, bl)
    dm = rq.done_map(kid["id"], day - timedelta(days=day.weekday()), day + timedelta(days=6))
    done_today = sum(1 for b in todays if (dm.get((b["id"], str(day))) or {}).get("details", {}).get("full"))
    r = sett["rules"]
    style.card(
        f'<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">'
        f'<div><h1>🗓️ {"My" if is_child else "His"} Daily Routine</h1>'
        f'<div class="sub">Start the timer, focus until it rings, then tap I\'m done. XP lands straight away!</div></div>'
        f'<div style="font-size:56px">⏱️</div></div>'
        f'<div class="bar-wrap">{style.bar(done_today / len(todays) if todays else 1)}</div>'
        f'<div class="band">Today: {done_today} of {len(todays)} done · all of them = +{r["routine_day_bonus"]} XP · '
        f'every session all week = +{r["routine_week_bonus"]} XP</div>', "ar-hero")
    if not rq._runs_ok():
        st.caption(f"ℹ️ The timer only lives in this browser tab until Papa runs `{rq.SQL_FILE}` in Supabase.")

    run = rq.running(kid["id"])
    if run:
        _running(run, is_child)
    st.markdown(f"### Today · {rq.DAYS[day.weekday()]} {day.day} {day.strftime('%B')}")
    if not todays:
        style.card("🌈 <b>No routine today.</b> Enjoy your sport! 🏀🎾🏊")
    for b in todays:
        _block_card(b, day, dm.get((b["id"], str(day))), run, is_child, r)
    st.markdown("### This week")
    _week_strip(kid["id"], sett)


def _block_card(b, day, act, run, is_child, rules):
    icon, name = rq.SUBJECTS[b["kind"]]
    xp = rq.xp_for(b["kind"], b["minutes"], rules)
    full = bool(act and act["details"].get("full"))
    if full:
        state = f'✅ Done · {style.pill("+" + str(act["xp"]) + " XP", "ok")}'
    elif act:
        state = f'⏹ Stopped early ({act["minutes"]} min) · {style.pill("+" + str(act["xp"]) + " XP", "yel")}'
    elif run and run["block_id"] == b["id"]:
        state = "⏱️ Timer running…"
    else:
        state = f'⭕ Not done yet · {style.pill("worth " + str(xp) + " XP", "yel")}'
    st.markdown(
        f'<div class="ar-sport {b["kind"]}"><div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px">'
        f'<span style="font-size:1.15rem">{icon} {esc(b["title"])}</span>'
        f'<span>⏱ {b["minutes"]} min · 🕓 {esc(rq.time_label(b["time"]))}</span></div>'
        f'<div style="margin-top:4px">{state}</div></div>', unsafe_allow_html=True)
    if is_child and not run and not full:
        label = f"▶ Start my {b['minutes']}-min {name} timer" if not act else f"▶ Do the full {b['minutes']} min now"
        if st.button(label, key=f"go_{b['id']}", use_container_width=True):
            rq.start(b)
            st.rerun()


def _running(run, is_child):
    icon, name = rq.SUBJECTS[run["kind"]]
    left = rq.seconds_left(run)
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000) + left * 1000
    components.html(f"""
<div style="font-family:Nunito,sans-serif;text-align:center;background:#fff;border:4px solid #ffd60a;border-radius:24px;padding:14px">
<link href="https://fonts.googleapis.com/css2?family=Luckiest+Guy&display=swap" rel="stylesheet">
<div style="font-weight:800;color:#55678a">{icon} {esc(run['title'])} · {run['minutes']} min focus</div>
<div id="t" style="font-family:'Luckiest Guy',Nunito,sans-serif;font-size:64px;color:#1f4f8f;letter-spacing:2px">--:--</div>
<div id="m" style="font-weight:800;color:#1f3358">Phone down, brain on 🧠</div></div>
<script>
const end={end_ms};
function tick(){{
  const s=Math.max(0,Math.round((end-Date.now())/1000));
  document.getElementById('t').textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');
  if(s<=60&&s>0){{document.getElementById('m').textContent='One minute left. Finish your last question!';}}
  if(s===0){{document.getElementById('t').textContent="TIME'S UP! 🎉";
    document.getElementById('m').textContent="Tap \\"I'm done\\" below to collect your XP 🍌";return;}}
  setTimeout(tick,500);
}}
tick();
</script>""", height=165)
    if not is_child:
        st.caption("He has a session running.")
        return
    with st.form("rq_done", border=True):
        st.markdown(f"**When the timer rings:** what did you work on?")
        c1, c2 = st.columns([1, 1.4])
        topic = c1.selectbox("Topic", rq.TOPICS[run["kind"]], index=None, placeholder="Pick one")
        note = c2.text_input("What I did (optional)", placeholder="e.g. 2 pages of my book, fractions worksheet")
        ok = st.form_submit_button("✅ I'm done!", use_container_width=True)
    if ok:
        if rq.seconds_left(run) > 0:
            st.warning(f"⏱️ {rq.seconds_left(run) // 60 + 1} min still to go. Keep going, you've got this! "
                       "(Need to stop? Use 'Stop early' below.)")
        else:
            msgs = rq.finish(run, topic or "", note)
            if any("whole" in m.lower() or "week" in m.lower() for m in msgs):
                style.banana_burst()
            st.rerun()
    c1, c2 = st.columns(2)
    with c1.popover("⏹ Stop early", use_container_width=True):
        done = rq.minutes_done(run)
        st.caption(f"You've done {done} min. Stopping early gives XP for the minutes done "
                   f"(at least {rq.MIN_EARLY} min) but not the whole-day bonus.")
        why = st.radio("Why are you stopping?", EARLY_REASONS, index=None, key="rq_why")
        if st.button("Stop and save", key="rq_stop", disabled=not why):
            for m in rq.finish(run, "", "", why):
                st.toast(m)
            st.rerun()
    if c2.button("✖ Cancel (no XP)", key="rq_cancel", type="tertiary", use_container_width=True):
        rq.cancel(run)
        st.rerun()


def _week_strip(uid, sett):
    ws = g.week_start()
    s = rq.week_summary(uid, ws, sett)
    started = min((g.to_date(a["day"]) for a in rq.sessions(uid)), default=g.today())   # no "missed" before day 1
    cells = ""
    for i in range(7):
        d = ws + timedelta(days=i)
        bl = rq.day_blocks(d, s["blocks"])
        marks = ""
        for b in bl:
            a = s["map"].get((b["id"], str(d)))
            if a and a["details"].get("full"):
                marks += "✅"
            elif a:
                marks += "🟡"
            elif started <= d < g.today():
                marks += "▫️"
            elif d < started:
                marks += "·"
            else:
                marks += "⭕"
        star = " 🌟" if rq.day_complete(d, s["map"], s["blocks"]) else ""
        cells += (f'<div class="rq-day{" today" if d == g.today() else ""}"><div class="d">{rq.DAYS[i]} {d.day}{star}</div>'
                  f'<div class="s">{marks or "🌈"}</div></div>')
    st.markdown(f'<div class="rq-week">{cells}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ar-stat" style="margin-top:.6rem">'
        f'<div class="box"><div class="big">✅ {s["full"]}/{s["planned"]}</div><div class="lbl">sessions done</div></div>'
        f'<div class="box"><div class="big">🌟 {s["days_full"]}</div><div class="lbl">whole days</div></div>'
        f'<div class="box money"><div class="big">🍌 {s["xp"]}</div><div class="lbl">of {s["potential"]} XP possible</div></div>'
        '</div>', unsafe_allow_html=True)
    st.caption("✅ done · 🟡 stopped early · ⭕ still to do · ▫️ missed · 🌟 whole day done")


# ---------------------------------------------------------------- Home card
def home_card(kid, is_child):
    try:
        sett = data.settings()
        day = g.today()
        todays = rq.day_blocks(day, rq.blocks(sett))
        if not todays:
            return
        dm = rq.done_map(kid["id"], day, day)
        run = rq.running(kid["id"])
    except Exception:
        return
    marks = " ".join(("✅" if (dm.get((b["id"], str(day))) or {}).get("details", {}).get("full") else "⭕")
                     + f" {rq.SUBJECTS[b['kind']][0]} {esc(b['title'])}" for b in todays)
    done = sum(1 for b in todays if (dm.get((b["id"], str(day))) or {}).get("details", {}).get("full"))
    msg = ("⏱️ A timer is running!" if run else "All done today! 🎉" if done == len(todays)
           else f"{len(todays) - done} to go · +{sett['rules']['routine_day_bonus']} XP bonus for all of them")
    style.card(f'<div class="ar-title" style="font-size:1.15rem">🗓️ Today\'s routine</div>'
               f'<div style="font-weight:800;margin:4px 0">{marks}</div><div class="ar-small">{msg}</div>'
               f'<div style="margin-top:6px">{style.bar(done / len(todays), "ok" if done == len(todays) else "")}</div>')
    if st.button("⏱️ Open my routine" if is_child else "His routine", key="home_rq", use_container_width=True):
        nav.go("routine")


# ---------------------------------------------------------------- Parent Hub tab
def render_parent(kid):
    sett = data.settings()
    st.markdown("#### 🗓️ His daily routine")
    st.caption("Each session runs a timer on his device. When it rings he taps I'm done and the XP lands "
               "straight away (it also counts for his streak, the weekly maths goal and screen-time unlock). "
               "If something wasn't really done, take it back below.")
    _week_strip(kid["id"], sett)
    st.markdown("#### ✏️ The plan")
    rows = [{"id": b["id"], "subject": b["kind"], "name": b["title"], "minutes": b["minutes"], "time": b["time"],
             **{dn: i in b["days"] for i, dn in enumerate(rq.DAYS)}} for b in rq.blocks(sett)]
    df = pd.DataFrame(rows, columns=["id", "subject", "name", "minutes", "time"] + rq.DAYS)
    ed = st.data_editor(
        df, key="rq_plan", num_rows="dynamic", hide_index=True, use_container_width=True,
        column_config={
            "id": None,
            "subject": st.column_config.SelectboxColumn("subject", options=list(rq.SUBJECTS), required=True,
                                                        help="maths or english"),
            "name": st.column_config.TextColumn("name", help="What he sees, e.g. Reading time"),
            "minutes": st.column_config.NumberColumn("minutes", min_value=5, max_value=120, step=5, required=True),
            "time": st.column_config.TextColumn("time (HH:MM)", help="Rough start time, e.g. 16:30. Blank = any time"),
            **{dn: st.column_config.CheckboxColumn(dn, width="small") for dn in rq.DAYS},
        })
    c1, c2 = st.columns(2)
    if c1.button("💾 Save the routine", use_container_width=True):
        out, bad = [], []
        for _, row in ed.iterrows():
            kind = row.get("subject")
            if kind not in rq.SUBJECTS:
                continue
            t = str(row.get("time") or "").strip()
            if t:
                try:
                    hh, mm = t.replace(".", ":").split(":")
                    t = f"{int(hh):02d}:{int(mm):02d}"
                except ValueError:
                    bad.append(t)
                    t = ""
            rid = row.get("id")
            out.append({"id": rid if isinstance(rid, str) and rid else f"{kind}_{len(out)}",
                        "kind": kind, "title": str(row.get("name") or rq.SUBJECTS[kind][1]).strip(),
                        "minutes": int(row.get("minutes") or 25), "time": t,
                        "days": [i for i, dn in enumerate(rq.DAYS) if bool(row.get(dn))]})
        rq.save_blocks(out)
        st.session_state.pop("rq_plan", None)
        if bad:
            st.warning(f"Couldn't read the time {', '.join(bad)} (use 16:30), so it was left blank.")
        st.success("Routine saved ✅")
        st.rerun()
    if c2.button("↩️ Back to 25-min Maths + English every day", type="tertiary", use_container_width=True):
        rq.save_blocks(rq.DEFAULT_ROUTINE)
        st.session_state.pop("rq_plan", None)
        st.rerun()

    st.markdown("#### 🍌 Routine XP")
    r = sett["rules"]
    with st.form("rq_rules"):
        a, b, c = st.columns(3)
        mpm = a.number_input("Maths: XP per minute", 0, 20, int(r["maths_per_min"]))
        epm = b.number_input("English: XP per minute", 0, 20, int(r["english_per_min"]))
        ecap = c.number_input("English: max minutes that count", 5, 240, int(r["english_cap_min"]), 5)
        dayb = a.number_input("Whole day done: bonus", 0, 500, int(r["routine_day_bonus"]), 5)
        wkb = b.number_input("Whole week done: bonus", 0, 1000, int(r["routine_week_bonus"]), 5)
        if st.form_submit_button("Save routine XP"):
            data.save_settings({"rules": {**r, "maths_per_min": int(mpm), "english_per_min": int(epm),
                                          "english_cap_min": int(ecap), "routine_day_bonus": int(dayb),
                                          "routine_week_bonus": int(wkb)}})
            st.success("Saved ✅ New sessions use these numbers.")
            st.rerun()
    s = rq.week_summary(kid["id"], g.week_start(), data.settings())
    st.caption(f"With this plan a full week is worth about {s['potential']} XP (plus the weekly maths goal bonus). "
               f"Maths also uses 'max minutes' from Settings → Advanced (maths cap min = {r['maths_cap_min']}).")

    st.markdown("#### ↩️ Recent sessions")
    recent = sorted(rq.sessions(kid["id"], g.today() - timedelta(days=13)), key=lambda a: str(a.get("created_at")),
                    reverse=True)
    if not recent:
        st.caption("No routine sessions in the last two weeks yet.")
    for a in recent:
        icon, name = rq.SUBJECTS[a["kind"]]
        det = a.get("details") or {}
        extra = " · ".join(x for x in [det.get("topic"), a.get("note"), det.get("early_reason")] if x)
        c1, c2 = st.columns([4, 1], vertical_alignment="center")
        c1.markdown(f'{"✅" if det.get("full") else "🟡"} {icon} **{esc(name)}** · {esc(str(a["day"])[5:])} · '
                    f'{a["minutes"]} min · +{a["xp"]} XP' + (f' · _{esc(extra)}_' if extra else ""))
        with c2.popover("Take back", use_container_width=True):
            note = st.text_input("Note for Aadiv (optional)", key=f"rqn_{a['id']}")
            if st.button("Take back the XP", key=f"rqb_{a['id']}"):
                rq.take_back(a, note)
                st.rerun()

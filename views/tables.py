import time

import streamlit as st
import streamlit.components.v1 as components

from ar import data, gamify as g, style, tables as T
from ar.style import esc


def render():
    is_child = data.is_child()
    kid = data.fresh_child()
    sett = data.settings()
    rules = sett["rules"]
    focus = {int(x) for x in sett.get("tables_focus") or []}
    acts = data.activities(kid["id"])
    done = T.mastered(acts)
    best = T.best_by_table(acts)
    today_xp = data.tables_xp_today(kid["id"])
    cap = int(rules["tables_daily_cap"])

    st.markdown("# ✖️ Times Tables")
    st.markdown(
        '<div class="ar-sub">12 quick questions a round. Trickier tables earn more XP per answer, and a new table beats repeating one. '
        'Get all 12 right fast enough to <b>master</b> a table ⭐</div>', unsafe_allow_html=True)
    style.card(f'<div style="display:flex;justify-content:space-between;font-weight:800">'
               f'<span>🍌 Tables XP today</span><span>{today_xp} / {cap}</span></div>'
               f'<div style="margin-top:6px">{style.bar(today_xp / cap if cap else 1, "den")}</div>'
               + ('<div class="ar-small" style="margin-top:4px">Daily tables XP is full. Practising still '
                  'makes you faster for tomorrow!</div>' if cap and today_xp >= cap else ""))

    rnd = st.session_state.get("tt_round")
    if rnd and is_child:
        _play(rnd, rules, done, today_xp, focus, acts)
        return
    res = st.session_state.pop("tt_result", None)
    if res and is_child:
        _result(res)

    _picker(is_child, done, best, focus, acts)
    _recent(acts)


# ---------------------------------------------------------------- picker
def _picker(is_child, done, best, focus, acts):
    st.markdown("### Pick a table")
    if focus:
        st.markdown('<div class="ar-tip" style="font-weight:800">🎯 Papa\'s focus tables this week (double XP): '
                    + ", ".join(f"{n}×" for n in sorted(focus)) + "</div>", unsafe_allow_html=True)
    today = str(g.today())
    if not is_child:
        st.info("This is Aadiv's practice area. Stars show the tables he has mastered.")
    cols = st.columns(5)
    for i, n in enumerate(T.TABLES):
        b = best.get(n)
        star = "⭐" if n in done else ""
        sub = f"Best so far {b['best']}/12 over {b['rounds']} rounds" if b else "Not tried yet"
        f = T.repeat_factor(T.rounds_today(acts, n, today))
        per = T.q_value(n, done, focus) * f
        mark = "🎯" if n in focus else ""
        pay = "0 XP" if per == 0 else f"+{per:g} XP"
        label = f"{n}× {star}{mark}\n{pay}"
        if cols[i % 5].button(label, key=f"tt_pick_{n}", use_container_width=True, disabled=not is_child, help=sub,
                              type="tertiary" if n in done else "secondary"):
            _start(n)
    if st.button("🎲 Mixed round (2× to 15×)", use_container_width=True, disabled=not is_child, key="tt_mixed"):
        _start(None)
    st.caption("XP per answer depends on how tricky a table is: 1×, 2×, 5×, 10×, 11× = 1 · 3×, 4× = 2 · "
               "6×, 9×, 12× = 3 · 7×, 8× = 4 · 13×–15× = 5. The same table again today pays half, then nothing. "
               "Mastered ⭐ tables pay half; 🎯 focus tables pay double. "
               "Master a table: 12/12 in under 60 s (1×–10×) or 90 s (11×–15×) for a one-off +20.")


def _start(table):
    st.session_state.tt_round = {"table": table, "qs": T.make_round(table, seed=time.time()),
                                 "answers": [], "start": time.time(), "last": None}
    st.rerun()


# ---------------------------------------------------------------- playing
def _play(r, rules, done, today_xp, focus, acts):
    qs, answers = r["qs"], r["answers"]
    i = len(answers)
    title = f"{r['table']}× table" if r["table"] else "Mixed tables"
    right_so_far = sum(1 for q, a in zip(qs, answers) if a == q[0] * q[1])
    st.markdown(f"### {title} · question {i + 1} of {len(qs)}")
    st.markdown(style.bar(i / len(qs), "ok"), unsafe_allow_html=True)
    last = r.get("last")
    if last:
        q, a = last
        if a == q[0] * q[1]:
            st.markdown(f'<div class="ar-ok">✅ {q[0]} × {q[1]} = {q[0] * q[1]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ar-bad">❌ {q[0]} × {q[1]} = <b>{q[0] * q[1]}</b> '
                        f'(you said {esc(a if a is not None else "nothing")})</div>', unsafe_allow_html=True)
    a_, b_, flip = qs[i]
    x, y = (b_, a_) if flip else (a_, b_)
    st.markdown(f'<div class="ar-timer" style="font-size:4rem;margin:.4rem 0">{x} × {y} = ?</div>',
                unsafe_allow_html=True)
    with st.form(f"tt_q_{i}", clear_on_submit=True):
        ans = st.text_input("Answer", key=f"tt_ans_{i}", placeholder="Type the answer and press Enter",
                            label_visibility="collapsed")
        go = st.form_submit_button("Check ✔", use_container_width=True)
    # put the cursor in the answer box so he can just type
    components.html("""<script>setTimeout(function(){var d=window.parent.document;
      var el=d.querySelector('input[aria-label="Answer"]'); if(el){el.setAttribute('inputmode','numeric');el.focus();}},150);
      </script>""", height=0)
    st.caption(f"✅ {right_so_far} right so far · ⏱️ {int(time.time() - r['start'])} s")
    if st.button("Stop this round", type="tertiary", key="tt_quit"):
        st.session_state.pop("tt_round", None)
        st.rerun()
    if go:
        txt = (ans or "").strip()
        val = int(txt) if txt.isdigit() else None
        answers.append(val)
        r["last"] = ([a_, b_], val)
        if len(answers) == len(qs):
            secs = time.time() - r["start"]
            reps = T.rounds_today(acts, r["table"], str(g.today()))
            res = T.score_round(r["table"], qs, answers, secs, rules, done, today_xp, focus, reps)
            data.save_tables_round(r["table"], qs, answers, secs, res)
            res["seconds"] = secs
            res["table"] = r["table"]
            st.session_state.tt_result = res
            st.session_state.pop("tt_round", None)
        st.rerun()


# ---------------------------------------------------------------- results
def _result(res):
    if res["perfect"]:
        style.banana_burst()
    head = (f"⭐ You mastered the {res['table']}× table!" if res["new_master"]
            else "Perfect round! 🎉" if res["perfect"] else f"{res['right']} / {res['total']} right")
    lines = "".join(style.pill(f"{t} +{x}" if x else t, "den" if x else "yel") for t, x in res["lines"])
    capped = ('<div class="ar-small">Daily tables XP is full, so this round earned '
              f'{res["xp"]} of {res["raw"]} XP.</div>' if res["capped"] else "")
    wrong = ""
    if res["wrong"]:
        wrong = ('<div style="margin-top:8px;font-weight:800">Practise these:</div>'
                 + "".join(style.pill(f"{q[0]} × {q[1]} = {q[0] * q[1]}", "bad") for q, _ in res["wrong"]))
    style.card(f'<div class="ar-title" style="font-size:1.4rem">{head} · +{res["xp"]} XP</div>'
               f'<div class="ar-small">⏱️ {res["seconds"]:.0f} s</div>{lines}{capped}{wrong}',
               "ar-card ar-ok" if res["perfect"] else "ar-card")


def _recent(acts):
    rows = [a for a in acts if a.get("kind") == "tables"]
    rows.sort(key=lambda a: str(a.get("created_at")), reverse=True)
    if not rows:
        return
    body = ""
    for a in rows[:8]:
        d = a.get("details") or {}
        body += (f'<tr><td>{esc(str(a.get("day"))[5:])}</td><td>{esc(a.get("session_type"))}</td>'
                 f'<td class="n">{d.get("right")}/{d.get("total")}</td><td class="n">{d.get("seconds", 0):.0f} s</td>'
                 f'<td class="n">+{a.get("xp")}</td><td>{"⭐" if d.get("mastered") else ""}</td></tr>')
    style.card('<div class="ar-title" style="font-size:1.1rem">📋 Recent rounds</div>'
               '<table class="ar-table"><tr><th>Day</th><th>Table</th><th class="n">Score</th>'
               f'<th class="n">Time</th><th class="n">XP</th><th></th></tr>{body}</table>')

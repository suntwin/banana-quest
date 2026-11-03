"""🔤 Banana Words: a few new words a day, with reviews that come back and get harder.

His page: ✨ Today's words · 🏆 Weekly test · 📚 My words. Parent: render_parent(kid) (Parent Hub -> 🔤 Words).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ar import data, gamify as g, nav, style, vocab as vb
from ar.style import esc

CHEERS = ["Banana-tastic! 🍌", "Slam dunk! 🏀", "Ace! 🎾", "Splash-tastic! 🏊", "You got it! ⭐", "Awesome! 💛"]


def _sql_needed(e=None):
    st.warning(f"Banana Words needs its tables. Papa: run `{vb.SQL_FILE}` once in Supabase → SQL Editor, then reload."
               + (f"\n\n_({e})_" if e else ""))


def speak(text: str, key: str, label: str = "🔊 Hear it"):
    """A small read-aloud button (the browser's own voice, Australian English if available)."""
    t = json.dumps(text)
    components.html(
        f"""<button id="b" style="font:800 15px Nunito,system-ui,sans-serif;padding:6px 14px;border-radius:14px;
        border:3px solid #ffd60a;background:#fff;color:#1f3358;cursor:pointer">{esc(label)}</button>
        <script>
        document.getElementById('b').onclick = function() {{
          const u = new SpeechSynthesisUtterance({t});
          const v = speechSynthesis.getVoices().find(v => v.lang === 'en-AU') ||
                    speechSynthesis.getVoices().find(v => v.lang.startsWith('en'));
          if (v) u.voice = v;
          u.rate = 0.85; speechSynthesis.cancel(); speechSynthesis.speak(u);
        }};
        </script>""", height=46)


def _bold_word(sentence: str, word: str) -> str:
    s = esc(sentence or "")
    return re.sub(r"\b(" + re.escape(esc(word)) + r")\b", r"<b>\1</b>", s, count=1, flags=re.I)


def word_card(w: dict, big=True) -> str:
    size = "2.4rem" if big else "1.5rem"
    html = (f'<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap">'
            f'<span class="ar-title" style="font-size:{size}">{esc(w["word"])}</span>'
            f'{style.pill(w.get("pos") or "", "den")}</div>'
            f'<div style="font-size:1.2rem;font-weight:800;margin-top:6px">{esc(w["definition"])}</div>')
    if w.get("example"):
        html += f'<div style="margin-top:8px;font-size:1.1rem;font-style:italic">“{_bold_word(w["example"], w["word"])}”</div>'
    bits = []
    if w.get("synonyms"):
        bits.append("🤝 <b>Same as:</b> " + esc(", ".join(w["synonyms"])))
    if w.get("antonyms"):
        bits.append("↔️ <b>Opposite:</b> " + esc(", ".join(w["antonyms"])))
    if bits:
        html += '<div class="ar-small" style="margin-top:8px">' + " &nbsp;·&nbsp; ".join(bits) + "</div>"
    if w.get("hook"):
        html += f'<div class="ar-tip" style="margin-top:8px">💡 <b>Remember it:</b> {esc(w["hook"])}</div>'
    if w.get("confusable"):
        html += (f'<div class="ar-small" style="margin-top:6px">⚠️ Don\'t mix it up with '
                 f'<b>{esc(w["confusable"])}</b></div>')
    return html


def _say(w: dict) -> str:
    return f"{w['word']}. {w['definition']}. {w.get('example') or ''}"


# ====================================================================== his page
def render():
    if not data.is_child():
        st.markdown("# 🔤 His Words")
        render_parent(data.fresh_child())
        return
    try:
        wm = vb.word_map()
        plan = vb.plan_today()
    except vb.NotReady as e:
        st.markdown("# 🔤 Banana Words")
        _sql_needed(e)
        return
    if not wm:
        st.markdown("# 🔤 Banana Words")
        style.card("📦 Your word list isn't loaded yet. Ask Papa to load it in Parent Hub → 🔤 Words.")
        return
    prog = plan["prog"]
    sm = vb.summary(prog, len(wm))
    stk = vb.word_streak()
    st.markdown(
        f'<div class="ar-hero"><h1>🔤 Banana Words</h1>'
        f'<div class="sub">{sm["started"]} of {sm["total"]} words met · {sm["mastered"]} mastered · '
        f'{"🔥" if stk["current"] else "🌱"} {stk["current"]}-day word streak</div>'
        f'<div class="bar-wrap">{style.bar(sm["started"] / max(1, sm["total"]))}</div>'
        f'<div class="band">A few new words every day = a giant word brain 🧠</div></div>', unsafe_allow_html=True)
    st.write("")
    if st.session_state.pop("aw_burst", False):
        style.banana_burst()
    t_today, t_test, t_words = st.tabs(["✨ Today's words", "🏆 Weekly test", "📚 My words"])
    with t_today:
        _today(wm, plan)
    with t_test:
        _weekly_test(wm, prog)
    with t_words:
        _my_words(wm, prog)


# ---------------------------------------------------------------------- ✨ today
def _build_session(plan: dict, wm: dict) -> dict:
    items = [{"kind": "review", "wid": wid, "mode": vb.mode_for(plan["prog"][wid], wm[wid])}
             for wid in plan["due"] if wid in wm]
    for wid in plan["new"]:
        items += [{"kind": "learn", "wid": wid}, {"kind": "check", "wid": wid, "mode": "meaning"}]
    if plan["new"]:
        wrap = list(plan["new"])
        vb._seed("wrap", g.today()).shuffle(wrap)
        items += [{"kind": "wrap", "wid": wid, "mode": "reverse"} for wid in wrap]
    return {"day": str(g.today()), "items": items, "i": 0, "ans": None, "right": 0, "asked": 0, "retried": [],
            "n_due": len(plan["due"]), "n_new": len(plan["new"])}


def _today(wm: dict, plan: dict):
    vs = st.session_state.get("aw")
    if vs and vs["day"] != str(g.today()):
        vs = st.session_state["aw"] = None
    if not vs:
        n_due, n_new = len(plan["due"]), len(plan["new"])
        if not n_due and not n_new:
            if vb.done_today() or plan["started_today"] or len(plan["prog"]) < len(wm):
                if not vb.done_today():
                    vb.finish_day()
                style.card('<div class="ar-title" style="font-size:1.5rem">🎉 Today\'s words are done!</div>'
                           '<div class="ar-small">Come back tomorrow for new words. Try the 🏆 Weekly test '
                           'or look at 📚 My words.</div>', "ar-card ar-ok")
            else:
                style.card("🌈 Wow, you've met every single word!")
            return
        bits = []
        if n_due:
            bits.append(f"🔁 <b>{n_due}</b> to remember")
        if n_new:
            bits.append(f"✨ <b>{n_new}</b> new word{'s' if n_new != 1 else ''}")
        mins = max(3, round((n_due * 12 + n_new * 45) / 60))
        style.card(f'<div class="ar-title" style="font-size:1.45rem">Today\'s words</div>'
                   f'<div style="margin-top:6px;font-size:1.15rem">{" &nbsp;+&nbsp; ".join(bits)}</div>'
                   f'<div class="ar-small" style="margin-top:4px">About {mins} minutes · it counts for your streak '
                   f'and unlocks screen time 📺</div>')
        if st.button("Let's go! 🍌", use_container_width=True, key="aw_start"):
            st.session_state.aw = _build_session(plan, wm)
            st.rerun()
        return
    _play(vs, wm, plan["prog"])


def _play(vs, wm, prog):
    items = vs["items"]
    if vs["i"] >= len(items):
        _session_done(vs)
        return
    it = items[vs["i"]]
    w = wm.get(it["wid"])
    if not w:
        vs["i"] += 1
        st.rerun()
    step = {"review": "🔁 Remember it?", "learn": "✨ New word", "check": "✨ Quick check", "wrap": "🎁 Bonus round",
            "retry": "🔄 One more try"}[it["kind"]]
    st.markdown(f'<div class="ar-small">{step} · {vs["i"] + 1} of {len(items)}</div>', unsafe_allow_html=True)
    st.markdown(style.bar(vs["i"] / max(1, len(items)), "den"), unsafe_allow_html=True)
    if it["kind"] == "learn":
        style.card(word_card(w))
        speak(_say(w), key=f"aw_say_{vs['i']}")
        if st.button("Got it! Test me 👉", use_container_width=True, key=f"aw_learn_{vs['i']}"):
            vs["i"] += 1
            st.rerun()
        return
    q = vb.make_question(w, it["mode"], wm, salt=f"{it['kind']}{vs['i']}")
    if vs.get("ans") is None:
        _ask(vs, it, w, q, prog)
    else:
        _feedback(vs, it, w, q, vs["ans"])


def _ask(vs, it, w, q, prog):
    i = vs["i"]
    st.markdown(f'<div class="ar-small">{esc(vb.MODE_LABEL.get(q["mode"], ""))}</div>', unsafe_allow_html=True)
    if q["mode"] == "spell":
        style.card(f'<div style="font-size:1.15rem"><b>Meaning:</b> {esc(q["prompt"])}</div>'
                   + (f'<div style="margin-top:6px;font-style:italic">{esc(q["sentence"])}</div>' if q.get("sentence") else "")
                   + f'<div class="ar-small" style="margin-top:6px">Starts with <b>{esc(q["hint"])}</b></div>')
        speak(w["word"], key=f"aw_sp_{i}", label="🔊 Hear the word")
        with st.form(f"aw_spell_{i}"):
            typed = st.text_input("Type the word", key=f"aw_typed_{i}")
            ok = st.form_submit_button("Check ✔️", use_container_width=True)
        if ok and typed.strip():
            right, close = vb.check_spelling(typed, q["answer_text"])
            _record(vs, it, w, q["mode"], right, prog, chosen=typed.strip(), close=close)
        return
    st.markdown(f"### {q['prompt']}")
    for k, opt in enumerate(q["options"]):
        if st.button(opt, key=f"opt_a{i}_{k}", use_container_width=True, type="tertiary"):
            _record(vs, it, w, q["mode"], k == q["answer"], prog, chosen=opt)


def _record(vs, it, w, mode, right, prog, chosen="", close=False):
    wid = w["id"]
    tricky = False
    if it["kind"] == "review":
        p = prog.get(wid)
        if p:
            before = bool(p.get("leech"))
            vb.answer(p, mode, right)
            tricky = bool(p.get("leech")) and not before
    elif it["kind"] == "check":
        prog[wid] = vb.introduce(wid, right)
    else:
        vb.practice_log(wid, mode, right)
    vs["asked"] += 1
    vs["right"] += int(right)
    if not right and wid not in vs["retried"]:
        vs["retried"].append(wid)
        vs["items"].append({"kind": "retry", "wid": wid, "mode": "meaning" if mode != "meaning" else "reverse"})
    vs["ans"] = {"right": right, "chosen": chosen, "close": close, "tricky": tricky}
    st.rerun()


def _feedback(vs, it, w, q, ans):
    i = vs["i"]
    if ans["right"]:
        st.markdown(f'<div class="ar-ok">✅ {CHEERS[(i + len(w["word"])) % len(CHEERS)]}</div>', unsafe_allow_html=True)
    else:
        right_txt = q["answer_text"] if q["mode"] == "spell" else q["options"][q["answer"]]
        msg = "So close! Just one letter." if ans.get("close") else "Not quite!"
        st.markdown(f'<div class="ar-bad">❌ {msg} The answer is <b>{esc(right_txt)}</b>. '
                    f'It\'ll come back so you can get it next time 💪</div>', unsafe_allow_html=True)
    style.card(word_card(w, big=False))
    speak(_say(w), key=f"aw_fb_{i}")
    if ans.get("tricky"):
        st.info("🧩 This one's a tricky word! Say your own sentence with it out loud to Mum or Papa.")
    if st.button("Next ▶", use_container_width=True, key=f"aw_next_{i}"):
        vs["i"] += 1
        vs["ans"] = None
        st.rerun()


def _session_done(vs):
    if not vb.done_today():
        vb.finish_day(vs["n_new"], vs["n_due"], vs["right"], vs["asked"])
        st.session_state.aw_burst = True
        st.rerun()
    acc = vs["right"] / max(1, vs["asked"])
    stk = vb.word_streak()
    style.card(f'<div class="ar-title" style="font-size:1.6rem">🎉 Today\'s words: done!</div>'
               f'<div style="margin-top:6px;font-size:1.15rem">✨ {vs["n_new"]} new · 🔁 {vs["n_due"]} remembered · '
               f'🎯 {round(acc * 100)}% right</div>'
               f'<div class="ar-small" style="margin-top:6px">🔥 Word streak: {stk["current"]} day'
               f'{"s" if stk["current"] != 1 else ""} · screen time is unlocked for today 📺</div>', "ar-card ar-ok")
    if st.button("Back to the start", key="aw_reset", type="tertiary"):
        st.session_state.aw = None
        st.rerun()


# ---------------------------------------------------------------------- 🏆 weekly test
def _weekly_test(wm, prog):
    vt = st.session_state.get("awt")
    if not vt:
        try:
            revs = vb.reviews(days=30)
        except vb.NotReady:
            revs = []
        ready, why = vb.test_ready(prog, revs)
        style.card(f'<div class="ar-title" style="font-size:1.35rem">🏆 Weekly word test</div>'
                   f'<div class="ar-small">{vb.TEST_SIZE} questions on this week\'s words and some older ones. '
                   f'No hints until the end! +{vb.XP["test"]} XP plus 1 XP per right answer.</div>')
        if not ready:
            st.caption(why)
            return
        if st.button("Start the weekly test 🏁", use_container_width=True, key="awt_start"):
            st.session_state.awt = {"items": vb.build_test(prog), "i": 0, "res": []}
            st.rerun()
        return
    items = vt["items"]
    if vt["i"] >= len(items):
        right = sum(1 for r in vt["res"] if r["right"])
        if not vt.get("paid"):
            vb.finish_test(right, len(items))
            vt["paid"] = True
        style.card(f'<div class="ar-title" style="font-size:1.6rem">🏆 {right} / {len(items)}</div>'
                   f'<div class="ar-small">Words you missed come back tomorrow so you can learn them.</div>',
                   "ar-card ar-ok")
        st.dataframe(pd.DataFrame([{"": "✅" if r["right"] else "❌", "Word": r["word"], "You said": r["chosen"],
                                    "Answer": r["answer"]} for r in vt["res"]]),
                     hide_index=True, use_container_width=True)
        if st.button("Done 👍", key="awt_done"):
            st.session_state.awt = None
            st.rerun()
        return
    it = items[vt["i"]]
    w, p = wm.get(it["wid"]), prog.get(it["wid"])
    if not w or not p:
        vt["i"] += 1
        st.rerun()
    q = vb.make_question(w, it["mode"], wm, salt=f"test{vt['i']}")
    st.markdown(f'<div class="ar-small">Question {vt["i"] + 1} of {len(items)} · '
                f'{esc(vb.MODE_LABEL.get(q["mode"], ""))}</div>', unsafe_allow_html=True)
    st.markdown(style.bar(vt["i"] / len(items), "den"), unsafe_allow_html=True)

    def done(right, chosen, answer_txt):
        vb.answer(p, q["mode"], right, test=True)
        vt["res"].append({"right": right, "word": w["word"], "chosen": chosen, "answer": answer_txt})
        vt["i"] += 1
        st.rerun()

    if q["mode"] == "spell":
        st.markdown(f"**Meaning:** {q['prompt']}")
        st.caption(f"Starts with **{q['hint']}**")
        speak(w["word"], key=f"awt_sp_{vt['i']}", label="🔊 Hear the word")
        with st.form(f"awt_spell_{vt['i']}"):
            typed = st.text_input("Type the word", key=f"awt_typed_{vt['i']}")
            ok = st.form_submit_button("Next ▶", use_container_width=True)
        if ok and typed.strip():
            done(vb.check_spelling(typed, q["answer_text"])[0], typed.strip(), q["answer_text"])
        return
    st.markdown(f"### {q['prompt']}")
    for k, opt in enumerate(q["options"]):
        if st.button(opt, key=f"opt_t{vt['i']}_{k}", use_container_width=True, type="tertiary"):
            done(k == q["answer"], opt, q["options"][q["answer"]])


# ---------------------------------------------------------------------- 📚 my words
FILTERS = {"started": "All I've met", "tricky": "🧩 Tricky", "learning": "🌱 Learning", "strong": "💪 Strong",
           "mastered": "🏅 Mastered"}


def _my_words(wm, prog):
    c1, c2 = st.columns([2, 1])
    f = c1.segmented_control("Show", list(FILTERS), format_func=FILTERS.get, default="started", key="aww_f") or "started"
    qtxt = c2.text_input("Search", key="aww_q", placeholder="Find a word").strip().lower()
    rows = []
    for w in wm.values():
        p = prog.get(w["id"])
        if not p:
            continue
        stage = int(p.get("stage") or 1)
        keep = {"started": True, "tricky": bool(p.get("leech")), "learning": stage <= 3, "strong": 4 <= stage <= 5,
                "mastered": stage >= 6}[f]
        if keep and (not qtxt or qtxt in w["word"].lower()):
            rows.append((w, p))
    rows.sort(key=lambda x: str(x[1].get("introduced_on")), reverse=True)
    st.caption(f"{len(rows)} word(s)" + (" · showing the first 50" if len(rows) > 50 else ""))
    if not rows:
        style.card("Nothing here yet. Do today's words to fill your collection ✨")
    for w, p in rows[:50]:
        with st.expander(f"{w['word']} · {vb.STAGE_LABEL.get(int(p.get('stage') or 1))}"
                         + (" · 🧩 tricky" if p.get("leech") else "")):
            style.card(word_card(w, big=False))
            speak(_say(w), key=f"aww_say_{w['id']}")


# ====================================================================== Home card
def home_card(kid, is_child):
    try:
        if not vb.word_map():
            return
        plan = vb.plan_today(kid["id"])
        stk = vb.word_streak(kid["id"])
        done = vb.done_today(kid["id"])
    except Exception:
        return
    n_due, n_new = len(plan["due"]), len(plan["new"])
    if done and not n_due and not n_new:
        body = f'<div class="ar-small">✅ Done for today! 🔥 {stk["current"]}-day word streak</div>'
    else:
        body = f'<div class="ar-small">🔁 {n_due} to remember · ✨ {n_new} new · 🔥 {stk["current"]}-day streak</div>'
    style.card(f'<div class="ar-title" style="font-size:1.2rem">🔤 Today\'s words</div>{body}')
    if st.button("My words 🔤" if is_child else "His words 🔤", use_container_width=True, key="home_words"):
        nav.go("words")


# ====================================================================== parent
def render_parent(kid):
    try:
        wm = vb.word_map()
    except vb.NotReady as e:
        _sql_needed(e)
        return
    if not wm:
        _bank_loader(first=True)
        return
    try:
        prog = vb.progress(kid["id"])
        revs = vb.reviews(kid["id"], days=30)
    except vb.NotReady as e:
        _sql_needed(e)
        return
    sett = vb.settings()
    sm = vb.summary(prog, len(wm))
    stk = vb.word_streak(kid["id"])
    week = [r for r in revs if vb._d(r["day"]) >= g.today() - timedelta(days=6)]
    acc = (sum(1 for r in week if r["correct"]) / len(week)) if week else None
    c = st.columns(5)
    c[0].metric(f"Words met (of {sm['total']})", sm["started"])
    c[1].metric("Mastered", sm["mastered"])
    c[2].metric("Tricky words", sm["tricky"])
    c[3].metric("Right (7 days)", f"{acc * 100:.0f}%" if acc is not None else "—")
    c[4].metric("Word streak", f"{stk['current']} 🔥")
    fin = vb.finish_date(sm["not_started"], int(sett["new_per_day"]))
    st.caption(f"At {sett['new_per_day']} new words a day he meets every word by **{fin.strftime('%d %b %Y')}** · "
               f"{len(vb.due_ids(prog))} to remember today · today's words "
               f"{'✅ done' if vb.done_today(kid['id']) else 'not done yet'}")
    l, r = st.columns([1.3, 1])
    with l:
        st.markdown("**Last 14 days**")
        rows = []
        for k in range(13, -1, -1):
            d = g.today() - timedelta(days=k)
            dr = [x for x in revs if vb._d(x["day"]) == d]
            rev = [x for x in dr if x["mode"] != "learn" and not str(x["mode"]).startswith("practice_")]
            rows.append({"Day": d.strftime("%a %d %b"), "New": sum(1 for x in dr if x["mode"] == "learn"),
                         "Remembered": len(rev),
                         "Right": f"{round(100 * sum(1 for x in rev if x['correct']) / len(rev))}%" if rev else "—"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=300)
    with r:
        st.markdown("**🧩 Tricky words**")
        tricky = sorted([p for p in prog.values() if p.get("leech") or int(p.get("lapses") or 0) >= 2],
                        key=lambda p: -int(p.get("lapses") or 0))
        if not tricky:
            st.caption("None yet.")
        for p in tricky[:15]:
            w = wm.get(p["word_id"])
            if w:
                st.markdown(f"- **{w['word']}** ({p.get('lapses')} slips): {w['definition']}")
        modes = Counter(x["mode"].replace("test_", "") for x in revs if not x["correct"] and x["mode"] != "learn"
                        and not str(x["mode"]).startswith("practice_"))
        if modes:
            st.markdown("**Where he slips (30 days)**")
            st.caption(" · ".join(f"{vb.MODE_LABEL.get(m, m).rstrip('?')} ({n})" for m, n in modes.most_common(5)))
    st.divider()
    with st.expander("⚙️ Settings and word list"):
        n = st.slider("New words per day", 2, 12, int(sett["new_per_day"]), key="aw_per_day")
        if st.button("Save", key="aw_save_set"):
            vb.save_settings({"new_per_day": int(n)})
            st.success("Saved.")
        st.caption("When lots of words are due again, the app gives fewer new words that day so it stays short.")
        st.markdown(f"**Word list:** {len(wm)} words · " + " · ".join(
            f"{vb.LEVEL_LABEL[k]}: {v}" for k, v in sorted(Counter(int(w.get('level') or 1) for w in wm.values()).items())))
        _bank_loader(first=False)
        st.markdown("**🧹 Start his words again**")
        st.caption("Clears his word progress, answers, word XP, word days and word badges. The word list stays.")
        ok = st.checkbox("Yes, clear his Banana Words progress", key="aw_reset_ok")
        if st.button("Reset Banana Words", disabled=not ok, key="aw_reset_go"):
            vb.reset_progress(kid["id"])
            st.success("Done. He starts fresh with today's words.")


def _bank_loader(first: bool):
    bank = vb.bundled_bank()
    if first:
        st.info("📦 The word list isn't loaded yet. Load it once and he can start today.")
    if bank:
        n = len(bank.get("words") or [])
        if st.button(f"{'Load' if first else 'Reload'} the word list ({n} words) 📥", key=f"aw_load_{first}",
                     use_container_width=first):
            errs = vb.validate_bank(bank)
            if errs:
                st.error("; ".join(errs[:5]))
            else:
                with st.spinner("Loading words…"):
                    vb.load_bank(bank)
                st.success(f"Loaded {n} words.")
                st.rerun()
        st.caption(f"From the app: {bank.get('title')} ({bank.get('updated')}). Reloading keeps his progress.")

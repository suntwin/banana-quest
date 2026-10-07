from datetime import timedelta

import streamlit as st

from ar import data, gamify as g, style
from ar.style import esc

ORDER = ["basketball", "tennis", "swimming", "maths", "writing"]
EFFORT = {1: "😴 1", 2: "🙂 2", 3: "💪 3", 4: "🔥 4", 5: "🚀 5"}


def render():
    is_child = data.is_child()
    st.markdown("# ➕ Log it!")
    st.markdown('<div class="ar-sub">Did some training, maths or writing? Log it and earn XP. '
                + ("Papa checks it, then the XP lands in your bank." if data.settings()["approval"] == "parent"
                   else "XP lands straight in your bank.") + "</div>", unsafe_allow_html=True)
    if not is_child:
        st.info("You're logging for Aadiv. Anything a parent logs is approved straight away.")

    done = st.session_state.pop("just_logged", None)
    if done:
        style.banana_burst()
        lines = "".join(f"<li>{esc(t)}: <b>+{x}</b></li>" for t, x in done["lines"])
        pb = "".join(f" 🏅 New PB: {esc(p)}!" for p in done["pbs"])
        status = ("Waiting for Papa to check it ⏳" if done["status"] == "pending" else "In your bank! 🍌")
        style.card(f'<div class="ar-title" style="font-size:1.4rem">Banana-tastic! +{done["xp"]} XP{pb}</div>'
                   f'<ul style="margin:.4rem 0">{lines}</ul><div class="ar-small">{status}</div>', "ar-card ar-ok")

    order = g.active_kinds(data.settings()) or ORDER
    lk = st.session_state.pop("log_kind", None)
    if lk in order:
        st.session_state.log_pick = lk
    if st.session_state.get("log_pick") not in order:
        st.session_state.log_pick = order[0]
    kind = st.radio("What did you do?", order, horizontal=True,
                    format_func=lambda k: f"{g.KINDS[k]['icon']} {g.KINDS[k]['name']}", key="log_pick")

    k = g.KINDS[kind]
    st.markdown(f'<div class="ar-sport {kind}" style="font-size:1.3rem">{k["icon"]} {esc(k["name"])}</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    day = c1.date_input("When?", value=g.today(), min_value=g.today() - timedelta(days=7), max_value=g.today(),
                        format="DD/MM/YYYY", key=f"day_{kind}")
    details = {}
    if kind in g.SPORTS:
        stype = c2.selectbox("What kind of session?", k["types"], key=f"type_{kind}")
    elif kind == "maths":
        stype = c2.selectbox("What topic?", g.MATHS_TOPICS, key="type_maths")
    else:
        stype = c2.selectbox("What kind of writing?", g.WRITING_GENRES, key="type_writing")

    c3, c4 = st.columns(2)
    minutes = c3.slider("How many minutes?", 5, 180 if kind in g.SPORTS else 90,
                        60 if kind in g.SPORTS else 20, step=5, key=f"min_{kind}")
    effort = c4.select_slider("How hard did you try?", options=[1, 2, 3, 4, 5], value=3,
                              format_func=lambda v: EFFORT[v], key=f"eff_{kind}")

    if kind in g.SPORTS:
        st.markdown("**📊 Stats (fill in what you know. New records earn bonus XP!)**")
        fields = k["fields"]
        cols = st.columns(2)
        for i, f in enumerate(fields):
            key, lab, typ = f[0], f[1], f[2]
            col = cols[i % 2] if typ != "text" else st
            if typ == "int":
                v = col.number_input(lab, min_value=0, max_value=5000, value=None, step=1, key=f"{kind}_{key}")
            elif typ == "float":
                v = col.number_input(lab, min_value=0.0, max_value=600.0, value=None, step=0.1, format="%.1f",
                                     key=f"{kind}_{key}")
            elif typ == "select":
                v = col.selectbox(lab, f[3], key=f"{kind}_{key}")
            else:
                v = st.text_input(lab, key=f"{kind}_{key}")
            if v not in (None, ""):
                details[key] = v
        _warn_stats(kind, details)
    elif kind == "maths":
        details["topic"] = stype
        a, b, c = st.columns(3)
        details["source"] = a.selectbox("Where from?", g.MATHS_SOURCES, key="m_src")
        corr = b.number_input("Questions right", min_value=0, max_value=500, value=None, step=1, key="m_c")
        tot = c.number_input("Questions total", min_value=0, max_value=500, value=None, step=1, key="m_t")
        if corr is not None and tot:
            details["correct"], details["total"] = int(min(corr, tot)), int(tot)
    else:
        details["title"] = st.text_input("Title", key="w_title")
        txt = st.text_area("Paste or type your writing here (optional, Papa can read it)", height=160, key="w_text")
        auto = len(txt.split()) if txt.strip() else 0
        words = st.number_input("How many words?", min_value=0, max_value=5000, value=auto, step=10, key=f"w_words_{auto}",
                                help="Counted for you if you paste the text.")
        details["words"] = int(words)
        if txt.strip():
            details["text"] = txt.strip()
        details["genre"] = stype

    note = st.text_input("Anything else? (what went well, what was tricky)", key=f"note_{kind}")

    hist = data.activities()
    xp, lines, pbs = g.calc_xp(kind, stype, minutes, effort, details, hist, data.settings()["rules"])
    extra = " · Papa can add up to ⭐⭐⭐ bonus for great writing" if kind == "writing" else ""
    style.card(f'<div class="ar-title" style="font-size:1.2rem">🍌 You\'ll earn {xp} XP{extra}</div>'
               + "".join(style.pill(f"{t} +{x}", "den") for t, x in lines))

    ok = not (kind == "writing" and not details.get("title"))
    if st.button(f"Save it! +{xp} XP", use_container_width=True, disabled=not ok, key="save_log"):
        row = data.log_activity(kind, day, stype, minutes, effort, details, note)
        if not is_child:
            row = [a for a in data.activities() if a["id"] == row["id"]][0]
            if row.get("status") == "pending":
                data.approve(row)
                row["status"] = "approved"
        else:
            row = [a for a in data.activities() if a["id"] == row["id"]][0]
        st.session_state.just_logged = {"xp": row.get("xp", xp), "lines": lines, "pbs": pbs,
                                        "status": row.get("status")}
        for key in list(st.session_state.keys()):
            if key.startswith((f"{kind}_", "w_", "m_", f"note_{kind}")):
                del st.session_state[key]
        st.rerun()
    if not ok:
        st.caption("Give your writing a title first.")


def _warn_stats(kind, d):
    if kind == "basketball" and d.get("ft_made") and d.get("ft_att") and d["ft_made"] > d["ft_att"]:
        st.warning("Free throws made can't be more than free throws tried.")
        d["ft_att"] = d["ft_made"]
    if kind == "tennis" and d.get("serves_in") and d.get("serves_att") and d["serves_in"] > d["serves_att"]:
        st.warning("Serves in can't be more than serves tried.")
        d["serves_att"] = d["serves_in"]

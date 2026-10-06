from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ar import data, gamify as g, style
from ar.style import esc

COLORS = {"basketball": "#e8590c", "tennis": "#5c940d", "swimming": "#1864ab", "maths": "#6741d9",
          "writing": "#c2255c"}


def render():
    kid = data.fresh_child()
    s = data.stats(kid["id"])
    acts = [a for a in s["activities"] if a.get("status") != "rejected"]
    st.markdown("# 🏆 Trophy Room")
    t1, t2, t3, t4 = st.tabs(["🏅 Badges", "📈 Personal bests", "📊 My weeks", "🪜 Levels"])

    with t1:
        have = data.badges(kid["id"])
        st.markdown(f'<div class="ar-sub">{len(have)} of {len(g.BADGES)} badges collected</div>',
                    unsafe_allow_html=True)
        html = ""
        for k, ic, name, desc in g.BADGES:
            cls = "ar-badge" if k in have else "ar-badge locked"
            html += f'<div class="{cls}" title="{esc(desc)}"><div class="ic">{ic}</div>{esc(name)}' \
                    f'<div class="ar-small" style="font-size:.68rem">{esc(desc)}</div></div>'
        st.markdown(html, unsafe_allow_html=True)

    with t2:
        cols = st.columns(3)
        for col, kind in zip(cols, g.SPORTS):
            b = g.bests(kind, acts)
            sp = g.SPORTS[kind]
            body = "".join(
                f'<div style="padding:6px 0;border-bottom:1px solid #ffffff55"><div style="font-size:.85rem">'
                f'{esc(g.label(m))}</div><div style="font-size:1.6rem">{_fmt(v)}</div>'
                f'<div style="font-size:.75rem;opacity:.85">{esc(str(d)[5:] if d else "")}</div></div>'
                for m, (v, d) in b.items()) or '<div style="opacity:.9">No records yet. Add stats when you log!</div>'
            col.markdown(f'<div class="ar-sport {kind}"><div style="font-size:1.25rem">{sp["icon"]} {sp["name"]}</div>'
                         f'{body}</div>', unsafe_allow_html=True)
        _swim_chart(acts)

    with t3:
        _weeks_chart(acts)
        tot = {k: sum(int(a.get("minutes") or 0) for a in acts if a["kind"] == k) for k in g.SPORTS}
        st.markdown(
            '<div class="ar-stat">' + "".join(
                f'<div class="box"><div class="big">{g.SPORTS[k]["icon"]} {v // 60}h {v % 60}m</div>'
                f'<div class="lbl">{g.SPORTS[k]["name"]} all time</div></div>' for k, v in tot.items())
            + '</div>', unsafe_allow_html=True)

    with t4:
        lvl = s["level"]
        rows = ""
        for i, (need, name, icon) in enumerate(g.LEVELS):
            me_ = i + 1 == lvl["num"]
            done = s["wallet"]["earned"] >= need
            rows += (f'<tr style="{"background:#fff3b0;" if me_ else ""}{"" if done else "opacity:.5"}">'
                     f'<td>{i + 1}</td><td style="font-size:1.4rem">{icon}</td><td><b>{esc(name)}</b>'
                     f'{" ← you are here" if me_ else ""}</td><td class="n">{need} XP</td></tr>')
        style.card(f'<table class="ar-table"><tr><th>#</th><th></th><th>Level</th><th class="n">Lifetime XP</th></tr>'
                   f'{rows}</table><div class="ar-small" style="margin-top:6px">Levels use all the XP you have ever '
                   f'earned, so spending XP in the shop never drops your level.</div>')


def _fmt(v):
    return f"{v:g}"


def _weeks_chart(acts):
    wk0 = g.week_start() - timedelta(weeks=7)
    weeks = [wk0 + timedelta(weeks=i) for i in range(8)]
    fig = go.Figure()
    for kind in ["basketball", "tennis", "swimming", "maths"]:
        ys = []
        for wk in weeks:
            ys.append(sum(int(a.get("minutes") or 0) for a in acts if a["kind"] == kind
                          and wk <= g.to_date(a["day"]) < wk + timedelta(days=7)))
        fig.add_bar(x=[w.strftime("%d %b") for w in weeks], y=ys, name=g.KINDS[kind]["name"],
                    marker_color=COLORS[kind])
    fig.update_layout(barmode="stack", height=340, margin=dict(l=10, r=10, t=30, b=10),
                      title="Minutes per week (last 8 weeks)", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(255,255,255,.7)", legend=dict(orientation="h", y=-0.2),
                      font=dict(family="Nunito", color="#1f3358"))
    st.plotly_chart(fig, use_container_width=True)


def _swim_chart(acts):
    pts = [(g.to_date(a["day"]), float(a["details"]["best50_sec"])) for a in acts
           if a["kind"] == "swimming" and (a.get("details") or {}).get("best50_sec")]
    if len(pts) < 2:
        return
    df = pd.DataFrame(sorted(pts), columns=["day", "sec"])
    fig = go.Figure(go.Scatter(x=df["day"], y=df["sec"], mode="lines+markers", line=dict(color="#1864ab", width=3)))
    fig.update_layout(height=280, title="🏊 50 m time (lower is faster)", margin=dict(l=10, r=10, t=40, b=10),
                      yaxis=dict(autorange="reversed", title="seconds"), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(255,255,255,.7)", font=dict(family="Nunito", color="#1f3358"))
    st.plotly_chart(fig, use_container_width=True)

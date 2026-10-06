"""Banana Quest theme: yellow + denim, goggles and bananas. CSS + small HTML helpers."""
from __future__ import annotations

import html as _html

import streamlit as st

CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Luckiest+Guy&family=Baloo+2:wght@500;600;700;800&family=Nunito:wght@400;600;700;800&display=swap');

:root{
  --yel:#ffd60a; --yel2:#ffe766; --yel3:#fff6c2; --den:#2f6db5; --den2:#1f4f8f; --den3:#dce9fa;
  --ink:#1f3358; --ink2:#55678a; --goggle:#8a94a6; --card:#ffffffe0; --line:#f3e3a1;
  --ok:#1fae6b; --bad:#e8505b; --orange:#ff9f1c;
}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select{
  font-family:'Nunito', system-ui, sans-serif !important; color:var(--ink);
}
h2,h3,h4,.ar-title{font-family:'Baloo 2','Nunito',sans-serif !important; color:var(--ink); font-weight:800 !important}
h1{font-family:'Luckiest Guy','Baloo 2',sans-serif !important; letter-spacing:1px; color:var(--ink); font-weight:400 !important}
.stApp{
  background:
    radial-gradient(1000px 520px at 0% -10%, #fff1a8 0%, transparent 60%),
    radial-gradient(900px 600px at 110% 0%, #d7e6fb 0%, transparent 55%),
    linear-gradient(170deg,#fffbe6 0%,#fff8d6 45%,#eef4fd 100%) !important;
}
/* faint banana-dot pattern */
.stApp::before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0; opacity:.35;
  background-image:
    radial-gradient(3px 3px at 30px 40px,#ffd60a 50%,transparent 52%),
    radial-gradient(2px 2px at 150px 110px,#2f6db5 50%,transparent 52%),
    radial-gradient(3px 3px at 260px 30px,#ffb703 50%,transparent 52%),
    radial-gradient(2px 2px at 340px 190px,#8a94a6 50%,transparent 52%);
  background-size:380px 240px;
}
[data-testid="stAppViewContainer"] > .main, section.main, [data-testid="stMain"]{position:relative; z-index:1}
[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#ffe766 0%,#fff3b0 55%,#dce9fa 100%) !important; border-right:3px solid var(--den)}
.block-container{padding-top:1.6rem; max-width:1100px}

/* buttons: default = denim overalls with yellow text; tertiary = white pill */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:16px !important; font-weight:800 !important; min-height:2.9rem;
  position:relative; overflow:hidden; transition:transform .12s ease, box-shadow .12s ease;
}
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondaryFormSubmit"], button[data-testid="stBaseButton-primaryFormSubmit"]{
  border:0 !important; color:#fff !important; padding:.6rem 1.1rem !important;
  background:linear-gradient(180deg,#3d80cc 0%,var(--den) 55%,var(--den2) 100%) !important;
  box-shadow:0 6px 0 -1px #173c6d, 0 10px 18px -8px #1f4f8f99 !important;
}
button[data-testid^="stBaseButton-secondary"] p, button[data-testid^="stBaseButton-primary"] p{color:var(--yel) !important; font-weight:800 !important; font-size:1.04rem}
button[data-testid^="stBaseButton-secondary"]:hover, button[data-testid^="stBaseButton-primary"]:hover{transform:translateY(-2px)}
button[data-testid^="stBaseButton-secondary"]:active, button[data-testid^="stBaseButton-primary"]:active{transform:translateY(3px); box-shadow:0 2px 0 -1px #173c6d !important}
button[data-testid^="stBaseButton-secondary"]:disabled, button[data-testid^="stBaseButton-primary"]:disabled{filter:grayscale(.8); opacity:.55}
button[data-testid="stBaseButton-tertiary"]{
  background:#fff !important; border:3px solid var(--yel) !important; color:var(--ink) !important;
  padding:.6rem 1.1rem !important; box-shadow:0 4px 0 -1px #e6bf00 !important;
}
button[data-testid="stBaseButton-tertiary"] p{color:var(--ink) !important; font-weight:800 !important; font-size:1.02rem}
button[data-testid="stBaseButton-tertiary"]:hover{border-color:var(--den) !important; background:#fffbe6 !important}
.stTextInput input, .stTextArea textarea, .stNumberInput input{border-radius:14px !important; border:2px solid var(--line) !important; background:#fff !important}
[data-baseweb="select"]>div{border-radius:14px !important}
[data-testid="stExpander"]{border-radius:18px; border:2px solid var(--line); background:#ffffffcc}
div[data-testid="stTabs"] button p{font-family:'Baloo 2',sans-serif; font-size:1.08rem; font-weight:700}
[data-testid="stMetric"]{background:var(--card); border:2px solid var(--line); border-radius:18px; padding:.7rem .9rem}
[data-testid="stProgress"] > div > div > div > div{background:linear-gradient(90deg,var(--yel),#ffb703) !important}

/* cards */
.ar-card{background:var(--card); border:3px solid var(--line); border-radius:24px; padding:1.1rem 1.25rem;
  box-shadow:0 10px 26px -18px #1f4f8f88; margin-bottom:.9rem}
/* hero = a yellow top with a denim "overalls" band along the bottom */
.ar-hero{background:linear-gradient(180deg,#ffe14d 0%,#ffd60a 100%);
  border-radius:28px; padding:1.3rem 1.5rem 1.3rem; position:relative; overflow:hidden;
  box-shadow:0 18px 36px -20px #1f4f8faa; margin-bottom:1rem; border:3px solid #e6bf00}
.ar-hero h1{margin:0; font-size:2.1rem; color:var(--ink) !important}
.ar-hero .sub{font-weight:800; color:var(--ink)}
.ar-hero::after{content:"🍌 🍌 🍌"; position:absolute; right:18px; bottom:6px; font-size:20px; letter-spacing:4px}
.ar-hero .bar-wrap{margin-top:10px}
.ar-hero .band{color:#ffe766 !important; font-weight:800; font-size:.95rem; margin:14px -1.5rem -1.3rem; padding:.6rem 1.5rem 1.9rem; background:linear-gradient(180deg,#2f6db5,#1f4f8f)}
.ar-sub{color:var(--ink2); font-weight:700}
.ar-pill{display:inline-block; padding:.22rem .7rem; border-radius:999px; font-weight:800; font-size:.82rem;
  background:#fff; color:var(--ink); border:2px solid var(--line); margin:0 .3rem .3rem 0}
.ar-pill.yel{background:var(--yel3); border-color:#ffe066}
.ar-pill.den{background:var(--den3); border-color:#b4cdf0}
.ar-pill.ok{background:#dff7ea; border-color:#a6e6c4}
.ar-pill.bad{background:#ffe3e5; border-color:#ffb9be}
.ar-pill.grey{background:#eef0f4; border-color:#d6dae2}
.ar-stat{display:flex; gap:.8rem; flex-wrap:wrap}
.ar-stat .box{flex:1 1 140px; background:#ffffffe6; border:3px solid var(--line); border-radius:22px; padding:.8rem 1rem; text-align:center}
.ar-stat .box.money{background:linear-gradient(180deg,#fff7c7,#ffe766); border-color:#ffd60a}
.ar-stat .big{font-family:'Baloo 2',sans-serif; font-size:2rem; font-weight:800; line-height:1.1}
.ar-stat .lbl{font-weight:800; color:var(--ink2); font-size:.85rem}
.ar-bar{height:18px; border-radius:999px; background:#fff3b8; overflow:hidden; border:2px solid #fff; box-shadow:inset 0 0 0 2px #f3e3a1}
.ar-bar>span{display:block; height:100%; border-radius:999px;
  background:repeating-linear-gradient(45deg,#ffd60a 0 12px,#ffc300 12px 24px); animation:slide 1.2s linear infinite}
.ar-bar.den>span{background:repeating-linear-gradient(45deg,#3d80cc 0 12px,#2f6db5 12px 24px)}
.ar-bar.ok>span{background:repeating-linear-gradient(45deg,#33c47f 0 12px,#1fae6b 12px 24px)}
@keyframes slide{0%{background-position:0 0}100%{background-position:34px 0}}
.ar-tip{background:#fffbe0; border:3px dashed #ffd60a; border-radius:18px; padding:.7rem 1rem}
.ar-ok{background:#e4fff1; border:3px solid #a6e6c4; border-radius:20px; padding:.8rem 1rem; font-weight:800}
.ar-bad{background:#fff0f1; border:3px solid #ffb9be; border-radius:20px; padding:.8rem 1rem; font-weight:800}
.ar-badge{display:inline-flex; flex-direction:column; align-items:center; justify-content:center; width:112px; height:122px;
  margin:.3rem; border-radius:22px; background:linear-gradient(180deg,#fff 0%,#fff7cf 100%); border:3px solid var(--line);
  text-align:center; font-weight:800; font-size:.78rem; vertical-align:top; padding:.4rem}
.ar-badge .ic{font-size:2.1rem; line-height:1.2}
.ar-badge.locked{filter:grayscale(1); opacity:.38}
.ar-badge.new{animation:pop .8s ease; border-color:var(--den); box-shadow:0 0 0 4px #ffd60a99}
@keyframes pop{0%{transform:scale(.5)}70%{transform:scale(1.12)}100%{transform:scale(1)}}
.ar-reward{background:#fff; border:3px solid var(--line); border-radius:22px; padding:.9rem 1rem .6rem; text-align:center; min-height:252px; margin-bottom:.4rem}
.ar-reward .em{font-size:2.6rem; line-height:1.2}
.ar-reward .nm{font-family:'Baloo 2',sans-serif; font-weight:800; font-size:1.12rem}
.ar-reward .cost{display:inline-block; margin:.35rem 0; padding:.15rem .7rem; border-radius:999px; background:var(--yel); font-weight:800}
.ar-reward.goal{border-color:var(--den); box-shadow:0 0 0 4px #dce9fa}
.ar-sport{border-radius:22px; padding:.9rem 1rem; color:#fff; font-weight:800; margin-bottom:.6rem}
.ar-sport.basketball{background:linear-gradient(135deg,#ff8a3d,#e8590c)}
.ar-sport.tennis{background:linear-gradient(135deg,#a3d94a,#5c940d)}
.ar-sport.swimming{background:linear-gradient(135deg,#4dabf7,#1864ab)}
.ar-sport.maths{background:linear-gradient(135deg,#9775fa,#6741d9)}
.ar-sport.writing{background:linear-gradient(135deg,#f783ac,#c2255c)}
.ar-sport *{color:#fff !important}
.ar-small{font-size:.85rem; color:var(--ink2); font-weight:600}
.ar-timer{font-family:'Luckiest Guy',sans-serif; font-size:3.4rem; letter-spacing:2px; color:var(--den2); text-align:center}
.ar-table{width:100%; border-collapse:collapse; font-size:.92rem}
.ar-table th{font-family:'Baloo 2',sans-serif; text-align:left; color:var(--ink2); padding:.5rem; border-bottom:2px solid var(--line)}
.ar-table td{padding:.5rem; border-bottom:1px solid var(--line); vertical-align:top}
.ar-table .n{text-align:right; font-weight:800; white-space:nowrap}
@media (max-width: 640px){
  .ar-hero h1{font-size:1.5rem} .ar-stat .box{flex:1 1 42%} .ar-stat .big{font-size:1.5rem}
  .ar-badge{width:96px; height:112px}
}
</style>
"""


def apply():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(s) -> str:
    return _html.escape(str(s) if s is not None else "")


def card(body_html: str, cls: str = "ar-card"):
    st.markdown(f'<div class="{cls}">{body_html}</div>', unsafe_allow_html=True)


def bar(pct: float, cls: str = "") -> str:
    return f'<div class="ar-bar {cls}"><span style="width:{max(0, min(1, pct)) * 100:.1f}%"></span></div>'


def pill(text, color="yel") -> str:
    return f'<span class="ar-pill {color}">{esc(text)}</span>'


def xp_toasts():
    for amount, reason in st.session_state.pop("xp_toasts", []):
        st.toast(f"+{amount} XP · {reason}", icon="🍌")


def banana_burst():
    """Confetti of bananas & sports balls."""
    st.markdown(
        '<div class="ar-burst">' + "".join(
            f'<span style="left:{(i * 37) % 100}%;animation-delay:{(i % 7) * 0.12:.2f}s;font-size:{20 + (i * 7) % 18}px">'
            f'{"🍌⭐🏀🎾🏊💛🍌🥽"[i % 8]}</span>' for i in range(28)) + """</div>
<style>
.ar-burst{position:fixed; inset:0; pointer-events:none; z-index:9999; overflow:hidden}
.ar-burst span{position:absolute; top:-40px; animation:fall 2.6s ease-in forwards}
@keyframes fall{0%{transform:translateY(0) rotate(0); opacity:1}100%{transform:translateY(110vh) rotate(540deg); opacity:0}}
</style>""",
        unsafe_allow_html=True,
    )

"""Banana Quest: Aadiv's rewards app (sports first, plus maths and writing)."""
import streamlit as st

st.set_page_config(page_title="Banana Quest", page_icon="🍌", layout="wide",
                   initial_sidebar_state="auto")

from ar import style  # noqa: E402
from ar.store import get_store  # noqa: E402

style.apply()
store = get_store()


def login():
    st.markdown(
        '<div class="ar-hero" style="text-align:center">'
        '<div style="font-size:64px">🍌</div><h1>Banana Quest</h1>'
        '<div class="sub">Train hard, earn XP, swap it for awesome stuff!</div>'
        '<div class="band">🏀 🎾 🏊 🔢 ✍️</div></div>',
        unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        if store.demo:
            st.info("Demo mode (no Supabase keys yet). Pick who's playing.")
            c1, c2 = st.columns(2)
            if c1.button("🍌 I'm Aadiv", use_container_width=True):
                st.session_state.profile = store.sign_in("aadiv@demo", "")
                st.session_state.landing = True
                st.rerun()
            if c2.button("🧭 I'm Papa", use_container_width=True, type="tertiary"):
                st.session_state.profile = store.sign_in("papa@demo", "")
                st.session_state.landing = True
                st.rerun()
            return
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Let's go! 🍌", use_container_width=True):
                try:
                    prof = store.sign_in(email.strip(), pw)
                except Exception as e:  # bad credentials etc.
                    st.error(f"Hmm, that didn't work: {e}")
                else:
                    if prof:
                        st.session_state.profile = prof
                        st.session_state.landing = True
                        st.rerun()
                    st.error("Logged in, but no Banana Quest profile found. Run supabase/seed_family.sql.")


def logout():
    store.sign_out()
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


if "profile" not in st.session_state or not st.session_state.profile:
    login()
    st.stop()

from views import home, log, parent, shop, trophies  # noqa: E402

prof = st.session_state.profile
if prof["role"] == "child":
    pages = [
        st.Page(home.render, title="Home", icon="🏠", url_path="home", default=True),
        st.Page(log.render, title="Log it!", icon="➕", url_path="log"),
        st.Page(shop.render, title="Reward Shop", icon="🎁", url_path="shop"),
        st.Page(trophies.render, title="Trophy Room", icon="🏆", url_path="trophies"),
    ]
else:
    pages = [
        st.Page(parent.render, title="Parent Hub", icon="🧭", url_path="parent", default=True),
        st.Page(home.render, title="Aadiv's Home", icon="🏠", url_path="home"),
        st.Page(shop.render, title="Reward Shop", icon="🎁", url_path="shop"),
        st.Page(trophies.render, title="Trophy Room", icon="🏆", url_path="trophies"),
    ]

from ar import nav as _nav  # noqa: E402

_nav.PAGES.clear()
_nav.PAGES.update({p.url_path: p for p in pages})

with st.sidebar:
    st.markdown(f"### {prof.get('avatar', '🍌')} Hi, {prof['display_name']}!")
    if store.demo:
        st.caption("Demo mode · data stored locally")
nav = st.navigation(pages)
if st.session_state.pop("landing", False) and nav.url_path != pages[0].url_path:
    st.switch_page(pages[0])
with st.sidebar:
    st.divider()
    if st.button("Log out", type="tertiary", use_container_width=True):
        logout()
nav.run()
style.xp_toasts()

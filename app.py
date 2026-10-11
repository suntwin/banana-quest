"""Banana Quest: Aadiv's rewards app (sports first, plus maths and writing)."""
import streamlit as st

st.set_page_config(page_title="Banana Quest", page_icon="🍌", layout="wide",
                   initial_sidebar_state="auto")

from ar import remember, style  # noqa: E402
from ar.store import get_store  # noqa: E402

style.apply()
store = get_store()
if store is not None and not hasattr(store, "current_token"):
    # A login made before an app update can hold an older store object: rebuild it.
    st.session_state.pop("store", None)
    store = get_store()
if store is None:
    st.markdown('<div class="ar-hero" style="text-align:center"><div style="font-size:56px">🍌</div>'
                '<h1>Banana Quest</h1><div class="sub">Almost ready!</div><div class="band">Setup needed</div></div>',
                unsafe_allow_html=True)
    st.error("Supabase isn't connected yet. In Streamlit Cloud open **Manage app → Settings → Secrets** and add:\n\n"
             "```toml\nSUPABASE_URL = \"https://xxxx.supabase.co\"\nSUPABASE_ANON_KEY = \"eyJ...\"\n```\n\n"
             "Then save. The app restarts by itself.")
    st.stop()


def try_restore():
    """Silently log back in from the 'remember me' cookie (once per browser session)."""
    if st.session_state.get("restore_tried"):
        return
    st.session_state.restore_tried = True
    blob = remember.read()
    st.session_state.restore_status = "none" if not blob else "failed"
    if not blob:
        if remember.had_old_cookie():           # v1 cookie: tidy it away
            st.session_state.forget_cookie = True
        return
    prof = None
    try:
        if blob.startswith("demo:"):
            prof = store.restore(blob)
        else:
            creds = remember.unpack(blob)
            if creds:
                prof = store.sign_in(*creds)
    except Exception:
        prof = None
    if prof:
        st.session_state.profile = prof
        st.session_state.remember_blob = blob
        st.session_state.landing = True
        st.rerun()
    else:
        st.session_state.forget_cookie = True   # password changed or key changed: delete it


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
                st.session_state.remember_blob = "demo:aadiv@demo"
                st.session_state.landing = True
                st.rerun()
            if c2.button("🧭 I'm Papa", use_container_width=True, type="tertiary"):
                st.session_state.profile = store.sign_in("papa@demo", "")
                st.session_state.remember_blob = "demo:papa@demo"
                st.session_state.landing = True
                st.rerun()
            return
        status = st.session_state.get("restore_status")
        if status == "failed":
            st.caption("This device had a saved login, but it no longer works (password changed?). Please log in again.")
        with st.form("login"):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            keep = st.checkbox("Remember me on this device (30 days)", value=True)
            if st.form_submit_button("Let's go! 🍌", use_container_width=True):
                try:
                    prof = store.sign_in(email.strip(), pw)
                except Exception as e:  # bad credentials etc.
                    st.error(f"Hmm, that didn't work: {e}")
                else:
                    if prof:
                        st.session_state.profile = prof
                        st.session_state.remember_blob = remember.pack(email.strip(), pw) if keep else None
                        st.session_state.landing = True
                        st.rerun()
                    st.error("Logged in, but no Banana Quest profile found. Run supabase/seed_family.sql.")


def logout():
    store.sign_out()
    for k in list(st.session_state.keys()):
        if k != "store":
            del st.session_state[k]
    st.session_state.restore_tried = True    # don't log straight back in from the old cookie
    st.session_state.forget_cookie = True
    st.rerun()


if "profile" not in st.session_state or not st.session_state.profile:
    if st.session_state.pop("forget_cookie", False):
        remember.forget()
    try_restore()
    login()
    st.stop()

from views import home, log, parent, shop, tables, trophies  # noqa: E402

prof = st.session_state.profile
if prof["role"] == "child":
    pages = [
        st.Page(home.render, title="Home", icon="🏠", url_path="home", default=True),
        st.Page(log.render, title="Log it!", icon="➕", url_path="log"),
        st.Page(tables.render, title="Times Tables", icon="✖️", url_path="tables"),
        st.Page(shop.render, title="Reward Shop", icon="🎁", url_path="shop"),
        st.Page(trophies.render, title="Trophy Room", icon="🏆", url_path="trophies"),
    ]
else:
    pages = [
        st.Page(parent.render, title="Parent Hub", icon="🧭", url_path="parent", default=True),
        st.Page(home.render, title="Aadiv's Home", icon="🏠", url_path="home"),
        st.Page(tables.render, title="Times Tables", icon="✖️", url_path="tables"),
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
    st.caption("🔒 Remembered on this device" if st.session_state.get("remember_blob")
               else "Not remembered on this device")
nav = st.navigation(pages)
if st.session_state.pop("landing", False) and nav.url_path != pages[0].url_path:
    st.switch_page(pages[0])
with st.sidebar:
    st.divider()
    if st.button("Log out", type="tertiary", use_container_width=True,
                 help="Also makes this device forget the login"):
        logout()
nav.run()
style.xp_toasts()
# 'Remember me': (re)write the login cookie on every page view. Done last, so a quick
# page switch can't cut it off; the value never changes, so writing it again is harmless.
if st.session_state.get("remember_blob"):
    try:
        remember.save(st.session_state.remember_blob)
    except Exception:
        pass

"""'Remember me': keep the login in a browser cookie so a refresh, a new tab or the
next day doesn't ask for the password again.

v2 (2026-10-11). The first version saved Supabase's *refresh token*. Supabase swaps that
token for a new one every time it is used or auto-refreshed, so the cookie kept going stale
(and re-using an old token can make Supabase cancel the login), which is why Aadiv kept being
logged out. Now the cookie holds the login itself, *encrypted* with a server-side key
(Fernet / AES). The browser only ever sees scrambled text, the key never leaves the server,
and the value never changes, so it can't go stale.

- The key comes from the COOKIE_SECRET secret, or is derived from SUPABASE_ANON_KEY if that
  isn't set. Changing either logs every device out once.
- The cookie is re-written on every page view, so it keeps renewing while he uses the app.
  (iPad Safari caps cookies made by a page script at 7 days, so on the iPad it lasts as long
  as he opens the app at least once a week.)
- Log out deletes it. Changing the password also stops it working.
"""
from __future__ import annotations

import base64
import hashlib
import json
from urllib.parse import unquote

import streamlit as st
import streamlit.components.v1 as components

COOKIE = "bq_login"
OLD_COOKIE = "bq_remember"     # v1 cookie, removed on sight
DAYS = 30


# ---------------------------------------------------------------- encryption
def _fernet():
    try:
        from cryptography.fernet import Fernet
    except Exception:          # library missing: 'remember me' quietly switches off
        return None
    secret = None
    try:
        secret = st.secrets.get("COOKIE_SECRET") or st.secrets.get("SUPABASE_ANON_KEY")
    except Exception:
        pass
    secret = secret or "banana-quest-demo-only"
    key = base64.urlsafe_b64encode(hashlib.sha256(("bq-remember-v2|" + str(secret)).encode()).digest())
    return Fernet(key)


def pack(email: str, password: str) -> str | None:
    f = _fernet()
    if not f:
        return None
    return f.encrypt(json.dumps({"e": email, "p": password, "v": 2}).encode()).decode()


def unpack(blob: str) -> tuple[str, str] | None:
    f = _fernet()
    if not f or not blob:
        return None
    try:
        d = json.loads(f.decrypt(blob.encode()).decode())
        return d["e"], d["p"]
    except Exception:
        return None


# ---------------------------------------------------------------- cookie read / write
def read() -> str | None:
    try:
        v = st.context.cookies.get(COOKIE)
    except Exception:
        return None
    return unquote(v) if v else None


def had_old_cookie() -> bool:
    try:
        return bool(st.context.cookies.get(OLD_COOKIE))
    except Exception:
        return False


def _js(name: str, value: str, max_age: int) -> str:
    return (f"d.cookie={json.dumps(name)}+'='+encodeURIComponent({json.dumps(value)})"
            f"+'; Max-Age={int(max_age)}; Path=/; SameSite=Lax'+secure;")


def _run(statements: str):
    # The component iframe is same-origin with the app page, so it can set the app's cookie.
    html = ("<script>(function(){try{var d=window.parent.document;"
            "var secure=window.parent.location.protocol==='https:'?'; Secure':'';"
            + statements + "}catch(e){}})();</script>")
    if hasattr(st, "iframe"):          # newer Streamlit (components.html is being retired)
        st.iframe(html, height=1)
    else:
        components.html(html, height=0)


def save(value: str):
    _run(_js(COOKIE, value, DAYS * 86400) + _js(OLD_COOKIE, "", 0))


def forget():
    _run(_js(COOKIE, "", 0) + _js(OLD_COOKIE, "", 0))

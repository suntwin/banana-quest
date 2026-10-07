"""'Remember me': keep a login token in a browser cookie so a refresh or a new visit
doesn't ask for the password again.

The cookie holds the Supabase *refresh token* (not the password). It is read on the
server with st.context.cookies and written from a tiny invisible script. It lasts
30 days; logging out deletes it and ends that login on the server.
"""
from __future__ import annotations

import json
from urllib.parse import unquote

import streamlit as st
import streamlit.components.v1 as components

COOKIE = "bq_remember"
DAYS = 30


def read() -> str | None:
    try:
        v = st.context.cookies.get(COOKIE)
    except Exception:
        return None
    return unquote(v) if v else None


def _set(value: str, max_age: int):
    # The component iframe is same-origin with the app page, so it can set the app's cookie.
    js = (
        "<script>(function(){var d=window.parent.document;"
        "var secure=window.parent.location.protocol==='https:'?'; Secure':'';"
        f"d.cookie={json.dumps(COOKIE)}+'='+encodeURIComponent({json.dumps(value)})"
        f"+'; Max-Age={int(max_age)}; Path=/; SameSite=Lax'+secure;}})();</script>"
    )
    components.html(js, height=0)


def save(value: str):
    _set(value, DAYS * 86400)


def forget():
    _set("", 0)

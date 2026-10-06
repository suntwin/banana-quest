"""Data store: Supabase in production, a local JSON file in demo mode.

Same tiny table API as Selective Brain:
    select(table, eq=None, order=None, desc=False, limit=None) -> list[dict]
    insert(table, row) -> dict
    upsert(table, row, on_conflict) -> dict
    update(table, eq, fields) -> None
    delete(table, eq) -> None

In Supabase every table is prefixed with ``ar_`` (ar_profiles, ar_activities ...)
so this app can live in the SAME Supabase project as Selective Brain without
touching any of Siyonah's tables.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

PREFIX = "ar_"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------
# Supabase backend
# ----------------------------------------------------------------------------
class SupabaseStore:
    demo = False

    def __init__(self, url: str, key: str):
        from supabase import create_client

        self.client = create_client(url, key)

    def _t(self, table):
        return self.client.table(PREFIX + table)

    # --- auth ---
    def sign_in(self, email: str, password: str) -> dict | None:
        res = self.client.auth.sign_in_with_password({"email": email, "password": password})
        if not res or not res.user:
            return None
        rows = self.select("profiles", eq={"id": res.user.id})
        return rows[0] if rows else None

    def sign_out(self):
        try:
            self.client.auth.sign_out()
        except Exception:
            pass

    # --- tables ---
    def select(self, table, eq=None, order=None, desc=False, limit=None):
        q = self._t(table).select("*")
        for k, v in (eq or {}).items():
            q = q.eq(k, v)
        if order:
            q = q.order(order, desc=desc)
        if limit:
            q = q.limit(limit)
        return q.execute().data or []

    def insert(self, table, row):
        res = self._t(table).insert(row).execute()
        return (res.data or [row])[0]

    def upsert(self, table, row, on_conflict):
        res = self._t(table).upsert(row, on_conflict=on_conflict).execute()
        return (res.data or [row])[0]

    def update(self, table, eq, fields):
        q = self._t(table).update(fields)
        for k, v in eq.items():
            q = q.eq(k, v)
        q.execute()

    def delete(self, table, eq):
        q = self._t(table).delete()
        for k, v in eq.items():
            q = q.eq(k, v)
        q.execute()


# ----------------------------------------------------------------------------
# Local JSON backend (demo / offline testing)
# ----------------------------------------------------------------------------
_LOCK = threading.Lock()
_ID_TABLES = {"families", "activities", "xp_events", "rewards", "redemptions"}
TABLES = ["families", "profiles", "settings", "activities", "xp_events", "rewards",
          "redemptions", "badges"]


class LocalStore:
    demo = True

    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            self._write(self._seed())

    def _seed(self):
        from .gamify import DEFAULT_REWARDS

        fam = str(uuid.uuid4())
        kid, dad = str(uuid.uuid4()), str(uuid.uuid4())
        data = {t: [] for t in TABLES}
        data["families"].append({"id": fam, "name": "Demo family"})
        data["profiles"] += [
            {"id": kid, "family_id": fam, "display_name": "Aadiv", "role": "child",
             "avatar": "🍌", "email": "aadiv@demo", "goal_reward_id": None},
            {"id": dad, "family_id": fam, "display_name": "Papa", "role": "parent",
             "avatar": "🧭", "email": "papa@demo", "goal_reward_id": None},
        ]
        for r in DEFAULT_REWARDS:
            data["rewards"].append({"id": str(uuid.uuid4()), "family_id": fam, "active": True,
                                    "created_at": now_iso(), **r})
        return data

    def _read(self):
        with _LOCK:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data):
        with _LOCK:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
            os.replace(tmp, self.path)

    # --- auth (demo: e-mail picks the profile, any password) ---
    def sign_in(self, email, password):
        for p in self._read()["profiles"]:
            if p.get("email") == email:
                return p
        return None

    def sign_out(self):
        pass

    # --- tables ---
    @staticmethod
    def _match(row, eq):
        return all(row.get(k) == v for k, v in (eq or {}).items())

    def select(self, table, eq=None, order=None, desc=False, limit=None):
        rows = [r for r in self._read().get(table, []) if self._match(r, eq)]
        if order:
            rows.sort(key=lambda r: (r.get(order) is None, str(r.get(order))), reverse=desc)
        return rows[:limit] if limit else rows

    def insert(self, table, row):
        data = self._read()
        row = dict(row)
        if table in _ID_TABLES:
            row.setdefault("id", str(uuid.uuid4()))
        row.setdefault("created_at", now_iso())
        data.setdefault(table, []).append(row)
        self._write(data)
        return row

    def upsert(self, table, row, on_conflict):
        keys = [k.strip() for k in on_conflict.split(",")]
        data = self._read()
        for r in data.setdefault(table, []):
            if all(r.get(k) == row.get(k) for k in keys):
                r.update(row)
                self._write(data)
                return r
        self._write(data)
        return self.insert(table, row)

    def update(self, table, eq, fields):
        data = self._read()
        for r in data.get(table, []):
            if self._match(r, eq):
                r.update(fields)
        self._write(data)

    def delete(self, table, eq):
        data = self._read()
        data[table] = [r for r in data.get(table, []) if not self._match(r, eq)]
        self._write(data)


# ----------------------------------------------------------------------------
def get_store():
    """One store per browser session (Supabase auth token lives on the client)."""
    if "store" not in st.session_state:
        url = key = None
        try:
            url = st.secrets.get("SUPABASE_URL")
            key = st.secrets.get("SUPABASE_ANON_KEY")
        except Exception:
            pass
        if url and key:
            st.session_state.store = SupabaseStore(url, key)
        else:
            path = Path(__file__).resolve().parent.parent / ".demo_data.json"
            st.session_state.store = LocalStore(str(path))
    return st.session_state.store

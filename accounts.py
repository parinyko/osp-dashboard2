# -*- coding: utf-8 -*-
"""Logins for the OSP dashboard (and the Monthly Report on the same domain).

SQLite file (AUTH_DB). One device per account: a user who is signed in somewhere cannot sign
in on another device until they sign out there, or an admin releases the device.
The browser's device id (a long-lived cookie) lets the same browser sign in again after its
session cookie is lost. Admins are not limited to one device.

Tables
  companies(id, name, active)
  users(id, username, password_hash, display_name, company_id, role 'user'|'admin', active, created_at, last_login_at)
  sessions(token_hash, user_id, device_id, device_label, ip, created_at, last_seen_at)
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
AUTH_DB = Path(os.environ.get("AUTH_DB", BASE_DIR / "auth.db"))
SESSION_COOKIE = "osp_sid"
DEVICE_COOKIE = "osp_did"
DEFAULT_COMPANIES = ["DMP", "Origin", "Ex-Press", "3BB", "NY CABLE", "AIS"]
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")

_init_lock = threading.Lock()
_ready = False


def _db():
    con = sqlite3.connect(AUTH_DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init():
    """Create tables, default companies and the first admin (ADMIN_USERNAME / ADMIN_PASSWORD)."""
    global _ready
    with _init_lock:
        if _ready:
            return
        AUTH_DB.parent.mkdir(parents=True, exist_ok=True)
        with _db() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE, active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '', company_id INTEGER REFERENCES companies(id),
                role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')), active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL, last_login_at INTEGER);
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                device_id TEXT NOT NULL DEFAULT '', device_label TEXT NOT NULL DEFAULT '', ip TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL, last_seen_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
            """)
            if not con.execute("SELECT 1 FROM companies LIMIT 1").fetchone():
                con.executemany("INSERT INTO companies(name) VALUES (?)", [(c,) for c in DEFAULT_COMPANIES])
            admin_user = os.environ.get("ADMIN_USERNAME", "").strip()
            admin_pw = os.environ.get("ADMIN_PASSWORD", "")
            if admin_user and admin_pw and not con.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone():
                con.execute("INSERT INTO users(username, password_hash, display_name, role, created_at) VALUES (?,?,?,?,?)",
                            (admin_user, generate_password_hash(admin_pw), "ผู้ดูแลระบบ", "admin", int(time.time())))
        _ready = True


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def device_label(user_agent):
    """'Chrome · Windows' style label from a User-Agent, so people recognise the other device."""
    ua = user_agent or ""
    os_name = next((n for k, n in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"), ("Windows", "Windows"),
                                   ("Mac OS X", "Mac"), ("Linux", "Linux")) if k in ua), "อุปกรณ์อื่น")
    browser = next((n for k, n in (("Edg/", "Edge"), ("OPR/", "Opera"), ("SamsungBrowser", "Samsung Internet"),
                                   ("Line/", "LINE"), ("Chrome/", "Chrome"), ("Firefox/", "Firefox"), ("Safari/", "Safari"))
                    if k in ua), "เบราว์เซอร์")
    return f"{browser} · {os_name}"


# ---------------------------------------------------------------- sign in / out

class LoginError(Exception):
    def __init__(self, message, other_device=None):
        super().__init__(message)
        self.message = message
        self.other_device = other_device


def login(username, password, device_id, user_agent, ip):
    """New session token for a correct username/password, honouring the one-device rule."""
    init()
    now = int(time.time())
    with _db() as con:
        u = con.execute("""SELECT u.*, c.active AS company_active FROM users u
                           LEFT JOIN companies c ON c.id = u.company_id WHERE u.username = ?""",
                        (str(username or "").strip(),)).fetchone()
        if not u or not check_password_hash(u["password_hash"], password or ""):
            raise LoginError("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        if not u["active"] or (u["company_id"] and u["company_active"] == 0):
            raise LoginError("บัญชีนี้ถูกปิดการใช้งาน ติดต่อผู้ดูแลระบบ")
        if u["role"] != "admin":
            other = con.execute("SELECT * FROM sessions WHERE user_id = ? AND device_id != ?",
                                (u["id"], device_id or "")).fetchone()
            if other:
                raise LoginError("บัญชีนี้กำลังใช้งานอยู่ที่เครื่องอื่น — ออกจากระบบที่เครื่องเดิมก่อน "
                                 "หรือให้ผู้ดูแลระบบปลดเครื่องให้",
                                 other_device={"label": other["device_label"], "last_seen": other["last_seen_at"]})
            # same browser signing in again: replace its old session
            con.execute("DELETE FROM sessions WHERE user_id = ?", (u["id"],))
        token = secrets.token_urlsafe(32)
        con.execute("""INSERT INTO sessions(token_hash, user_id, device_id, device_label, ip, created_at, last_seen_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (_hash(token), u["id"], device_id or "", device_label(user_agent), ip or "", now, now))
        con.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, u["id"]))
    return token


def logout(token):
    if not token:
        return
    init()
    with _db() as con:
        con.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash(token),))


def current_user(token, touch=True):
    """The signed-in user for a session token, or None. Refreshes last_seen at most once a minute."""
    if not token:
        return None
    init()
    now = int(time.time())
    with _db() as con:
        r = con.execute("""SELECT s.token_hash, s.last_seen_at, u.id, u.username, u.display_name, u.role, u.active,
                                  c.name AS company, c.active AS company_active
                           FROM sessions s JOIN users u ON u.id = s.user_id
                           LEFT JOIN companies c ON c.id = u.company_id WHERE s.token_hash = ?""",
                        (_hash(token),)).fetchone()
        if not r or not r["active"] or r["company_active"] == 0:
            return None
        if touch and now - r["last_seen_at"] > 60:
            con.execute("UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?", (now, r["token_hash"]))
    return {"id": r["id"], "username": r["username"], "name": r["display_name"] or r["username"],
            "role": r["role"], "company": r["company"] or ""}


# ---------------------------------------------------------------- admin

def list_users():
    init()
    with _db() as con:
        rows = con.execute("""SELECT u.id, u.username, u.display_name, u.role, u.active, u.created_at, u.last_login_at,
                                     c.id AS company_id, c.name AS company,
                                     (SELECT COUNT(*) FROM sessions s WHERE s.user_id = u.id) AS sessions,
                                     (SELECT device_label FROM sessions s WHERE s.user_id = u.id ORDER BY last_seen_at DESC LIMIT 1) AS device,
                                     (SELECT last_seen_at FROM sessions s WHERE s.user_id = u.id ORDER BY last_seen_at DESC LIMIT 1) AS last_seen
                              FROM users u LEFT JOIN companies c ON c.id = u.company_id
                              ORDER BY u.role DESC, c.name, u.username""").fetchall()
    return [dict(r) for r in rows]


def list_companies():
    init()
    with _db() as con:
        rows = con.execute("""SELECT c.id, c.name, c.active, (SELECT COUNT(*) FROM users u WHERE u.company_id = c.id) AS users
                              FROM companies c ORDER BY c.name""").fetchall()
    return [dict(r) for r in rows]


def add_company(name):
    name = re.sub(r"\s+", " ", str(name or "")).strip()
    if not 1 <= len(name) <= 60:
        raise ValueError("ชื่อบริษัทต้องยาว 1–60 ตัวอักษร")
    init()
    try:
        with _db() as con:
            con.execute("INSERT INTO companies(name) VALUES (?)", (name,))
    except sqlite3.IntegrityError:
        raise ValueError(f"มีบริษัท {name} อยู่แล้ว")


def set_company_active(company_id, active):
    init()
    with _db() as con:
        con.execute("UPDATE companies SET active = ? WHERE id = ?", (1 if active else 0, int(company_id)))
        if not active:   # everyone in a closed company is signed out
            con.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE company_id = ?)", (int(company_id),))


def _check_password(pw):
    if len(pw or "") < 6:
        raise ValueError("รหัสผ่านต้องยาวอย่างน้อย 6 ตัวอักษร")


def create_user(username, password, display_name, company_id, role="user"):
    username = str(username or "").strip()
    if not USERNAME_RE.match(username):
        raise ValueError("ชื่อผู้ใช้ใช้ได้เฉพาะ a-z 0-9 . _ - ยาว 3–32 ตัว")
    _check_password(password)
    if role not in ("user", "admin"):
        raise ValueError("สิทธิ์ไม่ถูกต้อง")
    if role == "user" and not company_id:
        raise ValueError("เลือกบริษัทของผู้ใช้")
    init()
    try:
        with _db() as con:
            con.execute("""INSERT INTO users(username, password_hash, display_name, company_id, role, created_at)
                           VALUES (?,?,?,?,?,?)""",
                        (username, generate_password_hash(password), str(display_name or "").strip()[:80],
                         int(company_id) if company_id else None, role, int(time.time())))
    except sqlite3.IntegrityError:
        raise ValueError(f"มีชื่อผู้ใช้ {username} อยู่แล้ว")


def update_user(user_id, display_name=None, company_id=None, role=None):
    init()
    with _db() as con:
        if display_name is not None:
            con.execute("UPDATE users SET display_name = ? WHERE id = ?", (str(display_name).strip()[:80], int(user_id)))
        if company_id is not None:
            con.execute("UPDATE users SET company_id = ? WHERE id = ?", (int(company_id) if company_id else None, int(user_id)))
        if role in ("user", "admin"):
            con.execute("UPDATE users SET role = ? WHERE id = ?", (role, int(user_id)))


def set_password(user_id, password):
    _check_password(password)
    init()
    with _db() as con:
        con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), int(user_id)))
        con.execute("DELETE FROM sessions WHERE user_id = ?", (int(user_id),))   # new password = sign out everywhere


def set_active(user_id, active):
    init()
    with _db() as con:
        con.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, int(user_id)))
        if not active:
            con.execute("DELETE FROM sessions WHERE user_id = ?", (int(user_id),))


def release_device(user_id):
    """Admin: sign the user out of their device so they can sign in on another one."""
    init()
    with _db() as con:
        con.execute("DELETE FROM sessions WHERE user_id = ?", (int(user_id),))


def admin_count():
    init()
    with _db() as con:
        return con.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1").fetchone()[0]


def backup(dest):
    """Consistent copy of the database (for the nightly file backup)."""
    init()
    dest = Path(dest)
    tmp = dest.with_suffix(".tmp")
    src = _db()
    try:
        out = sqlite3.connect(tmp)
        with out:
            src.backup(out)
        out.close()
        os.replace(tmp, dest)
    finally:
        src.close()

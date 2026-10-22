"""FastAPI backend — OSP Monthly Report (all companies).

  POST /api/login {password}     viewer or admin session cookie
  POST /api/logout
  GET  /api/me                   {role, auth}
  GET  /api/companies            meta.json: companies, their zones and teams   (viewer)
  GET  /api/data/{slug}          one company's records                         (viewer)
  GET  /api/settings             monthly targets per company                   (viewer)
  PUT  /api/settings/{slug}      save one company's targets                    (admin)
  GET  /api/status               stored Excel files + dataset info             (admin)
  POST /api/upload               one "Data Job done <YEAR>….xlsx" -> rebuild   (admin)
  DELETE /api/files/{name}       remove a year and rebuild                     (admin)

Also serves the Vite `dist/` build.

Auth: OSP_VIEW_PASSWORD lets people see every company's report, OSP_ADMIN_PASSWORD
also allows uploads and target changes. With neither set (local dev) everything is
open. Sessions are HMAC-signed cookies keyed by OSP_SECRET.

Run (dev):  uvicorn server.app:app --reload --port 8000
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import sys
import threading
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server.etl import ETL_VERSION, build_dataset, list_excel_files, parse_upload_name

ROOT = Path(__file__).resolve().parents[1]
STORAGE = Path(os.environ.get("OSP_STORAGE", ROOT / "server" / "storage"))
EXCEL_DIR = STORAGE / "excel"
DATA_DIR = STORAGE / "data"
META_JSON = DATA_DIR / "meta.json"
SETTINGS_JSON = STORAGE / "settings.json"
DIST_DIR = ROOT / "dist"

EXCEL_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 300 * 1024 * 1024

# Rebuilds are serialized so two uploads can't clobber each other.
_BUILD_LOCK = threading.Lock()
_SETTINGS_LOCK = threading.Lock()


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------- auth ----------

VIEW_PASSWORD = os.environ.get("OSP_VIEW_PASSWORD", "")
ADMIN_PASSWORD = os.environ.get("OSP_ADMIN_PASSWORD", "")
AUTH_ENABLED = bool(VIEW_PASSWORD or ADMIN_PASSWORD)
SECRET = os.environ.get("OSP_SECRET") or secrets.token_hex(32)
COOKIE = "osp_session"
SESSION_SECONDS = 30 * 86400

if not AUTH_ENABLED:
    _log("!!! OSP_VIEW_PASSWORD / OSP_ADMIN_PASSWORD not set — no login, everyone can upload / edit targets")
elif not os.environ.get("OSP_SECRET"):
    _log("!!! OSP_SECRET not set — sessions end whenever the server restarts")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _sig(body: str) -> str:
    return hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()


def _make_token(role: str) -> str:
    body = _b64(json.dumps({"role": role, "exp": int(time.time()) + SESSION_SECONDS}).encode())
    return f"{body}.{_sig(body)}"


def _read_token(token: str) -> str | None:
    body, _, sig = (token or "").rpartition(".")
    if not body or not hmac.compare_digest(sig, _sig(body)):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except Exception:
        return None
    if payload.get("exp", 0) < time.time() or payload.get("role") not in ("viewer", "admin"):
        return None
    return payload["role"]


def current_role(request: Request) -> str | None:
    if not AUTH_ENABLED:
        return "admin"
    role = _read_token(request.cookies.get(COOKIE, ""))
    if role:
        return role
    return None if VIEW_PASSWORD else "viewer"   # no view password = viewing is open


def require_viewer(request: Request) -> str:
    role = current_role(request)
    if not role:
        raise HTTPException(401, "login required")
    return role


def require_admin(request: Request) -> str:
    if current_role(request) != "admin":
        raise HTTPException(403, "admin only")
    return "admin"


# Login throttling: 10 wrong passwords per 15 minutes per client IP.
_FAILS: dict[str, list[float]] = {}
_FAIL_WINDOW = 15 * 60
_FAIL_LIMIT = 10


def _client_ip(request: Request) -> str:
    # Production sits behind cloudflared on 127.0.0.1, which sets this header.
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")


# ---------- dataset ----------

_META_CACHE: dict = {"key": None, "meta": None}


def _meta() -> dict | None:
    try:
        st = META_JSON.stat()
    except FileNotFoundError:
        return None
    key = (st.st_mtime_ns, st.st_size)
    if _META_CACHE["key"] != key:
        try:
            _META_CACHE.update(key=key, meta=json.loads(META_JSON.read_text(encoding="utf-8")))
        except Exception:
            return None
    return _META_CACHE["meta"]


def _rebuild() -> dict:
    """Rebuild every company file from EXCEL_DIR. Caller must hold _BUILD_LOCK."""
    return build_dataset(EXCEL_DIR, DATA_DIR, log=_log)


def _rebuild_if_stale() -> None:
    """Rebuild when meta.json came from an older ETL (or is missing while Excel files
    exist). Runs in a thread so startup isn't delayed; old data keeps being served."""
    if not list_excel_files(EXCEL_DIR):
        return
    with _BUILD_LOCK:
        meta = _meta()
        if meta and meta.get("etl_version") == ETL_VERSION:
            return
        _log(f"dataset etl_version={meta and meta.get('etl_version')} != {ETL_VERSION}; rebuilding")
        try:
            _rebuild()
        except Exception:
            traceback.print_exc()


@asynccontextmanager
async def _lifespan(app):
    threading.Thread(target=_rebuild_if_stale, name="etl-migrate", daemon=True).start()
    yield


app = FastAPI(title="OSP Monthly Report", lifespan=_lifespan, docs_url=None, redoc_url=None)


# ---------- settings (monthly targets) ----------

# DMP's targets from the original report; other companies start without a target line.
DEFAULT_SETTINGS = {"targets": {"dmp": {"zone_default": 260, "team_default": 86, "zones": {}, "teams": {}}}}


def _load_settings() -> dict:
    try:
        return json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    except Exception:
        traceback.print_exc()
        return json.loads(json.dumps(DEFAULT_SETTINGS))


class TargetIn(BaseModel):
    zone_default: float | None = None
    team_default: float | None = None
    zones: dict[str, float | None] = {}
    teams: dict[str, float | None] = {}


def _clean_target(v):
    if v is None:
        return None
    if not (0 <= v <= 1_000_000):
        raise HTTPException(400, f"target out of range: {v}")
    return round(v, 2)


# ---------- API ----------

def _cookie_path() -> str:
    return (os.environ.get("OSP_BASE_PATH", "").rstrip("/") or "") + "/"


class LoginIn(BaseModel):
    password: str


@app.get("/api/me")
def api_me(request: Request):
    return {"role": current_role(request), "auth": AUTH_ENABLED}


@app.post("/api/login")
def api_login(body: LoginIn, request: Request, response: Response):
    if not AUTH_ENABLED:
        return {"role": "admin"}
    ip = _client_ip(request)
    now = time.time()
    fails = [t for t in _FAILS.get(ip, []) if now - t < _FAIL_WINDOW]
    if len(fails) >= _FAIL_LIMIT:
        raise HTTPException(429, "ใส่รหัสผิดหลายครั้งเกินไป ลองใหม่ในอีก 15 นาที")
    pw = body.password.encode()
    role = None
    if ADMIN_PASSWORD and hmac.compare_digest(pw, ADMIN_PASSWORD.encode()):
        role = "admin"
    elif VIEW_PASSWORD and hmac.compare_digest(pw, VIEW_PASSWORD.encode()):
        role = "viewer"
    if not role:
        _FAILS[ip] = fails + [now]
        raise HTTPException(401, "รหัสผ่านไม่ถูกต้อง")
    _FAILS.pop(ip, None)
    secure = request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https"
    # Scoped to this app's path: the dashboard on the same domain never sees it.
    response.set_cookie(
        COOKIE, _make_token(role), max_age=SESSION_SECONDS,
        httponly=True, samesite="lax", secure=secure, path=_cookie_path(),
    )
    return {"role": role}


@app.post("/api/logout")
def api_logout(response: Response):
    response.delete_cookie(COOKIE, path=_cookie_path())
    return {"ok": True}


@app.get("/api/companies", dependencies=[Depends(require_viewer)])
def api_companies():
    meta = _meta()
    if not meta:
        return {"companies": [], "empty": True}
    return {k: meta.get(k) for k in ("generated_at", "date_min", "date_max", "total", "companies")}


@app.get("/api/data/{slug}", dependencies=[Depends(require_viewer)])
def api_data(slug: str):
    meta = _meta() or {}
    if slug not in {c["slug"] for c in meta.get("companies", [])}:
        raise HTTPException(404, "unknown company")
    return FileResponse(DATA_DIR / f"{slug}.json", media_type="application/json",
                        headers={"Cache-Control": "no-store"})


@app.get("/api/settings", dependencies=[Depends(require_viewer)])
def api_settings():
    return _load_settings()


@app.put("/api/settings/{slug}", dependencies=[Depends(require_admin)])
def api_put_settings(slug: str, body: TargetIn):
    meta = _meta() or {}
    if slug not in {c["slug"] for c in meta.get("companies", [])}:
        raise HTTPException(404, "unknown company")
    entry = {
        "zone_default": _clean_target(body.zone_default),
        "team_default": _clean_target(body.team_default),
        "zones": {k[:100]: _clean_target(v) for k, v in body.zones.items() if v is not None},
        "teams": {k[:100]: _clean_target(v) for k, v in body.teams.items() if v is not None},
    }
    with _SETTINGS_LOCK:
        s = _load_settings()
        s.setdefault("targets", {})[slug] = entry
        tmp = SETTINGS_JSON.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(SETTINGS_JSON)
    return s


def _status_payload() -> dict:
    files = []
    for p, year in list_excel_files(EXCEL_DIR):
        st = p.stat()
        files.append({
            "name": p.name, "year": year, "size": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        })
    meta = _meta()
    data = None
    if meta:
        data = {k: meta.get(k) for k in ("etl_version", "generated_at", "date_min", "date_max", "total")}
        data["companies"] = [{"slug": c["slug"], "name": c["name"], "total": c["total"]} for c in meta.get("companies", [])]
    return {"files": files, "data": data}


@app.get("/api/status", dependencies=[Depends(require_admin)])
def api_status():
    return _status_payload()


# A plain `def` endpoint runs in the threadpool: the ~10 s save + ETL would freeze the
# event loop (and every other viewer) as `async def`.
@app.post("/api/upload", dependencies=[Depends(require_admin)])
def api_upload(file: UploadFile = File(...)):
    parsed = parse_upload_name(file.filename or "")
    if not parsed:
        raise HTTPException(
            400,
            f"ชื่อไฟล์ต้องขึ้นต้นด้วย 'Data Job done <ปี>' และเป็น .xlsx/.xlsm (ได้: {file.filename!r})",
        )
    year, ext = parsed
    # Store under one canonical name per year, whatever the upload was called.
    dst = EXCEL_DIR / f"Data Job done {year}.{ext}"
    tmp = EXCEL_DIR / f".upload-{year}.{ext}"
    with _BUILD_LOCK:
        written = 0
        try:
            with tmp.open("wb") as out:
                while chunk := file.file.read(1024 * 1024):
                    written += len(chunk)
                    if written > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, "ไฟล์ใหญ่เกิน 300 MB")
                    out.write(chunk)
        except HTTPException:
            tmp.unlink(missing_ok=True)
            raise
        except Exception as e:
            tmp.unlink(missing_ok=True)
            raise HTTPException(500, f"failed to save upload: {e}")

        # Keep the previous file(s) of this year until the new one builds cleanly,
        # so a broken upload doesn't wipe a year that was working.
        backups = []
        for other, oyear in list_excel_files(EXCEL_DIR):
            if oyear == year:
                bak = other.with_name(other.name + ".bak")
                other.replace(bak)
                backups.append((bak, other))
        tmp.replace(dst)
        try:
            info = _rebuild()
        except Exception as e:
            traceback.print_exc()
            dst.unlink(missing_ok=True)
            for bak, orig in backups:
                bak.replace(orig)
            try:
                if list_excel_files(EXCEL_DIR):
                    _rebuild()
            except Exception:
                traceback.print_exc()
            raise HTTPException(400, f"อ่านไฟล์ไม่ได้ — ใช้ข้อมูลเดิมต่อ: {e}")
        for bak, _ in backups:
            bak.unlink(missing_ok=True)

    return {"ok": True, "year": year, "build": info, "status": _status_payload()}


@app.delete("/api/files/{name}", dependencies=[Depends(require_admin)])
def api_delete(name: str):
    stored = {p.name: p for p, _ in list_excel_files(EXCEL_DIR)}
    target = stored.get(name)
    if not target:
        raise HTTPException(404, "file not found")
    with _BUILD_LOCK:
        target.unlink()
        if list_excel_files(EXCEL_DIR):
            try:
                _rebuild()
            except Exception as e:
                raise HTTPException(500, f"ETL failed: {e}")
        else:
            for p in DATA_DIR.glob("*.json"):
                p.unlink(missing_ok=True)
    return {"ok": True, "status": _status_payload()}


@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "DELETE"])
def api_not_found(rest: str):
    raise HTTPException(404, "not found")


# ---------- Static frontend (production) ----------

if DIST_DIR.exists():
    _DIST = DIST_DIR.resolve()
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Only real files inside dist/ — "../" in the path must not reach the
        # stored Excel files or the server code.
        candidate = (_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(_DIST):
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html", headers={"Cache-Control": "no-cache"})
else:

    @app.get("/")
    def root_no_dist():
        return JSONResponse({"ok": True, "msg": "Backend running. `npm run build` for the UI, or use the Vite dev server."})


# ---------- Serving under a sub-path ----------
# Production shares osp-dashboard.workproth.com with the OSP dashboard: Cloudflare
# sends /monthly/* here and the rest to the dashboard. Cloudflare doesn't strip the
# prefix, so mount the whole app under it (the frontend is built with the same base).
BASE_PATH = os.environ.get("OSP_BASE_PATH", "").rstrip("/")
if BASE_PATH:
    from fastapi.responses import RedirectResponse

    _report = app
    # Mounted apps get no lifespan events, so the outer app runs the start-up rebuild.
    app = FastAPI(title="OSP Monthly Report", lifespan=_lifespan, docs_url=None, redoc_url=None)
    app.mount(BASE_PATH, _report)

    @app.get("/")
    def _to_base():
        return RedirectResponse(BASE_PATH + "/")


# ---------- Sign-in shared with the OSP dashboard ----------
# The dashboard (same domain) keeps users in a SQLite file; mounted here read-only as
# OSP_AUTH_DB. Its session cookie (osp_sid, path /) reaches /monthly too, so one sign-in
# covers both. Unset = no dashboard sign-in required (local dev).
AUTH_DB = os.environ.get("OSP_AUTH_DB", "")
if AUTH_DB:
    import sqlite3
    from urllib.parse import quote
    from fastapi.responses import RedirectResponse as _Redirect

    def dashboard_user(token: str):
        if not token:
            return None
        try:
            con = sqlite3.connect(f"file:{AUTH_DB}?mode=ro", uri=True, timeout=5)
            try:
                row = con.execute(
                    """SELECT u.username, u.role FROM sessions s JOIN users u ON u.id = s.user_id
                       LEFT JOIN companies c ON c.id = u.company_id
                       WHERE s.token_hash = ? AND u.active = 1 AND COALESCE(c.active, 1) = 1""",
                    (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            finally:
                con.close()
        except sqlite3.Error:
            return None
        return {"username": row[0], "role": row[1]} if row else None

    @app.middleware("http")
    async def _require_dashboard_login(request: Request, call_next):
        if dashboard_user(request.cookies.get("osp_sid", "")):
            return await call_next(request)
        target = request.url.path + (("?" + request.url.query) if request.url.query else "")
        login = "/login?next=" + quote(target)
        if "/api/" in request.url.path:
            return JSONResponse({"detail": "login required", "login_url": login}, status_code=401)
        return _Redirect(login, status_code=302)

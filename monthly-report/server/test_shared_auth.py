import hashlib, importlib, sqlite3, sys


def _db(path):
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
    CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password_hash TEXT, display_name TEXT,
                        company_id INTEGER, role TEXT, active INTEGER DEFAULT 1, created_at INTEGER, last_login_at INTEGER);
    CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER, device_id TEXT, device_label TEXT, ip TEXT,
                           created_at INTEGER, last_seen_at INTEGER);
    INSERT INTO companies(id, name) VALUES (1, 'DMP');
    INSERT INTO users(id, username, password_hash, company_id, role) VALUES (1, 'u1', 'x', 1, 'user');
    """)
    con.execute("INSERT INTO sessions VALUES (?, 1, 'd', 'l', 'ip', 0, 0)", (hashlib.sha256(b"good").hexdigest(),))
    con.commit()
    con.close()


def test_dashboard_sign_in_required(monkeypatch, tmp_path):
    db = tmp_path / "auth.db"
    _db(db)
    monkeypatch.setenv("OSP_AUTH_DB", str(db))
    monkeypatch.setenv("OSP_BASE_PATH", "/monthly")
    monkeypatch.setenv("OSP_STORAGE", str(tmp_path / "st"))
    for k in ("OSP_VIEW_PASSWORD", "OSP_ADMIN_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    sys.modules.pop("server.app", None)
    from fastapi.testclient import TestClient
    app = importlib.import_module("server.app").app
    c = TestClient(app, follow_redirects=False)
    r = c.get("/monthly/c/dmp")
    assert r.status_code == 302 and r.headers["location"] == "/login?next=/monthly/c/dmp"
    r = c.get("/monthly/api/me")
    assert r.status_code == 401 and r.json()["login_url"].startswith("/login?next=")
    c.cookies.set("osp_sid", "bad")
    assert c.get("/monthly/api/me").status_code == 401
    c.cookies.set("osp_sid", "good")
    assert c.get("/monthly/api/me").status_code == 200
    con = sqlite3.connect(db); con.execute("UPDATE companies SET active = 0"); con.commit(); con.close()
    assert c.get("/monthly/api/me").status_code == 401   # company closed
    sys.modules.pop("server.app", None)

import importlib
import json

import pytest
from fastapi.testclient import TestClient


def load_app(monkeypatch, tmp_path, view="", admin="", base=""):
    monkeypatch.setenv("OSP_STORAGE", str(tmp_path))
    monkeypatch.setenv("OSP_BASE_PATH", base)
    monkeypatch.setenv("OSP_VIEW_PASSWORD", view)
    monkeypatch.setenv("OSP_ADMIN_PASSWORD", admin)
    monkeypatch.setenv("OSP_SECRET", "test-secret")
    import server.app as appmod
    appmod = importlib.reload(appmod)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (data / "meta.json").write_text(json.dumps({
        "etl_version": 1, "companies": [{"slug": "dmp", "name": "DMP", "total": 1, "zones": []}],
    }))
    (data / "dmp.json").write_text(json.dumps({"records": [{"d": "2026-01-01"}]}))
    return appmod, TestClient(appmod.app)


def test_open_when_no_passwords(monkeypatch, tmp_path):
    _, c = load_app(monkeypatch, tmp_path)
    assert c.get("/api/me").json()["role"] == "admin"
    assert c.get("/api/data/dmp").json()["records"]


def test_viewer_and_admin(monkeypatch, tmp_path):
    _, c = load_app(monkeypatch, tmp_path, view="see", admin="boss")
    assert c.get("/api/companies").status_code == 401
    assert c.get("/api/data/dmp").status_code == 401
    assert c.post("/api/login", json={"password": "nope"}).status_code == 401

    assert c.post("/api/login", json={"password": "see"}).json()["role"] == "viewer"
    assert c.get("/api/companies").status_code == 200
    assert c.get("/api/data/dmp").status_code == 200
    assert c.get("/api/data/../meta").status_code in (404, 405)
    assert c.put("/api/settings/dmp", json={"zone_default": 1}).status_code == 403
    assert c.get("/api/status").status_code == 403

    assert c.post("/api/login", json={"password": "boss"}).json()["role"] == "admin"
    r = c.put("/api/settings/dmp", json={"zone_default": 300, "zones": {"Latkrabang": 280, "X": None}})
    assert r.status_code == 200
    assert r.json()["targets"]["dmp"] == {"zone_default": 300, "team_default": None, "zones": {"Latkrabang": 280}, "teams": {}}
    assert c.put("/api/settings/nope", json={}).status_code == 404


def test_tampered_cookie_rejected(monkeypatch, tmp_path):
    appmod, c = load_app(monkeypatch, tmp_path, view="see", admin="boss")
    c.cookies.set(appmod.COOKIE, appmod._make_token("viewer").replace(".", "x.", 1))
    assert c.get("/api/companies").status_code == 401


def test_login_throttle(monkeypatch, tmp_path):
    _, c = load_app(monkeypatch, tmp_path, view="see", admin="boss")
    for _ in range(10):
        assert c.post("/api/login", json={"password": "bad"}).status_code == 401
    assert c.post("/api/login", json={"password": "see"}).status_code == 429


@pytest.mark.parametrize("name,ok", [
    ("Data Job done 2026.xlsx", True),
    ("Data Job done 2026 10:10:2026.xlsx", True),
    ("data job done 2025.XLSM", True),
    ("Data Job done.xlsx", False),
    ("report 2026.xlsx", False),
    ("Data Job done 2026.csv", False),
])
def test_upload_names(name, ok):
    from server.etl import parse_upload_name
    assert (parse_upload_name(name) is not None) == ok


def test_open_viewing_admin_only_writes(monkeypatch, tmp_path):
    _, c = load_app(monkeypatch, tmp_path, view="", admin="boss")
    assert c.get("/api/me").json() == {"role": "viewer", "auth": True}
    assert c.get("/api/data/dmp").status_code == 200
    assert c.put("/api/settings/dmp", json={"zone_default": 1}).status_code == 403
    assert c.get("/api/status").status_code == 403
    assert c.post("/api/login", json={"password": "boss"}).json()["role"] == "admin"
    assert c.get("/api/status").status_code == 200


def test_served_under_base_path(monkeypatch, tmp_path):
    _, c = load_app(monkeypatch, tmp_path, admin="boss", base="/monthly")
    assert c.get("/monthly/api/me").json()["role"] == "viewer"
    assert c.get("/monthly/api/data/dmp").status_code == 200
    r = c.post("/monthly/api/login", json={"password": "boss"})
    assert r.status_code == 200 and "Path=/monthly/" in r.headers["set-cookie"]
    assert c.get("/api/me").status_code == 404
    assert c.get("/", follow_redirects=False).headers["location"] == "/monthly/"

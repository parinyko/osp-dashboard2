# -*- coding: utf-8 -*-
"""Job Map data: where each job is, and the FTTH network drawings (KMZ) per site.

Job position, best first:
  1. "job"      coordinates written in the Job Title, e.g. "(13.717414, 100.559227)"
  2. "site"     the job's SITE_CODE -> site position (learned from other jobs' titles, or
                the site table the server keeps next to the KMZ files)
  3. "district" centre of the job's District Name — always available, so no job is left off
The KMZ files and the site table are AIS internal data: they live on the server only
(NETWORK_DIR), never in this repository.
"""
from __future__ import annotations

import io
import json
import os
import re
import threading
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DISTRICTS_FILE = BASE_DIR / "static" / "map" / "districts.geojson"
LEARNED_FILE = BASE_DIR / "site_coords_learned.json"
NETWORK_DIR = Path(os.environ.get("NETWORK_DIR", "/network"))
KMZ_DIR = NETWORK_DIR / "kmz"
SITE_TABLE_FILE = NETWORK_DIR / "site_coords.json"

COORD_RE = re.compile(r"(1[0-9]\.\d{3,})\s*,\s*(1[0-9]{2}\.\d{3,})")
# Bangkok and the provinces around it — anything else in a title is a typo
LAT_RANGE, LON_RANGE = (12.5, 15.5), (99.5, 102.0)


def _norm_district(name):
    s = re.sub(r"^(เขต|อำเภอ|อ\.)\s*", "", str(name or "").strip())
    return re.sub(r"\s+", "", s)


# ---------------------------------------------------------------- districts / zones

_districts = None


def districts():
    """{normalized district name: {"province", "district", "zone", "x", "y"}} from the static GeoJSON."""
    global _districts
    if _districts is None:
        out = {}
        try:
            fc = json.loads(DISTRICTS_FILE.read_text(encoding="utf-8"))
            for f in fc.get("features", []):
                p = f["properties"]
                out[_norm_district(p["district"])] = {
                    "province": p["province"], "district": p["district"], "zone": p.get("zone"),
                    "x": p["cx"], "y": p["cy"],
                }
        except (OSError, ValueError, KeyError):
            pass
        _districts = out
    return _districts


# ---------------------------------------------------------------- site positions

_site_lock = threading.Lock()
_site_table = None          # from NETWORK_DIR (history + KMZ OLT points), read-only
_learned = None             # from job titles seen by this dashboard, kept in LEARNED_FILE


def _load_site_tables():
    global _site_table, _learned
    if _site_table is None:
        try:
            _site_table = {k: (float(v[0]), float(v[1])) for k, v in json.loads(SITE_TABLE_FILE.read_text()).items()}
        except (OSError, ValueError, TypeError, IndexError):
            _site_table = {}
    if _learned is None:
        try:
            _learned = {k: (float(v[0]), float(v[1])) for k, v in json.loads(LEARNED_FILE.read_text()).items()}
        except (OSError, ValueError, TypeError, IndexError):
            _learned = {}


def title_coords(title):
    m = COORD_RE.search(str(title or ""))
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]:
        return lat, lon
    return None


# Splitters named in a job title — "BKK0928-034 (13.74, 100.51)", "OB_KJN5M_ZZ_G1NK_THECN_P04_SP01_18[13.86,100.67]".
# The key is the part the KMZ placemark names share ("OB_PADUM_ZZ_01HW_IJSX9_BKK0928-034_18",
# "OB_KJN5M_ZZ_01NK_THECN_P04_SP01_01_18").
REF_PATTERNS = (
    (re.compile(r"(?<![A-Z0-9])([A-Z]{3}\d{4}-\d{3})(?!\d)"), lambda m: m.group(1)),
    (re.compile(r"(?<![A-Z0-9])([A-Z0-9]{5})_P(\d{2})_SP(\d{2})"), lambda m: f"{m.group(1)}_P{m.group(2)}_SP{m.group(3)}"),
)
REF_COORD_RE = re.compile(r"(?:_\d+)?(?:\(\d+\))?\s*[\(\[]\s*(1[0-9]\.\d{3,})\s*,\s*(1[0-9]{2}\.\d{3,})\s*[\)\]]")


def fault_refs(title):
    """[{"key", "lat", "lon"}] for every splitter the title names; lat/lon when written right after it."""
    title = str(title or "")
    out = {}
    for rx, key_of in REF_PATTERNS:
        for m in rx.finditer(title):
            key = key_of(m)
            c = REF_COORD_RE.match(title, m.end())
            lat = lon = None
            if c:
                la, lo = float(c.group(1)), float(c.group(2))
                if LAT_RANGE[0] <= la <= LAT_RANGE[1] and LON_RANGE[0] <= lo <= LON_RANGE[1]:
                    lat, lon = la, lo
            # a splitter is often named twice — keep the mention that carries coordinates
            if key not in out or (out[key]["lat"] is None and lat is not None):
                out[key] = {"key": key, "lat": lat, "lon": lon, "src": "title" if lat is not None else None}
    return list(out.values())


def learn_sites(pairs):
    """Remember site positions from job titles. pairs = [(site_code, (lat, lon)), ...]"""
    with _site_lock:
        _load_site_tables()
        changed = False
        for site, ll in pairs:
            if site and ll and _learned.get(site) != ll:
                _learned[site] = ll
                changed = True
        if changed:
            tmp = str(LEARNED_FILE) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({k: list(v) for k, v in _learned.items()}, f)
            os.replace(tmp, LEARNED_FILE)


def site_coords(site):
    with _site_lock:
        _load_site_tables()
        # the site table (OLT position from the drawing) is the real site; a learned position
        # is where one of its faults was — use it only when the table has nothing
        return _site_table.get(site) or _learned.get(site)


def locate(title, site, district):
    """(lat, lon, precision) — precision is "job", "site", "district" or None."""
    ll = title_coords(title)
    if ll:
        return ll[0], ll[1], "job"
    if site:
        ll = site_coords(site)
        if ll:
            return ll[0], ll[1], "site"
    d = districts().get(_norm_district(district))
    if d:
        return d["y"], d["x"], "district"
    return None, None, None


# ---------------------------------------------------------------- KMZ index

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
TOKEN_RE = re.compile(r"[A-Z][A-Z0-9]{3,5}")
_index = None
_index_at = 0
_index_lock = threading.Lock()


def _year(y):
    y = int(y)
    return y + 2000 if y < 100 else y


def file_date(name):
    """Date written in a drawing's file name ("Approve 17-10-18", "1 July 2025", "2020-03-10")."""
    s = name.lower()
    for rx, order in (
        (r"(20\d\d)-(\d{1,2})-(\d{1,2})", "ymd"),
        (r"(\d{1,2})[-/ ]?([a-z]{3,9})[-/ ]?(\d{2,4})", "dMy"),
        (r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", "dmy"),
        (r"(\d{2})(\d{2})(20\d\d)", "dmy"),
    ):
        for m in re.finditer(rx, s):
            try:
                a, b, c = m.groups()
                if order == "ymd":
                    return datetime(int(a), int(b), int(c))
                if order == "dMy":
                    mon = MONTHS.get(b[:3])
                    if mon:
                        return datetime(_year(c), mon, int(a))
                    continue
                return datetime(_year(c), int(b), int(a))
            except ValueError:
                continue
    return None


def kmz_index(max_age=600):
    """{SITE_CODE: [{"file", "title", "date"}, newest first]} built from the file names."""
    global _index, _index_at
    with _index_lock:
        if _index is not None and time.time() - _index_at < max_age:
            return _index
        idx = defaultdict(list)
        try:
            names = [n for n in os.listdir(KMZ_DIR) if n.lower().endswith((".kmz", ".kml"))]
        except OSError:
            names = []
        for n in names:
            try:
                st = (KMZ_DIR / n).stat()
            except OSError:
                continue
            if st.st_size == 0:
                continue
            d = file_date(n)
            entry = {"file": n, "title": n.rsplit(".", 1)[0], "size": st.st_size,
                     "date": (d or datetime.fromtimestamp(st.st_mtime)).strftime("%Y-%m-%d"),
                     "dated": d is not None}
            for tok in set(TOKEN_RE.findall(n.upper())):
                idx[tok].append(entry)
        for v in idx.values():
            v.sort(key=lambda e: (e["date"], e["file"]), reverse=True)
        _index, _index_at = dict(idx), time.time()
        return _index


def kmz_versions(site):
    return kmz_index().get(str(site or "").upper().strip(), [])


# ---------------------------------------------------------------- KMZ -> GeoJSON

def _kml_bytes(path):
    if path.suffix.lower() == ".kml":
        return path.read_bytes()
    with zipfile.ZipFile(path) as z:
        kmls = [n for n in z.namelist() if n.lower().endswith(".kml")]
        if not kmls:
            raise ValueError("ไม่พบ .kml ในไฟล์ KMZ")
        kmls.sort(key=lambda n: (n.lower() != "doc.kml", len(n)))
        return z.read(kmls[0])


def _declare_prefixes(data):
    """Some drawings use gx:/xsi: prefixes without declaring them, which XML parsers reject.
    Declare every prefix in use on the root element."""
    head = data[:4096]
    used = set(re.findall(rb"</?([A-Za-z_][\w.-]*):[A-Za-z_]", data))
    used |= set(re.findall(rb"\s([A-Za-z_][\w.-]*):[A-Za-z_][\w.-]*=\"", data))   # xsi:schemaLocation="..."
    used -= {b"xml", b"xmlns"}
    missing = [p for p in used if b"xmlns:" + p + b"=" not in head]
    if not missing:
        return data
    m = re.search(rb"<(?:[A-Za-z_][\w.-]*:)?kml\b", data)
    if not m:
        return data
    decl = b"".join(b' xmlns:' + p + b'="urn:x-' + p + b'"' for p in missing)
    return data[:m.end()] + decl + data[m.end():]


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _kml_color(c):
    """KML aabbggrr -> ("#rrggbb", opacity)."""
    c = (c or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{8}", c):
        return None, None
    return "#" + c[6:8] + c[4:6] + c[2:4], round(int(c[0:2], 16) / 255, 2)


def _coords(text):
    pts = []
    for part in (text or "").split():
        xyz = part.split(",")
        if len(xyz) >= 2:
            try:
                pts.append([round(float(xyz[0]), 6), round(float(xyz[1]), 6)])
            except ValueError:
                pass
    return pts


def _child(el, name):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _find_all(el, name):
    return [c for c in el.iter() if _local(c.tag) == name]


def _style_of(el):
    """Colors from a <Style> element."""
    st = {}
    for sub in el:
        kind = _local(sub.tag)
        color = _child(sub, "color")
        col, op = _kml_color(color.text if color is not None else "")
        if kind == "LineStyle":
            if col:
                st["stroke"], st["stroke_opacity"] = col, op
            w = _child(sub, "width")
            if w is not None:
                try:
                    st["width"] = round(float(w.text), 1)
                except (TypeError, ValueError):
                    pass
        elif kind == "PolyStyle":
            if col:
                st["fill"], st["fill_opacity"] = col, op
            f = _child(sub, "fill")
            if f is not None and (f.text or "").strip() == "0":
                st["fill_opacity"] = 0
        elif kind == "IconStyle" and col:
            st["icon"] = col
    return st


def kml_to_geojson(data, max_features=30000):
    styles, style_maps, feats = {}, {}, []
    folders = []
    data = _declare_prefixes(data)
    for event, el in ET.iterparse(io.BytesIO(data), events=("start", "end")):
        tag = _local(el.tag)
        if event == "start":
            if tag in ("Folder", "Document"):
                folders.append(None)
            continue
        if tag == "name" and folders and folders[-1] is None:
            folders[-1] = (el.text or "").strip()
        elif tag == "Style" and el.get("id"):
            styles[el.get("id")] = _style_of(el)
        elif tag == "StyleMap" and el.get("id"):
            for pair in el:
                if _local(pair.tag) == "Pair":
                    key, url = _child(pair, "key"), _child(pair, "styleUrl")
                    if key is not None and (key.text or "").strip() == "normal" and url is not None:
                        style_maps[el.get("id")] = (url.text or "").strip().lstrip("#")
        elif tag in ("Folder", "Document"):
            folders.pop()
            el.clear()
        elif tag == "Placemark":
            if len(feats) < max_features:
                name = _child(el, "name")
                desc = _child(el, "description")
                url = _child(el, "styleUrl")
                inline = _child(el, "Style")
                path = [f for f in folders if f]
                props = {
                    "name": (name.text or "").strip() if name is not None else "",
                    "folder": path[-1] if path else "",
                    "path": " / ".join(path[1:]) if len(path) > 1 else (path[0] if path else ""),
                    "style": (url.text or "").strip().lstrip("#") if url is not None else "",
                }
                if desc is not None and desc.text:
                    props["desc"] = re.sub(r"<[^>]+>", " ", desc.text).strip()[:300]
                if inline is not None:
                    props["inline"] = _style_of(inline)
                ext = {}
                for d in el.iter():
                    t = _local(d.tag)
                    if t in ("Data", "SimpleData") and d.get("name"):
                        v = _child(d, "value") if t == "Data" else d
                        val = (v.text or "").strip() if v is not None else ""
                        if val and len(ext) < 12:
                            ext[d.get("name")[:40]] = val[:120]
                if ext:
                    props["ext"] = ext
                for g in el.iter():
                    kind = _local(g.tag)
                    if kind == "Point":
                        c = _coords(_child(g, "coordinates").text if _child(g, "coordinates") is not None else "")
                        if c:
                            feats.append({"type": "Feature", "properties": {**props, "kind": "point"},
                                          "geometry": {"type": "Point", "coordinates": c[0]}})
                    elif kind == "LineString":
                        c = _coords(_child(g, "coordinates").text if _child(g, "coordinates") is not None else "")
                        if len(c) >= 2:
                            feats.append({"type": "Feature", "properties": {**props, "kind": "line"},
                                          "geometry": {"type": "LineString", "coordinates": c}})
                    elif kind == "Polygon":
                        rings = []
                        for b in ("outerBoundaryIs", "innerBoundaryIs"):
                            for bd in _find_all(g, b):
                                for lr in _find_all(bd, "coordinates"):
                                    r = _coords(lr.text)
                                    if len(r) >= 4:
                                        rings.append(r)
                        if rings:
                            feats.append({"type": "Feature", "properties": {**props, "kind": "polygon"},
                                          "geometry": {"type": "Polygon", "coordinates": rings}})
            el.clear()

    # resolve shared styles (StyleMap -> Style) into plain colour properties
    groups = defaultdict(int)
    for f in feats:
        p = f["properties"]
        sid = p.pop("style", "")
        st = dict(styles.get(style_maps.get(sid, sid), {}))
        st.update(p.pop("inline", {}) or {})
        p.update(st)
        p["folder"] = p["folder"] or "(ไม่มีโฟลเดอร์)"
        groups[p["folder"]] += 1
    return {"type": "FeatureCollection", "features": feats,
            "groups": [{"name": k, "count": v} for k, v in sorted(groups.items(), key=lambda kv: -kv[1])],
            "truncated": len(feats) >= max_features}


_points = {}   # (file, mtime) -> [(NAME WITHOUT SPACES, lat, lon)]


def kmz_points(site):
    """Named points of the site's newest drawing (cheap after the first call)."""
    versions = kmz_versions(site)
    if not versions:
        return []
    path = KMZ_DIR / versions[0]["file"]
    try:
        key = (str(path), path.stat().st_mtime)
    except OSError:
        return []
    if key not in _points:
        try:
            gj = kmz_geojson(versions[0]["file"])
        except Exception:
            gj = {"features": []}
        _points[key] = [(re.sub(r"\s+", "", f["properties"].get("name", "")).upper(),
                         f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0])
                        for f in gj["features"] if f["geometry"]["type"] == "Point"]
    return _points[key]


def locate_faults(site, faults):
    """Fill in splitters without title coordinates from the site's drawing (src "kmz")."""
    missing = [f for f in faults if f["lat"] is None]
    if not missing or not site:
        return faults
    pts = kmz_points(site)
    for f in missing:
        for name, lat, lon in pts:
            if f["key"] in name:
                f["lat"], f["lon"], f["src"] = round(lat, 6), round(lon, 6), "kmz"
                break
    return faults


_cache = OrderedDict()
_cache_lock = threading.Lock()
CACHE_ITEMS = 40


def kmz_geojson(file_name):
    """Converted drawing, cached in memory (a few recent files)."""
    path = (KMZ_DIR / file_name).resolve()
    if KMZ_DIR.resolve() not in path.parents or not path.is_file():
        raise FileNotFoundError(file_name)
    key = (str(path), path.stat().st_mtime)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    gj = kml_to_geojson(_kml_bytes(path))
    with _cache_lock:
        _cache[key] = gj
        while len(_cache) > CACHE_ITEMS:
            _cache.popitem(last=False)
    return gj


# ---------------------------------------------------------------- site table (rebuilt daily)

MONTHLY_EXCEL_DIR = Path(os.environ.get("MONTHLY_EXCEL_DIR", "/monthly-excel"))
OLT_RE = re.compile(rb"<Placemark\b[^>]*>\s*<name>([^<]*)</name>(.*?)</Placemark>", re.S)
POINT_RE = re.compile(rb"<Point\b.*?<coordinates>\s*([-\d.]+)\s*,\s*([-\d.]+)", re.S)


def _olt_point(path, site):
    """Position of the site's OLT placemark ("TNMMM_OLT1_ZT") in one drawing."""
    if path.stat().st_size > 25_000_000:
        return None
    try:
        data = _kml_bytes(path)
    except (OSError, ValueError, zipfile.BadZipFile):
        return None
    s = site.encode()
    for m in OLT_RE.finditer(data):
        name = m.group(1).strip().upper()
        if name.startswith(s) and (b"OLT" in name or name == s):
            p = POINT_RE.search(m.group(2))
            if p:
                lon, lat = float(p.group(1)), float(p.group(2))
                if LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]:
                    return round(lat, 6), round(lon, 6)
    return None


def _history_sites():
    """Median position of each SITE_CODE over the Monthly Report's "Data Job done" exports."""
    import statistics
    try:
        import openpyxl
    except ImportError:
        return {}
    pts = defaultdict(list)
    for path in sorted(MONTHLY_EXCEL_DIR.glob("*.xlsx")):
        try:
            wb = openpyxl.load_workbook(path, read_only=True)
        except Exception:
            continue
        for ws in wb.worksheets:
            rows = ws.iter_rows(values_only=True)
            head = [str(c or "").strip() for c in next(rows, [])]
            if "SITE_CODE" not in head:
                continue
            si = head.index("SITE_CODE")
            li = head.index("Lat/Long") if "Lat/Long" in head else None
            ti = head.index("TITLE") if "TITLE" in head else None
            for r in rows:
                site = str(r[si] or "").strip().upper() if si < len(r) else ""
                if not site:
                    continue
                ll = (title_coords(r[li]) if li is not None and li < len(r) else None) or \
                     (title_coords(r[ti]) if ti is not None and ti < len(r) else None)
                if ll:
                    pts[site].append(ll)
            break
        wb.close()
    return {k: (round(statistics.median(a for a, _ in v), 6), round(statistics.median(b for _, b in v), 6))
            for k, v in pts.items()}


def build_site_table():
    """KMZ OLT position when the site has a drawing, else the median of its past jobs.
    Written to NETWORK_DIR/site_coords.json; returns (sites, from_kmz, from_history)."""
    global _site_table
    table = dict(_history_sites())
    hist = len(table)
    from_kmz = 0
    for site, versions in kmz_index(max_age=0).items():
        if not re.fullmatch(r"[A-Z][A-Z0-9]{3,5}", site):
            continue
        for e in versions[:3]:
            ll = _olt_point(KMZ_DIR / e["file"], site)
            if ll:
                table[site] = ll
                from_kmz += 1
                break
    tmp = str(SITE_TABLE_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({k: list(v) for k, v in table.items()}, f)
    os.replace(tmp, SITE_TABLE_FILE)
    with _site_lock:
        _site_table = None
    return len(table), from_kmz, hist

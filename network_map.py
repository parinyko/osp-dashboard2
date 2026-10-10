# -*- coding: utf-8 -*-
"""Job Map data: where each job is, and the FTTH network drawings (KMZ) per site.

Job position, best first:
  1. "job"      coordinates written in the Job Title, e.g. "(13.717414, 100.559227)"
  2. "site"     the job's SITE_CODE -> site position: the OLT in the site's KMZ drawing, else the
                official SITE_MASTER list, else where the site's past jobs were (site table next to
                the KMZ files), else positions learned from other jobs' titles
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
# Official site positions (SITE_MASTER sheet "พิกัด SITE AIS", ~4,200 sites): {"sites": {CODE: {"lat","lon","name"}}}
SITE_MASTER_FILE = NETWORK_DIR / "site_master.json"

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


def _code_variants(site):
    """SITE_MASTER sometimes drops the code's last letter ("SLL5M" is listed as "SLL5") and job
    titles sometimes do ("BUKW" for "BUKWM"): exact first, then the 4-letter base and its usual suffixes."""
    site = str(site or "").strip().upper()
    if not site:
        return []
    out = [site]
    base = site[:4] if len(site) == 5 else site if len(site) == 4 else None
    if base:
        out += [base] + [base + x for x in "MPAB"]
    return list(dict.fromkeys(out))


def site_coords(site):
    with _site_lock:
        _load_site_tables()
        # the site table (drawing OLT / SITE_MASTER / past jobs) is the real site; a learned position
        # is where one of its faults was — use it only when the table has nothing
        for key in _code_variants(site):
            if key in _site_table:
                return _site_table[key]
        return _learned.get(str(site or "").upper())


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
    """Colours, line width, icon and label settings from a <Style> element."""
    st = {}
    for sub in el:
        kind = _local(sub.tag)
        color = _child(sub, "color")
        col, op = _kml_color(color.text if color is not None else "")
        scale = _child(sub, "scale")
        try:
            scale = round(float(scale.text), 2) if scale is not None else None
        except (TypeError, ValueError):
            scale = None
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
            o = _child(sub, "outline")
            if o is not None and (o.text or "").strip() == "0":
                st["outline"] = 0
        elif kind == "IconStyle":
            if col:
                st["icon"], st["icon_opacity"] = col, op       # tint, multiplied into the icon like Google Earth
            if scale is not None:
                st["icon_scale"] = scale
            icon = _child(sub, "Icon")
            href = _child(icon, "href") if icon is not None else None
            if href is not None and (href.text or "").strip():
                st["icon_href"] = href.text.strip()
            hs = _child(sub, "hotSpot")
            if hs is not None:
                try:
                    st["hot"] = [float(hs.get("x", 0.5)), float(hs.get("y", 0.5)),
                                 hs.get("xunits", "fraction"), hs.get("yunits", "fraction")]
                except ValueError:
                    pass
        elif kind == "LabelStyle":
            if col:
                st["label"], st["label_opacity"] = col, op
            if scale is not None:
                st["label_scale"] = scale
    return st


def kml_to_geojson(data, max_features=30000):
    """GeoJSON of a drawing plus its folder tree, the way Google Earth lists it.
    Every feature carries fid (its folder) and pid (its placemark); tree nodes are
    {"id", "name", "count", "visible", "open", "children", "items": [[pid, name, kind]]}."""
    styles, style_maps, feats = {}, {}, []
    folders = {}        # id -> node
    stack = []          # open Folder/Document ids
    in_pm = 0
    pid = 0
    data = _declare_prefixes(data)
    for event, el in ET.iterparse(io.BytesIO(data), events=("start", "end")):
        tag = _local(el.tag)
        if event == "start":
            if tag in ("Folder", "Document"):
                fid = len(folders)
                folders[fid] = {"id": fid, "name": None, "parent": stack[-1] if stack else None,
                                "visible": True, "open": False, "children": [], "items": [], "own": 0}
                if stack:
                    folders[stack[-1]]["children"].append(fid)
                stack.append(fid)
            elif tag == "Placemark":
                in_pm += 1
            continue
        if not in_pm and stack:
            node = folders[stack[-1]]
            if tag == "name" and node["name"] is None:
                node["name"] = (el.text or "").strip()
            elif tag == "visibility" and (el.text or "").strip() == "0":
                node["visible"] = False
            elif tag == "open" and (el.text or "").strip() == "1":
                node["open"] = True
        if tag == "Style" and el.get("id"):
            styles[el.get("id")] = _style_of(el)
        elif tag == "StyleMap" and el.get("id"):
            for pair in el:
                if _local(pair.tag) == "Pair":
                    key, url = _child(pair, "key"), _child(pair, "styleUrl")
                    if key is not None and (key.text or "").strip() == "normal" and url is not None:
                        style_maps[el.get("id")] = (url.text or "").strip().lstrip("#")
        elif tag in ("Folder", "Document"):
            stack.pop()
            el.clear()
        elif tag == "Placemark":
            in_pm -= 1
            if len(feats) < max_features:
                name = _child(el, "name")
                desc = _child(el, "description")
                url = _child(el, "styleUrl")
                inline = _child(el, "Style")
                vis = _child(el, "visibility")
                fid = stack[-1] if stack else -1
                pid += 1
                props = {
                    "name": (name.text or "").strip() if name is not None else "",
                    "fid": fid, "pid": pid,
                    "style": (url.text or "").strip().lstrip("#") if url is not None else "",
                }
                if vis is not None and (vis.text or "").strip() == "0":
                    props["hidden"] = 1
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
                kinds = []
                for g in el.iter():
                    kind = _local(g.tag)
                    if kind == "Point":
                        c = _coords(_child(g, "coordinates").text if _child(g, "coordinates") is not None else "")
                        if c:
                            feats.append({"type": "Feature", "properties": {**props, "kind": "point"},
                                          "geometry": {"type": "Point", "coordinates": c[0]}})
                            kinds.append("point")
                    elif kind == "LineString":
                        c = _coords(_child(g, "coordinates").text if _child(g, "coordinates") is not None else "")
                        if len(c) >= 2:
                            feats.append({"type": "Feature", "properties": {**props, "kind": "line"},
                                          "geometry": {"type": "LineString", "coordinates": c}})
                            kinds.append("line")
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
                            kinds.append("polygon")
                if kinds and fid in folders:
                    folders[fid]["items"].append([pid, props["name"], kinds[0]])
                    folders[fid]["own"] += 1
            el.clear()

    # shared styles (StyleMap -> Style) become plain properties; folder path for popups
    def path_of(fid):
        names = []
        while fid is not None and fid in folders:
            if folders[fid]["parent"] is not None and folders[fid]["name"]:
                names.append(folders[fid]["name"])
            fid = folders[fid]["parent"]
        return " / ".join(reversed(names))
    paths = {}
    for f in feats:
        p = f["properties"]
        sid = p.pop("style", "")
        st = dict(styles.get(style_maps.get(sid, sid), {}))
        st.update(p.pop("inline", {}) or {})
        p.update(st)
        if p["fid"] not in paths:
            paths[p["fid"]] = path_of(p["fid"])
        p["path"] = paths[p["fid"]]
        p["folder"] = folders[p["fid"]]["name"] if p["fid"] in folders else ""

    def node(fid):
        n = folders[fid]
        kids = [node(c) for c in n["children"]]
        kids = [k for k in kids if k["count"]]
        return {"id": fid, "name": n["name"] or "(ไม่มีชื่อ)", "visible": n["visible"], "open": n["open"],
                "count": n["own"] + sum(k["count"] for k in kids), "children": kids, "items": n["items"]}
    tree = [node(fid) for fid, n in folders.items() if n["parent"] is None]
    return {"type": "FeatureCollection", "features": feats, "tree": tree,
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


def _master_sites():
    try:
        sites = json.loads(SITE_MASTER_FILE.read_text(encoding="utf-8")).get("sites", {})
    except (OSError, ValueError, AttributeError):
        return {}
    out = {}
    for code, v in sites.items():
        try:
            lat, lon = float(v["lat"]), float(v["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]:
            out[str(code).upper()] = (round(lat, 6), round(lon, 6))
    return out


def build_site_table():
    """Site position, best first: the OLT in the site's KMZ drawing, the official SITE_MASTER list,
    the median of the site's past jobs. Written to NETWORK_DIR/site_coords.json;
    returns (sites, from_kmz, from_history)."""
    global _site_table
    table = dict(_history_sites())
    hist = len(table)
    table.update(_master_sites())
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


# ---------------------------------------------------------------- drawing icons

ICON_DIR = NETWORK_DIR / "icons"
# Google Earth's stock icons (and the earthpoint set some drawings use) — fetched once, kept on the server
ICON_HOSTS = ("maps.google.com/mapfiles/", "www.earthpoint.us/dots/", "earth.google.com/images/", "www.gstatic.com/mapspro/")
IMAGE_TYPES = {".png": "image/png", ".gif": "image/gif", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def remote_icon(url):
    """(bytes, mimetype) for an allowed icon URL, cached under NETWORK_DIR/icons; None if not allowed / unreachable."""
    import hashlib
    import urllib.request
    u = str(url or "").strip()
    bare = re.sub(r"^https?://", "", u).lower()
    ext = os.path.splitext(bare.split("?", 1)[0])[1]
    if not bare.startswith(ICON_HOSTS) or ext not in IMAGE_TYPES:
        return None
    path = ICON_DIR / (hashlib.sha1(bare.encode()).hexdigest() + ext)
    if path.is_file():
        return path.read_bytes(), IMAGE_TYPES[ext]
    try:
        with urllib.request.urlopen("https://" + re.sub(r"^https?://", "", u), timeout=10) as r:
            data = r.read(512 * 1024)
    except Exception:
        return None
    try:
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except OSError:
        pass
    return data, IMAGE_TYPES[ext]


def kmz_resource(file_name, inner):
    """(bytes, mimetype) of an image packed inside a KMZ (files/icon.png); None otherwise."""
    path = (KMZ_DIR / file_name).resolve()
    if KMZ_DIR.resolve() not in path.parents or not path.is_file() or path.suffix.lower() != ".kmz":
        return None
    inner = str(inner or "").lstrip("/").replace("\\", "/")
    ext = os.path.splitext(inner)[1].lower()
    if ext not in IMAGE_TYPES or ".." in inner.split("/"):
        return None
    try:
        with zipfile.ZipFile(path) as z:
            names = {n.lower(): n for n in z.namelist()}
            real = names.get(inner.lower())
            return (z.read(real), IMAGE_TYPES[ext]) if real else None
    except (OSError, zipfile.BadZipFile):
        return None

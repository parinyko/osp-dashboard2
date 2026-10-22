"""Excel -> per-company JSON datasets.

Reads every stored `Data Job done <YEAR>.xlsx|.xlsm` in `excel_dir`, cleans each row,
classifies it into company / zone / team (server/companies.py), and writes:

    data_dir/<slug>.json   {"records": [...]} for one company
    data_dir/meta.json     etl version, date range, and per company: zones (in
                           display order) with their teams, job counts

Usage from Python:
    from server.etl import build_dataset
    info = build_dataset(excel_dir, data_dir)
"""
from __future__ import annotations

import json
import re
import sys
import time as _time
from collections import defaultdict
from datetime import datetime, date, time, timedelta
from pathlib import Path

import openpyxl

from server.companies import OTHER_ZONE, classify, mnm_area, zone_order


# Bump whenever the shape or meaning of the emitted records changes. On startup the
# backend compares this with meta.json and rebuilds, so a deploy never serves data
# produced by an older ETL.
ETL_VERSION = 1

# Durations longer than this are data-entry errors (e.g. a blank ONSITE_DATE turns
# "Onsite to Done" into a 100+ day span). They are dropped instead of skewing means.
MAX_DURATION_SEC = 30 * 86400


# ---------- Filename helpers ----------

# Files are stored under this exact name, one per year (see server/app.py upload).
FILENAME_RE = re.compile(r"(?i)^Data\s+Job\s+done\s+(\d{4})\.xls[xm]$")
# Uploads may carry an export date after the year: "Data Job done 2026 10:10:2026.xlsx".
UPLOAD_NAME_RE = re.compile(r"(?i)^Data\s+Job\s+done\s+(\d{4})\b.*\.(xlsx|xlsm)$")


def parse_year_from_filename(name: str) -> int | None:
    m = FILENAME_RE.match(name.strip())
    return int(m.group(1)) if m else None


def parse_upload_name(name: str) -> tuple[int, str] | None:
    """Upload filename -> (year, extension) or None."""
    m = UPLOAD_NAME_RE.match(name.strip())
    return (int(m.group(1)), m.group(2).lower()) if m else None


def list_excel_files(excel_dir: Path) -> list[tuple[Path, int]]:
    """Return [(path, year), ...] for stored year files, sorted by year."""
    out: list[tuple[Path, int]] = []
    if not excel_dir.exists():
        return out
    for p in excel_dir.iterdir():
        if not p.is_file():
            continue
        year = parse_year_from_filename(p.name)
        if year is not None:
            out.append((p, year))
    out.sort(key=lambda x: x[1])
    return out


# ---------- Value parsers ----------

def parse_date(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if isinstance(v, str):
        s = v.strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
            "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y",
            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y",
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
    return None


def _excel_duration_datetime(v: datetime) -> int | None:
    """A duration cell of 1 day or more comes back from openpyxl as a datetime near
    the Excel epoch (e.g. 1900-01-01 20:49:07 = 1 day 20:49:07). openpyxl shifts
    serials below 60 by one day for Excel's fake 1900-02-29, so the base differs
    on either side of 1900-03-01. A real calendar date is not a duration."""
    if v.year > 1900:
        return None
    base = datetime(1899, 12, 31) if v < datetime(1900, 3, 1) else datetime(1899, 12, 30)
    return int((v - base).total_seconds())


def _raw_seconds(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return _excel_duration_datetime(v)
    if isinstance(v, time):
        return v.hour * 3600 + v.minute * 60 + v.second
    if isinstance(v, timedelta):
        return int(v.total_seconds())
    if isinstance(v, (int, float)):
        if 0 <= v <= 1:
            return int(round(v * 86400))
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        m = re.match(r"^(\d{1,3}):(\d{1,2})(?::(\d{1,2}))?$", s)
        if m:
            h, mi, sec = m.group(1), m.group(2), m.group(3) or "0"
            return int(h) * 3600 + int(mi) * 60 + int(sec)
    return None


def parse_seconds(v):
    """Duration cell -> seconds, or None when blank, an error like #VALUE!, a real
    calendar date, negative, or longer than MAX_DURATION_SEC."""
    s = _raw_seconds(v)
    if s is None or s < 0 or s > MAX_DURATION_SEC:
        return None
    return s


def _canon(v, choices):
    """Normalise a free-text status cell to its canonical spelling, ignoring case
    and surrounding spaces ("pass" -> "Pass"). Unknown values pass through as-is."""
    s = (str(v) if v is not None else "").strip()
    if not s:
        return None
    for c in choices:
        if s.lower() == c.lower():
            return c
    return s


BEFORE_WAIVE_VALUES = ("In Due", "Out Due")
AFTER_WAIVE_VALUES = ("Pass", "Not Waive")


COL_MAP = {
    "z_create_date": ["Z_CREATE_DATE"],
    "report_date": ["REPORT_DATE"],
    "create_date": ["CREATE_DATE"],
    "assign_date": ["ASSIGN_DATE"],
    "accept_date": ["ACCEPT_DATE"],
    "initiate_date": ["INITIATE_DATE"],
    "onsite_date": ["ONSITE_DATE"],
    "finish_date": ["FINISH_DATE"],
    "zone_id": ["ZONE_BY_SITE", "ZONE_ID"],
    "wfm_company": ["WFM_COMPANY"],
    "assign_to": ["ASSIGN_TO"],
    "priority": ["PRIORITY_ID"],
    "before_waive": ["Before Waive"],
    "after_waive": ["Team After Waive", "After Waive"],
    "reason_overdue": ["สาเหตุ Over Due"],
    "subcause2": ["SUBCAUSE2"],
    "accept_to_depart": ["Accept to Depart"],
    "depart_to_onsite": ["Depart to Onsite"],
    "onsite_to_done": ["Onsite to Done"],
    "total_time": ["Total Time"],
    "jb_id": ["JB_ID"],
    "solution": ["Solution"],
    "problem": ["Problem"],
}

# Without these the report has nothing to group or date by — refuse the file.
REQUIRED_COLUMNS = ("report_date", "wfm_company", "assign_to", "priority")


def _iso_dt(v):
    dt = parse_date(v)
    if not dt:
        return None
    return dt.replace(microsecond=0).isoformat()


def _text(v):
    return (str(v).strip() if v is not None else "") or None


def _pick_sheet(wb, filename_stem: str) -> str:
    """Prefer the sheet named like the file stem; else the first sheet starting with
    'Data Job done'; else the first sheet."""
    names = wb.sheetnames
    if filename_stem in names:
        return filename_stem
    for n in names:
        if n.strip().lower().startswith("data job done"):
            return n
    return names[0]


def read_workbook(path: Path, log=print) -> list[dict]:
    log(f"  loading {path.name} ...")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[_pick_sheet(wb, path.stem)]
        header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
        header = [str(h).strip() if h is not None else "" for h in header]
        idx: dict[str, int] = {}
        for key, names in COL_MAP.items():
            for nm in names:
                if nm in header:
                    idx[key] = header.index(nm)
                    break
        missing_required = [k for k in REQUIRED_COLUMNS if k not in idx]
        if missing_required:
            cols = [COL_MAP[k][0] for k in missing_required]
            raise ValueError(f"{path.name}: ไม่พบคอลัมน์ที่จำเป็น {cols} ในชีต '{ws.title}'")
        missing = [k for k in COL_MAP if k not in idx and k != "total_time"]
        if missing:
            log(f"    !!! missing columns in {path.name}: {missing}")
        rows: list[dict] = []
        for r in ws.iter_rows(min_row=2, values_only=True):
            rows.append({k: (r[idx[k]] if k in idx and idx[k] < len(r) else None) for k in COL_MAP})
        return rows
    finally:
        wb.close()


def _total_seconds(r: dict):
    """Total Time. The workbooks have no "Total Time" column, so derive it as
    REPORT_DATE - ACCEPT_DATE (equals Accept->Depart + Depart->Onsite + Onsite->Done
    to within a minute on 98.5% of rows). A real column still wins."""
    if r.get("total_time") not in (None, ""):
        return parse_seconds(r.get("total_time"))
    accept = parse_date(r.get("accept_date"))
    report = parse_date(r.get("report_date") or r.get("finish_date"))
    if not accept or not report:
        return None
    secs = int((report - accept).total_seconds())
    return secs if 0 <= secs <= MAX_DURATION_SEC else None


def transform(raw: list[dict]) -> dict[str, dict]:
    """-> {slug: {"name", "rule", "records": [...], "teams": {zone: {team: sortkey}},
    "areas": {zone: area_no}}}."""
    out: dict[str, dict] = {}
    for r in raw:
        dt = parse_date(r.get("report_date")) or parse_date(r.get("z_create_date"))
        if not dt:
            continue
        zid = _text(r.get("zone_id"))
        assign = _text(r.get("assign_to"))
        cls = classify(_text(r.get("wfm_company")), assign, zid)
        co = out.setdefault(cls["slug"], {
            "name": cls["company"], "rule": cls["rule"], "records": [],
            "teams": defaultdict(dict), "areas": {},
        })
        rec = {
            "d": dt.date().isoformat(),
            # Full timestamps for the Gantt view: ct create, gt assign, at accept,
            # it initiate (depart), nt onsite, rt report (finish).
            "ct": _iso_dt(r.get("create_date") or r.get("z_create_date")),
            "gt": _iso_dt(r.get("assign_date")),
            "at": _iso_dt(r.get("accept_date")),
            "it": _iso_dt(r.get("initiate_date")),
            "nt": _iso_dt(r.get("onsite_date")),
            "rt": _iso_dt(r.get("report_date") or r.get("finish_date")),
            "zid": zid,
            "a": assign,
            "p": _text(r.get("priority")),
            "bw": _canon(r.get("before_waive"), BEFORE_WAIVE_VALUES),
            "aw": _canon(r.get("after_waive"), AFTER_WAIVE_VALUES),
            "ro": _text(r.get("reason_overdue")),
            "sc": _text(r.get("subcause2")),
            "ad": parse_seconds(r.get("accept_to_depart")),
            "do": parse_seconds(r.get("depart_to_onsite")),
            "od": parse_seconds(r.get("onsite_to_done")),
            "tt": _total_seconds(r),
            "sol": _text(r.get("solution")),
            "prb": _text(r.get("problem")),
            "jb": _text(r.get("jb_id")),
            "z": cls["zone"],
            "t": cls["team"],
        }
        co["records"].append(rec)
        co["teams"][cls["zone"]].setdefault(cls["team"], cls["sort"])
        if cls["zone"] not in co["areas"]:
            area = mnm_area(zid) if cls["rule"] == "mnm" else None
            co["areas"][cls["zone"]] = area[0] if area else None
    return out


def _company_meta(slug: str, co: dict) -> dict:
    recs = co["records"]
    zone_jobs: dict[str, int] = defaultdict(int)
    for r in recs:
        zone_jobs[r["z"]] += 1
    teams_sorted = {
        z: [t for t, _ in sorted(ts.items(), key=lambda kv: (kv[1], kv[0]))]
        for z, ts in co["teams"].items()
    }
    zones = [
        {"name": z, "jobs": zone_jobs[z], "teams": teams_sorted[z]}
        for z in zone_order(slug, co["rule"], co["areas"])
    ]
    days = [r["d"] for r in recs]
    return {
        "slug": slug,
        "name": co["name"],
        "total": len(recs),
        "date_min": min(days) if days else None,
        "date_max": max(days) if days else None,
        "zones": zones,
        "other_jobs": zone_jobs.get(OTHER_ZONE, 0),
        "other_teams": teams_sorted.get(OTHER_ZONE, []),
    }


def _write_json(path: Path, payload, attempts: int = 20) -> None:
    """Write via a temp file + replace so a reader never sees half a file. On
    Windows the replace fails while another handle has the file open — retry."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    for i in range(attempts):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            _time.sleep(0.25)


# ---------- Public entry point ----------

def build_dataset(excel_dir: Path, data_dir: Path, *, log=print) -> dict:
    excel_dir = Path(excel_dir)
    data_dir = Path(data_dir)
    files = list_excel_files(excel_dir)
    if not files:
        raise FileNotFoundError(f"No 'Data Job done <YEAR>.xls[xm]' files in {excel_dir}")

    all_rows: list[dict] = []
    file_info: list[dict] = []
    for path, year in files:
        rows = read_workbook(path, log=log)
        all_rows.extend(rows)
        st = path.stat()
        file_info.append({
            "name": path.name,
            "year": year,
            "size": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            "raw_rows": len(rows),
        })
    log(f"loaded {len(all_rows)} raw rows from {len(files)} file(s)")

    companies = transform(all_rows)
    data_dir.mkdir(parents=True, exist_ok=True)

    metas = []
    for slug, co in companies.items():
        co["records"].sort(key=lambda r: r["d"])
        _write_json(data_dir / f"{slug}.json", {"records": co["records"]})
        metas.append(_company_meta(slug, co))
    metas.sort(key=lambda m: -m["total"])

    days = [m[k] for m in metas for k in ("date_min", "date_max") if m[k]]
    generated_at = datetime.now().isoformat(timespec="seconds")
    meta = {
        "etl_version": ETL_VERSION,
        "generated_at": generated_at,
        "date_min": min(days) if days else None,
        "date_max": max(days) if days else None,
        "total": sum(m["total"] for m in metas),
        "files": file_info,
        "companies": metas,
    }
    # meta.json goes last: it is what tells readers which company files exist.
    _write_json(data_dir / "meta.json", meta)
    keep = {f"{m['slug']}.json" for m in metas} | {"meta.json"}
    for p in data_dir.glob("*.json"):
        if p.name not in keep:
            p.unlink(missing_ok=True)

    log(f"emit {meta['total']} records in {len(metas)} companies ({meta['date_min']} -> {meta['date_max']})")
    return {k: meta[k] for k in ("generated_at", "date_min", "date_max", "total", "files")} | {
        "companies": [{"slug": m["slug"], "name": m["name"], "total": m["total"]} for m in metas]
    }


def _cli():
    """python -m server.etl [excel_dir] [data_dir]"""
    here = Path(__file__).resolve().parent
    excel_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "storage" / "excel"
    data_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else here / "storage" / "data"
    info = build_dataset(excel_dir, data_dir, log=lambda m: print(m, file=sys.stderr))
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()

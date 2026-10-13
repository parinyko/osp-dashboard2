"""Closed jobs per team: the Monthly Report's "Data Job done" workbook for the days it covers,
and closures seen between /dashboard uploads for the days after it.

The workbook (~50 MB) sits in MONTHLY_EXCEL_DIR, mounted read-only from the Monthly
Report app. Reading it takes several seconds, so it is parsed in a background thread
whenever the file changes, and only compact counts are kept:
(assignee, day, priority, work group) -> jobs closed.
"""
import collections
import glob
import json
import os
import threading

import pandas as pd

EXCEL_DIR = os.environ.get("MONTHLY_EXCEL_DIR", "")
COLUMNS = ["ASSIGN_TO", "PRIORITY_ID", "REPORT_DATE", "SUBSYSTEM"]
PRIORITY_KEY = {"critical": "c", "major": "m", "minor": "n"}

_lock = threading.Lock()
_state = {"key": None, "data": None, "loading": False, "error": ""}


def _workbook():
    """Newest .xlsx in EXCEL_DIR, preferring one named like 'Data Job done'."""
    if not EXCEL_DIR or not os.path.isdir(EXCEL_DIR):
        return ""
    files = [f for f in glob.glob(os.path.join(EXCEL_DIR, "*.xls*")) if not os.path.basename(f).startswith("~$")]
    named = [f for f in files if "job done" in os.path.basename(f).lower()]
    files = named or files
    return max(files, key=os.path.getmtime) if files else ""


def _parse(path, sub_group):
    book = pd.ExcelFile(path)
    sheet = next((s for s in book.sheet_names if s.lower().startswith("data job done")), book.sheet_names[0])
    df = book.parse(sheet, usecols=COLUMNS)
    when = pd.to_datetime(df["REPORT_DATE"], errors="coerce")
    rows = collections.Counter()
    for name, pri, day, sub in zip(df["ASSIGN_TO"], df["PRIORITY_ID"], when, df["SUBSYSTEM"]):
        p = PRIORITY_KEY.get(str(pri).strip().lower())
        if not p or pd.isna(day):
            continue
        g = sub_group.get(str(sub).strip().casefold(), "")
        rows[(str(name).strip().casefold(), day.strftime("%Y-%m-%d"), p, g)] += 1
    days = [k[1] for k in rows]
    return {
        "rows": rows,
        "first": min(days) if days else "",
        "last": when.max().strftime("%Y-%m-%d %H:%M") if days else "",
        "file": os.path.basename(path),
        "sheet": sheet,
    }


def _load(path, key, sub_group):
    try:
        data = _parse(path, sub_group)
        with _lock:
            _state.update(key=key, data=data, error="")
    except Exception as exc:  # keep serving the previous counts, show why the new file failed
        with _lock:
            _state.update(key=key, error=f"อ่านไฟล์ {os.path.basename(path)} ไม่สำเร็จ: {exc}")
    finally:
        with _lock:
            _state["loading"] = False


def snapshot(sub_group):
    """Current counts (or None while the first read runs) plus a status dict.
    Starts a background re-read when the workbook changed since the last one."""
    path = _workbook()
    with _lock:
        if not path:
            return _state["data"], {"loading": False, "error": "ไม่พบไฟล์ Data Job done (ตั้ง MONTHLY_EXCEL_DIR)"}
        key = (path, os.path.getmtime(path))
        if key != _state["key"] and not _state["loading"]:
            _state["loading"] = True
            threading.Thread(target=_load, args=(path, key, sub_group), daemon=True).start()
        return _state["data"], {"loading": _state["loading"], "error": _state["error"]}


# ---------------------------------------------------------------- closures seen in /dashboard uploads
# The Monthly Report workbook is updated only now and then, so days after its last close date
# come from the JobMonitor files people upload at /dashboard. Those hold open jobs only: a job
# counts as closed at the upload where it first shows "Done(Not Leave)" or where it is gone
# from the file (unless it was last seen as Cancel). A job that comes back later is uncounted.
LEDGER_KEEP_DAYS = 400
_ledger_lock = threading.Lock()


def _read_ledger(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("baseline", None)
            data.setdefault("done", {})
            return data
    except (OSError, ValueError):
        pass
    return {"baseline": None, "done": {}}


def _write_ledger(path, data):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def record_upload(path, jobs, stamp):
    """jobs: {job_id: [assignee, priority key, group, status]} for every OSP job in the upload.
    stamp: upload time 'YYYY-MM-DD HH:MM'. Returns how many closures were added."""
    with _ledger_lock:
        led = _read_ledger(path)
        prev = (led["baseline"] or {}).get("jobs", {})
        done = led["done"]
        is_dnl = lambda st: str(st).lower().startswith("done")
        open_prev = sum(1 for v in prev.values() if not is_dnl(v[3]))
        open_now = sum(1 for v in jobs.values() if not is_dnl(v[3]))
        # a filtered / partial export would look like a mass closure: skip "gone" for it
        partial = bool(prev) and open_now < open_prev * 0.5
        added = 0
        day = stamp[:10]
        for jid, (who, p, g, st) in jobs.items():
            if is_dnl(st):
                if jid not in done:
                    done[jid] = [day, stamp, who, p, g, "dnl"]; added += 1
            elif jid in done and done[jid][5] == "gone":
                del done[jid]; added -= 1          # it came back: not closed after all
        if not partial:
            for jid, (who, p, g, st) in prev.items():
                if jid not in jobs and jid not in done and str(st).lower() != "cancel":
                    done[jid] = [day, stamp, who, p, g, "gone"]; added += 1
            led["baseline"] = {"t": stamp, "jobs": jobs}
        cutoff = (pd.Timestamp(day) - pd.Timedelta(days=LEDGER_KEEP_DAYS)).strftime("%Y-%m-%d")
        led["done"] = {k: v for k, v in done.items() if v[0] >= cutoff}
        led["partial_skipped"] = stamp if partial else led.get("partial_skipped", "")
        _write_ledger(path, led)
        return added


def upload_closures(path):
    """{(assignee casefold, day, priority, group): jobs} from the ledger, plus its start time."""
    with _ledger_lock:
        led = _read_ledger(path)
    rows = collections.Counter()
    for day, _, who, p, g, _how in led["done"].values():
        rows[(str(who).strip().casefold(), day, p, g)] += 1
    start = led.get("since") or ((led["baseline"] or {}).get("t", ""))
    return rows, {"since": start, "latest": (led["baseline"] or {}).get("t", "")}


def mark_since(path, stamp):
    """Remember when upload tracking began (the first baseline)."""
    with _ledger_lock:
        led = _read_ledger(path)
        if not led.get("since"):
            led["since"] = stamp
            _write_ledger(path, led)

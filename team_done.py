"""Closed jobs per team, read from the Monthly Report's "Data Job done" workbook.

The workbook (~50 MB) sits in MONTHLY_EXCEL_DIR, mounted read-only from the Monthly
Report app. Reading it takes several seconds, so it is parsed in a background thread
whenever the file changes, and only compact counts are kept:
(assignee, day, priority, work group) -> jobs closed.
"""
import collections
import glob
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

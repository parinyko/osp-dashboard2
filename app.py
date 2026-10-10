# -*- coding: utf-8 -*-
"""Job Dashboard / Resource Monitor - rebuilt clean Flask application."""
from __future__ import annotations

import json
import os
import re
import time
import threading
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from flask import Flask, render_template, request, redirect, jsonify, flash, send_file
from werkzeug.utils import secure_filename

import network_map as nm

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

# Monthly Report is a separate app; unset = its menu entries stay hidden.
MONTHLY_REPORT_URL = os.environ.get("MONTHLY_REPORT_URL", "")


@app.context_processor
def inject_links():
    return {"monthly_report_url": MONTHLY_REPORT_URL}

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
TZ = ZoneInfo("Asia/Bangkok")

REMARK_FILE = BASE_DIR / "remarks.json"
CONTACT_FILE = BASE_DIR / "contacts.json"
DAILY_OSP_FILE = BASE_DIR / "daily_osp_remain.json"
RESOURCE_FILE = BASE_DIR / "resource_monitor_history.json"
DAILY_OSP_SCHEDULE_FILE = BASE_DIR / "daily_osp_schedule.json"
DAILY_OSP_DEFAULT_TIMES = ["06:00", "18:00"]
DAILY_OSP_MAX_RECORDS = 730
RESOURCE_MONITOR_MAX_RECORDS = 20000

VALID_SUBSYSTEMS = [
    "EDS-OSP", "ETS-OSP", "FTTB-OSP", "FTTH-OSP", "FTTX-OSP",
    "Splitter-OSP", "Transmission-OSP", "EDS SW NODE-OSP", "EDS IPLC-OSP",
]

TEAM_DATA = [
    {"zone":"DMP","user":f"Dmplocallatkrabang {x}"} for x in "ABC"
] + [
    {"zone":"DMP","user":f"Dmplocalpathumthani {x}"} for x in "ABC"
] + [{"zone":"Origin","user":"Originlocal Center"}] + [
    {"zone":"Origin","user":f"Originlocalthungkhru {x}"} for x in "ABC"
] + [
    {"zone":"Origin","user":f"Originlocalnonthaburi {x}"} for x in "ABC"
] + [{"zone":"EDS BKK","user":f"Exeds {x}"} for x in "AB"] + [
    {"zone":"SCT","user":f"Exsct {x}"} for x in "ABC"
] + [{"zone":"SCT","user":"Extrsct E"}] + [
    {"zone":"BPL","user":f"Exbpl {x}"} for x in "ABCDE"
] + [{"zone":"BPL","user":f"Extrbpl {x}"} for x in "FG"] + [
    {"zone":"TLC","user":f"Extlc {x}"} for x in "ABCDE"
] + [{"zone":"TLC","user":"Extrtlc F"}] + [
    {"zone":"CWT","user":f"Excwt {x}"} for x in "ABCDE"
] + [{"zone":"CWT","user":f"Extrcwt {x}"} for x in "FGH"] + [
    {"zone":"Team Spare","user":f"Exspare {x}"} for x in "ABCDEFGHI"
] + [
    {"zone":"BKK2","user":u} for u in ["Kitsada Wiraphan","Poolsak Saenmee","Chawalit Bunrod"]
] + [{"zone":"SPK","user":u} for u in ["Sittikorn Pantanoo","Phongsakron Topradit","Preecha Ruamsungneon"]] + [
    {"zone":"NTB","user":u} for u in ["Piriya Sripoon","Cherdchai Wandee","Piyanut Wattanonda"]
] + [{"zone":"AIS","user":u} for u in ["Ruj Chalanun","Parinya Khoonkrong","Songwat Sintanarot","Boonsom Duangjun","Nares Vongkasigum"]]

DASHBOARD_EXCLUDED_ZONES = {"BKK2", "SPK", "NTB", "AIS"}
ASSIGN_ORDER = [t["user"] for t in TEAM_DATA] + ["Workforce BKK Pool"]
AREA_DATA = {
    "Dmplocallatkrabang A":"หนองจอก มีนบุรี คลองสามวา คันนายาว บึงกุ่ม",
    "Dmplocallatkrabang B":"สวนหลวง ลาดกระบัง บางกะปิ",
    "Dmplocallatkrabang C":"สะพานสูง ประเวศ บางนา",
    "Dmplocalpathumthani A":"เมืองปทุมธานี สามโคก ลาดหลุมแก้ว",
    "Dmplocalpathumthani B":"คลองหลวง หนองเสือ",
    "Dmplocalpathumthani C":"ลำลูกกา ธัญบุรี",
    "Originlocal Center":"",
    "Originlocalthungkhru A":"บางขุนเทียน ราษฎร์บูรณะ จอมทอง",
    "Originlocalthungkhru B":"ทุ่งครุ บางบอน ทวีวัฒนา",
    "Originlocalthungkhru C":"หนองแขม บางแค ภาษีเจริญ",
    "Originlocalnonthaburi A":"บางใหญ่ บางบัวทอง ไทรน้อย เมืองนนทบุรี ปากเกร็ด",
    "Originlocalnonthaburi B":"บางใหญ่ บางบัวทอง ไทรน้อย เมืองนนทบุรี ปากเกร็ด",
    "Originlocalnonthaburi C":"บางใหญ่ บางบัวทอง ไทรน้อย เมืองนนทบุรี ปากเกร็ด",
    "Exsct A":"ลาดพร้าว จตุจักร บางซื่อ วังทองหลาง ห้วยขวาง ดินแดง พญาไท",
    "Exsct B":"ดุสิต ราชเทวี วัฒนา คลองเตย ปทุมวัน ป้อมปราบศัตรูพ่าย พระนคร สัมพันธวงศ์",
    "Exsct C":"บางรัก สาธร ยานนาวา บางคอแหลม คลองเตย",
    "Extrsct E":"Around the zone (Night)",
    "Exbpl A":"สะพานสูง มีนบุรี หนองจอก ลาดกระบัง รามคำแหง",
    "Exbpl B":"บางพลี(ตอนล่าง) บางเสาธง(ตอนล่าง) บางบ่อ(ตอนล่าง)",
    "Exbpl C":"บางพลี(ตอนบน) บางเสาธง(ตอนบน) บางบ่อ(ตอนบน)",
    "Exbpl D":"บางนา พระประแดง เมืองสมุทรปราการ",
    "Exbpl E":"Around the zone (Night)",
    "Extrbpl F":"คลองเตย พระโขนง สวนหลวง ประเวศ",
    "Extrbpl G":"บางกะปิ วังทองหลาง ห้วยขวาง วัฒนา",
    "Extlc A":"บางขุนเทียน พระสมุทรเจดีย์ พระประแดง ทุ่งครุ ราษฎร์บูรณะ จอมทอง บางบอน",
    "Extlc B":"บางพลัด บางกรวย บางใหญ่ เมืองนนทบุรี (Zone TLC)",
    "Extlc C":"ปากเกร็ด บางบัวทอง ไทรน้อย(ตอนล่าง) ไทรน้อย(ตอนบน)",
    "Extlc D":"Around the zone (Night)",
    "Extlc E":"หนองแขม บางแค ภาษีเจริญ ธนบุรี คลองสาน บางกอกใหญ่ บางกอกน้อย ตลิ่งชัน ทวีวัฒนา",
    "Extrtlc F":"Around the zone (Night)",
    "Excwt A":"Around the zone (Night)",
    "Excwt B":"สามโคก(ฝั่งตะวันออก) เมืองปทุมธานี(ฝั่งตะวันออก) ธัญบุรี(คลอง1-7) คลองหลวง(คลอง1-7)",
    "Excwt C":"ลำลูกกา หนองจอก คลองสามวา มีนบุรี รามอินทรา",
    "Excwt D":"ธัญบุรี(คลอง7 เป็นต้นไป) คลองหลวง(คลอง7 เป็นต้นไป) หนองเสือ",
    "Excwt E":"บางซื่อ หลักสี่ เมืองนนทบุรี ปากเกร็ด ดอนเมือง",
    "Extrcwt F":"เมืองปทุม(ฝั่งตะวันตก) สามโคก(ฝั่งตะวันตก) ลาดหลุมแก้ว",
    "Extrcwt G":"Around the zone (Night)",
    "Extrcwt H":"คันนายาว บึงกุ่ม ลาดพร้าว บางเขน สายไหม จตุจักร",
    "Exeds A":"All Zone (เน้น RRU กับงานภายในห้าง ทุกโซน)",
    "Exeds B":"All Zone",
    "Exspare A":"ปากเกร็ด บางบัวทอง ไทรน้อย",
}
for _u in [f"Exspare {x}" for x in "BCDEFGHI"]:
    AREA_DATA[_u] = "Team Spare"

def now_local():
    return datetime.now(TZ)

def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()

def load_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, (dict, list)) else default
    except (OSError, json.JSONDecodeError, TypeError):
        return default.copy() if isinstance(default, (dict, list)) else default

def atomic_save_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

REMARKS = load_json_file(REMARK_FILE, {})
CONTACTS = load_json_file(CONTACT_FILE, {})
def load_history(path):
    data = load_json_file(path, {})
    if isinstance(data, dict):
        data = data.get("records", [])
    return data if isinstance(data, list) else []

def save_history(path, records):
    atomic_save_json(path, {"version": 1, "updated_at": now_local().isoformat(), "records": records})

DAILY_OSP_HISTORY = load_history(DAILY_OSP_FILE)

# Daily OSP Remain auto-snapshot times ("HH:MM", Asia/Bangkok), set from the page.
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

def normalize_times(values):
    return sorted({str(v).strip() for v in values if TIME_RE.match(str(v).strip())})

def load_daily_osp_times():
    data = load_json_file(DAILY_OSP_SCHEDULE_FILE, {})
    if isinstance(data, dict) and isinstance(data.get("times"), list):
        return normalize_times(data["times"])   # may be empty = auto snapshot off
    return list(DAILY_OSP_DEFAULT_TIMES)

DAILY_OSP_TIMES = load_daily_osp_times()

# Password for changing the schedule. Set on the server (deploy compose), never in this public repo.
# Unset = no password (local dev).
SCHEDULE_PASSWORD = os.environ.get("SCHEDULE_PASSWORD", "")
SCHEDULE_FAILS = {}   # client ip -> [timestamps of wrong passwords]

def client_ip():
    return request.headers.get("CF-Connecting-IP") or request.remote_addr or "-"
RESOURCE_HISTORY = load_history(RESOURCE_FILE)
DATA, RAW_DATA, ORIGINAL_DATA = [], [], []
LAST_UPDATE = "-"
TOTAL_JOBS = TOTAL_CRITICAL = TOTAL_MAJOR = TOTAL_MINOR = 0
TOTAL_SCT = TOTAL_CWT = TOTAL_ONT = TOTAL_TLC = 0
DATA_LOCK = threading.RLock()

def dashboard_teams():
    return [dict(t) for t in TEAM_DATA if t["zone"] not in DASHBOARD_EXCLUDED_ZONES]

def get_status_color(status_text):
    s = clean_text(status_text).lower()
    if "on-site" in s or "onsite" in s: return "#c6efce"
    if "departed" in s: return "#ffe699"
    if "assigned" in s or "accepted" in s: return "#ffc7ce"
    if "held" in s: return "#9fd5ff"
    return "#ffffff"

def normalize_status_series(df):
    return df["Status"].fillna("").astype(str).str.strip().str.lower() if "Status" in df else pd.Series("", index=df.index)

def normalize_priority_series(df):
    return df["Priority"].fillna("").astype(str).str.strip().str.lower() if "Priority" in df else pd.Series("", index=df.index)

def prepare_job_dataframe(df):
    required = ["Sub System", "Status", "Priority", "Assign to"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("ไม่พบคอลัมน์ที่จำเป็น: " + ", ".join(missing))
    out = df.copy()
    subsystem = out["Sub System"].fillna("").astype(str).str.strip()
    status = normalize_status_series(out)
    priority = normalize_priority_series(out)
    out = out[subsystem.isin(VALID_SUBSYSTEMS)].copy()
    status = normalize_status_series(out)
    priority = normalize_priority_series(out)
    out = out[~status.str.contains("done(not leave)", regex=False)]
    out = out[priority.ne("") & priority.ne("none")].copy()
    order = {name: i for i, name in enumerate(ASSIGN_ORDER)}
    out["_sort"] = out["Assign to"].fillna("").astype(str).str.strip().map(order).fillna(9999)
    out = out.sort_values(["_sort", "Assign to"], kind="stable").drop(columns="_sort")
    return out

def calculate_totals(df):
    p = normalize_priority_series(df)
    zone = df["Zone"].fillna("").astype(str) if "Zone" in df else pd.Series("", index=df.index)
    return dict(jobs=len(df), critical=int((p=="critical").sum()), major=int((p=="major").sum()),
                minor=int((p=="minor").sum()), sct=int(zone.str.contains("Bangkok-ST2",case=False,na=False).sum()),
                cwt=int(zone.str.contains("Bangkok-CWT",case=False,na=False).sum()),
                ont=int(zone.str.contains("Bangkok-ONT",case=False,na=False).sum()),
                tlc=int(zone.str.contains("Bangkok-TLC",case=False,na=False).sum()))

def build_dashboard_data(df):
    rows = []
    for team in dashboard_teams():
        user = team["user"]
        assigned = df[df["Assign to"].fillna("").astype(str).str.strip().str.casefold() == user.casefold()] if "Assign to" in df else df.iloc[0:0]
        statuses = [clean_text(v) for v in assigned.get("Status", []) if clean_text(v)]
        joined = ", ".join(dict.fromkeys(statuses))
        low = joined.lower()
        work = "On-site" if ("on-site" in low or "onsite" in low) else ("Departed" if "departed" in low else ("Working" if len(assigned) else "ว่าง"))
        rows.append({"zone":team["zone"], "user":user, "area":AREA_DATA.get(user,"Team Spare" if team["zone"]=="Team Spare" else ""),
                     "work_status":work, "job_count":len(assigned), "status_text":joined,
                     "status_color":get_status_color(joined), "contact":CONTACTS.get(user,""), "remark":REMARKS.get(user,"")})
    return rows

def empty_dashboard_data():
    return [{"zone":t["zone"],"user":t["user"],"area":AREA_DATA.get(t["user"],""),
             "work_status":"ว่าง","job_count":0,"status_text":"","status_color":"#ffffff",
             "contact":CONTACTS.get(t["user"],""),"remark":REMARKS.get(t["user"],"")} for t in dashboard_teams()]

def apply_group_rowspans(rows):
    out = [dict(r) for r in rows]
    counts = {}
    for r in out: counts[r["zone"]] = counts.get(r["zone"],0)+1
    seen = set()
    for r in out:
        r["show_zone"] = r["zone"] not in seen
        r["rowspan"] = counts[r["zone"]] if r["show_zone"] else 0
        seen.add(r["zone"])
    return out

def update_global_data(df):
    global DATA, RAW_DATA, ORIGINAL_DATA, LAST_UPDATE, TOTAL_JOBS, TOTAL_CRITICAL, TOTAL_MAJOR, TOTAL_MINOR
    global TOTAL_SCT, TOTAL_CWT, TOTAL_ONT, TOTAL_TLC
    prepared = prepare_job_dataframe(df)
    totals = calculate_totals(prepared)
    with DATA_LOCK:
        ORIGINAL_DATA = df.fillna("").to_dict(orient="records")
        RAW_DATA = prepared.fillna("").to_dict(orient="records")
        DATA = build_dashboard_data(prepared)
        TOTAL_JOBS, TOTAL_CRITICAL, TOTAL_MAJOR, TOTAL_MINOR = totals["jobs"], totals["critical"], totals["major"], totals["minor"]
        TOTAL_SCT, TOTAL_CWT, TOTAL_ONT, TOTAL_TLC = totals["sct"], totals["cwt"], totals["ont"], totals["tlc"]
        LAST_UPDATE = now_local().strftime("%Y-%m-%d %H:%M:%S")

def get_latest_upload_path():
    files = [p for p in UPLOAD_FOLDER.iterdir() if p.is_file() and p.suffix.lower() in (".xlsx",".xls")]
    return max(files, key=lambda p:p.stat().st_mtime) if files else None

def load_latest_excel_into_memory():
    path = get_latest_upload_path()
    if path is None: return False
    try:
        update_global_data(pd.read_excel(path))
        return True
    except Exception as exc:
        app.logger.exception("Cannot load Excel %s: %s", path, exc)
        return False

def load_daily_osp_history():
    global DAILY_OSP_HISTORY
    DAILY_OSP_HISTORY = load_history(DAILY_OSP_FILE)
    return DAILY_OSP_HISTORY

def save_daily_osp_snapshot(slot="Manual", allow_duplicate=False):
    global DAILY_OSP_HISTORY
    if not RAW_DATA: load_latest_excel_into_memory()
    if not RAW_DATA: raise ValueError("ยังไม่มีข้อมูล กรุณา Upload Excel ก่อน")
    prepared = pd.DataFrame(RAW_DATA)
    now = now_local()
    sub = prepared["Sub System"].fillna("").astype(str).str.strip()
    pri = normalize_priority_series(prepared)
    rows = []
    for name in VALID_SUBSYSTEMS:
        m = sub.eq(name)
        rows.append({"subsystem": name, "critical": int((m & pri.eq("critical")).sum()),
                     "major": int((m & pri.eq("major")).sum()), "minor": int((m & pri.eq("minor")).sum()),
                     "total": int(m.sum())})
    record = {"timestamp": now.strftime("%d/%m/%Y %H:%M:%S"), "iso_timestamp": now.isoformat(),
              "date": now.strftime("%Y-%m-%d"), "slot": slot, "last_update": LAST_UPDATE,
              "totals": {"critical": sum(r["critical"] for r in rows), "major": sum(r["major"] for r in rows),
                         "minor": sum(r["minor"] for r in rows), "grand_total": sum(r["total"] for r in rows)},
              "subsystems": rows}
    if not allow_duplicate and any(r.get("date")==record["date"] and r.get("slot")==slot for r in DAILY_OSP_HISTORY):
        return DAILY_OSP_HISTORY[-1], False
    DAILY_OSP_HISTORY.append(record)
    DAILY_OSP_HISTORY = DAILY_OSP_HISTORY[-DAILY_OSP_MAX_RECORDS:]
    save_history(DAILY_OSP_FILE, DAILY_OSP_HISTORY)
    return record, True

def load_resource_history():
    global RESOURCE_HISTORY
    RESOURCE_HISTORY = load_history(RESOURCE_FILE)
    return RESOURCE_HISTORY

# A team can hold several jobs at once. The one it is working on is the most advanced:
# On-Site > Departed > Accepted > Assigned > Held.
STATUS_RANK = (("on-site", 5), ("onsite", 5), ("departed", 4), ("accepted", 3), ("assigned", 2), ("held", 1))

def status_rank(status):
    low = clean_text(status).lower()
    return max((r for k, r in STATUS_RANK if k in low), default=0)

# The JobMonitor export has no SITE_CODE column, but every Job Title starts with it:
# "[Important] PADUM-[1605]SitePriority=..." -> PADUM (matches SITE_CODE of the
# "Data Job done" export for 99.6% of jobs; the rest carry a sub-site suffix like LWSWB_RM).
TITLE_TAGS_RE = re.compile(r"^(\s*\[[^\]]*\]\s*)+")
SITE_CODE_RE = re.compile(r"[A-Za-z0-9_./]{2,40}")

def site_code_from_title(title):
    t = TITLE_TAGS_RE.sub("", clean_text(title))
    if "-" not in t: return ""
    code = t.split("-", 1)[0].strip()
    return code if SITE_CODE_RE.fullmatch(code) else ""

# Resource Monitor company filter: zone -> company.
ZONE_COMPANY = {"DMP": "DMP", "Origin": "Origin"}

def zone_company(zone):
    return ZONE_COMPANY.get(zone, "Ex-Press")

def save_resource_snapshot():
    global RESOURCE_HISTORY
    stamp = now_local()
    rows = []
    df = pd.DataFrame(RAW_DATA) if RAW_DATA else pd.DataFrame()
    for t in dashboard_teams():
        user=t["user"]
        jobs = df[df["Assign to"].fillna("").astype(str).str.strip().str.casefold()==user.casefold()] if "Assign to" in df else df.iloc[0:0]
        job_list = [{"job_id":clean_text(j.get("Job ID",j.get("JobID",""))),"status":clean_text(j.get("Status","")),
                     "priority":clean_text(j.get("Priority","")),"create_time":clean_text(j.get("Create Time","")),
                     "site":site_code_from_title(j.get("Job Title",""))}
                    for j in jobs.to_dict("records")]
        # Each cell used to show the first job with every job's status joined ("Accepted, On-Site"),
        # so the status often belonged to another job. Show the team's current job with its own status.
        main = max(job_list, key=lambda j: status_rank(j["status"])) if job_list else {}
        rows.append({"zone":t["zone"],"user":user,"status":main.get("status",""),"job_id":main.get("job_id",""),
                     "priority":main.get("priority",""),"create_time":main.get("create_time",""),"site":main.get("site",""),
                     "due_status":resource_due_status(main.get("priority",""),main.get("create_time",""),stamp),
                     "job_count":len(job_list),
                     "others":[{"job_id":j["job_id"],"status":j["status"],"site":j["site"]} for j in job_list if j is not main]})
    # The page shows 30-minute slots, so file the snapshot under its slot (23:17 -> 23:00).
    # An upload mid-slot replaces that slot's earlier snapshot, so a slot shows its latest state.
    slot=f"{stamp.hour:02d}:{0 if stamp.minute < 30 else 30:02d}"
    rec={"date":stamp.strftime("%Y-%m-%d"),"time":slot,"timestamp":stamp.isoformat(),"rows":rows}
    RESOURCE_HISTORY=[r for r in RESOURCE_HISTORY if not (r.get("date")==rec["date"] and r.get("time")==slot)]
    RESOURCE_HISTORY.append(rec)
    RESOURCE_HISTORY=RESOURCE_HISTORY[-RESOURCE_MONITOR_MAX_RECORDS:]
    save_history(RESOURCE_FILE,RESOURCE_HISTORY)
    return rec

def resource_due_status(priority, create_time, now=None):
    p=clean_text(priority).lower()
    if not create_time: return ""
    try:
        dt=pd.to_datetime(create_time, errors="coerce")
        if pd.isna(dt): return ""
        if getattr(dt,"tzinfo",None) is None: dt=dt.tz_localize(TZ)
        else: dt=dt.tz_convert(TZ)
        hours=((now or now_local())-dt.to_pydatetime()).total_seconds()/3600
        if p=="critical":
            return "Indue" if hours < 3 else "Outdue"
        if p=="major":
            return "Indue" if hours < 10 else "Outdue"
    except Exception:
        return ""
    return ""

def background_scheduler():
    last_minute = None
    while True:
        now=now_local()
        minute = now.strftime("%Y-%m-%d %H:%M")
        if minute != last_minute:
            last_minute = minute
            try:
                if now.minute in (0,30):
                    save_resource_snapshot()
                hhmm = now.strftime("%H:%M")
                if hhmm in DAILY_OSP_TIMES:
                    save_daily_osp_snapshot(hhmm)
                if hhmm == "03:15":   # Job Map: refresh the site position table once a day
                    threading.Thread(target=rebuild_site_table, name="site-table", daemon=True).start()
            except Exception:
                app.logger.exception("Scheduled snapshot failed")
        time.sleep(15)

def get_request_value(name):
    payload=request.get_json(silent=True) or {}
    return payload.get(name, request.form.get(name,""))

@app.route("/save_remark", methods=["POST"])
def save_remark():
    user=clean_text(get_request_value("user")); remark=clean_text(get_request_value("remark"))
    if not user: return jsonify(success=False,message="ไม่พบ User"),400
    REMARKS[user]=remark; atomic_save_json(REMARK_FILE,REMARKS)
    return jsonify(success=True,user=user,remark=remark)

@app.route("/save_contact", methods=["POST"])
def save_contact():
    user=clean_text(get_request_value("user")); contact=clean_text(get_request_value("contact"))
    if not user: return jsonify(success=False,message="ไม่พบ User"),400
    CONTACTS[user]=contact; atomic_save_json(CONTACT_FILE,CONTACTS)
    return jsonify(success=True,user=user,contact=contact)

def parse_available_on(remark, now=None):
    """Return the datetime when a team becomes available from Remark.

    Supported examples:
      - Available on 22:00
      - Available on 22.00
      - Available on 03/10/2026 22:00
      - Available on 03-10-2026 22:00
      - Available on 03/10/26 22:00

    If no date is supplied, today's date in Asia/Bangkok is used.
    Returns None when the remark does not contain a usable Available on time.
    """
    text = clean_text(remark)
    if not text:
        return None

    now = now or datetime.now(ZoneInfo("Asia/Bangkok"))

    m = re.search(
        r"available\s+on\s+"
        r"(?:(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\s+)?"
        r"(\d{1,2})[:.](\d{2})",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return None

    day, month, year, hour, minute = m.groups()
    hour = int(hour)
    minute = int(minute)
    if hour > 23 or minute > 59:
        return None

    if day and month and year:
        year = int(year)
        if year < 100:
            year += 2000
        try:
            return datetime(
                year, int(month), int(day), hour, minute,
                tzinfo=ZoneInfo("Asia/Bangkok")
            )
        except ValueError:
            return None

    return datetime(
        now.year, now.month, now.day, hour, minute,
        tzinfo=ZoneInfo("Asia/Bangkok")
    )


# -----------------------------------------------------------------------------
# OSP Job Aging Summary
# -----------------------------------------------------------------------------
# Order requested for Dashboard OSP BKK.  FTTX / EDS IPLC are intentionally
# excluded from this summary because they are not part of the requested groups.
OSP_AGING_GROUPS = [
    ("EDS", [
    "EDS-OSP",
    "ETS-OSP",
    "EDS SW NODE-OSP",
    "EDS IPLC-OSP",
]),
    ("FBB", ["FTTB-OSP", "FTTH-OSP", "Splitter-OSP"]),
    ("MBB", ["Transmission-OSP"]),
]

# The Excel export may use one of these names for the Job title.  Create Time
# is handled separately below.
TITLE_COLUMN_CANDIDATES = [
    "Title", "Job Title", "Job title", "Job_Title", "TITLE",
    "ชื่อ Job", "Job Name", "Description", "รายละเอียด",
]
CREATE_TIME_COLUMN_CANDIDATES = [
    "Create Time", "Created Time", "CreateTime", "CreatedTime",
    "Create Date", "Created Date", "วันที่สร้าง", "เวลาสร้าง",
]


def _find_column(df, candidates):
    if df.empty:
        return None
    exact = {str(c).strip().casefold(): c for c in df.columns}
    for candidate in candidates:
        found = exact.get(candidate.casefold())
        if found is not None:
            return found
    # Small fallback for exports with extra spaces / punctuation.
    normalized = {}
    for c in df.columns:
        key = re.sub(r"[^a-z0-9ก-๙]+", "", str(c).strip().casefold())
        normalized[key] = c
    for candidate in candidates:
        key = re.sub(r"[^a-z0-9ก-๙]+", "", candidate.casefold())
        if key in normalized:
            return normalized[key]
    return None


def _parse_aging_datetime(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = pd.to_datetime(value, dayfirst=True, errors="coerce")
            if pd.isna(dt):
                return None
            if hasattr(dt, "to_pydatetime"):
                dt = dt.to_pydatetime()
        if dt.tzinfo is None:
            return dt.replace(tzinfo=ZoneInfo("Asia/Bangkok"))
        return dt.astimezone(ZoneInfo("Asia/Bangkok"))
    except Exception:
        return None


def _transmission_type(title):
    """Classify Transmission-OSP by keywords in the Job title."""
    text = clean_text(title).casefold()
    if "node b down" in text:
        return "BBU"
    if "rru" in text:
        return "RRU"
    if "highloss" in text or "high loss" in text:
        return "High loss"
    if "ร้องเรียน" in text:
        return "ร้องเรียน"
    return "Optic LOS"


def _empty_aging_counts():
    return {
        "today": 0,
        "lt3": 0,
        "lt7": 0,
        "lt15": 0,
        "over15": 0,
        "total": 0,
    }


def _add_aging_bucket(counts, age_days):
    # Buckets are mutually exclusive and follow the requested display order.
    if age_days < 1:
        counts["today"] += 1
    elif age_days < 3:
        counts["lt3"] += 1
    elif age_days < 7:
        counts["lt7"] += 1
    elif age_days < 15:
        counts["lt15"] += 1
    else:
        counts["over15"] += 1
    counts["total"] += 1


def build_osp_aging_summary(job_df):
    """Build the requested grouped OSP aging table from Create Time."""
    rows = []
    if job_df is None or job_df.empty:
        return rows

    subsystem_col = "Sub System" if "Sub System" in job_df.columns else None
    if subsystem_col is None:
        return rows

    title_col = _find_column(job_df, TITLE_COLUMN_CANDIDATES)
    create_col = _find_column(job_df, CREATE_TIME_COLUMN_CANDIDATES)
    if create_col is None:
        # Keep the table structure valid when an old Excel file has no Create Time.
        create_col = None

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    subsystem_series = job_df[subsystem_col].fillna("").astype(str).str.strip()
    priority_series = normalize_priority_series(job_df)

    # Filter exactly like the main Job Monitor before aging the jobs.
    status_series = normalize_status_series(job_df)
    valid_mask = subsystem_series.isin({s for _, subs in OSP_AGING_GROUPS for s in subs})
    valid_mask &= ~status_series.str.contains("done(not leave)", regex=False)
    valid_mask &= priority_series.ne("") & priority_series.ne("none")
    filtered = job_df.loc[valid_mask].copy()
    filtered_subsystems = subsystem_series.loc[filtered.index]
    filtered_priority = priority_series.loc[filtered.index]

    # Build one accumulator per requested display row.
    accumulators = {}
    for group_name, subsystems in OSP_AGING_GROUPS:
        for subsystem in subsystems:
            if subsystem == "Transmission-OSP":
                for kind in ("Optic LOS", "BBU", "RRU", "High loss", "ร้องเรียน"):
                    accumulators[(group_name, subsystem, kind)] = {
                        "critical": _empty_aging_counts(),
                        "major": _empty_aging_counts(),
                        "minor": _empty_aging_counts(),
                    }
            else:
                accumulators[(group_name, subsystem, None)] = {
                    "critical": _empty_aging_counts(),
                    "major": _empty_aging_counts(),
                    "minor": _empty_aging_counts(),
                }

    for idx, row in filtered.iterrows():
        subsystem = str(filtered_subsystems.loc[idx]).strip()
        priority = str(filtered_priority.loc[idx]).strip().casefold()
        if priority not in ("critical", "major", "minor"):
            continue

        create_dt = _parse_aging_datetime(row[create_col]) if create_col else None
        # A Job without a usable Create Time cannot be assigned an age bucket.
        if create_dt is None:
            continue
        age_days = max((now - create_dt).total_seconds() / 86400.0, 0.0)

        kind = _transmission_type(row[title_col]) if subsystem == "Transmission-OSP" and title_col else (
            "Optic LOS" if subsystem == "Transmission-OSP" else None
        )
        key = ("MBB", subsystem, kind) if subsystem == "Transmission-OSP" else next(
            (k for k in accumulators if k[1] == subsystem and k[2] is None), None
        )
        if key is None:
            continue
        _add_aging_bucket(accumulators[key][priority], age_days)

    for group_name, subsystems in OSP_AGING_GROUPS:
        for subsystem in subsystems:
            if subsystem == "Transmission-OSP":
                for kind in ("Optic LOS", "BBU", "RRU", "High loss", "ร้องเรียน"):
                    a = accumulators[(group_name, subsystem, kind)]
                    rows.append(_make_aging_row(group_name, kind, a, subsystem=subsystem, transmission=True))
            else:
                a = accumulators[(group_name, subsystem, None)]
                rows.append(_make_aging_row(group_name, subsystem, a, subsystem=subsystem, transmission=False))
    return rows


def _make_aging_row(group_name, label, a, subsystem="", transmission=False):
    row = {
        "group": group_name,
        "subsystem": subsystem,
        "label": label,
        "transmission": transmission,
    }
    grand = 0
    for priority in ("critical", "major", "minor"):
        counts = a[priority]
        for key, value in counts.items():
            row[f"{priority}_{key}"] = value
        grand += counts["total"]
    row["total"] = grand
    return row


DONE_SUBSYSTEM_GROUPS = {
    "all": [
        "EDS-OSP", "ETS-OSP", "EDS SW NODE-OSP", "EDS IPLC-OSP",
        "FTTB-OSP", "FTTH-OSP", "FTTX-OSP", "Splitter-OSP",
        "Transmission-OSP",
    ],
    "mbb": ["Transmission-OSP"],
    "eds": ["EDS-OSP", "ETS-OSP", "EDS SW NODE-OSP", "EDS IPLC-OSP"],
    "fbb": ["FTTB-OSP", "FTTH-OSP", "FTTX-OSP", "Splitter-OSP"],
}


def build_done_not_leave_by_group(source_df):
    """Return JSON-safe Done(Not Leave) totals grouped by the selected OSP subsystem group."""
    result = {}
    if source_df is None or source_df.empty or "Sub System" not in source_df.columns:
        for key in DONE_SUBSYSTEM_GROUPS:
            result[key] = {"total": 0, "rows": []}
        return result

    subsystem = source_df["Sub System"].fillna("").astype(str).str.strip()
    status = (source_df["Status"].fillna("").astype(str).str.strip().str.casefold()
              if "Status" in source_df.columns else pd.Series("", index=source_df.index))
    user = (source_df["Assign to"].fillna("").astype(str).str.strip()
            if "Assign to" in source_df.columns else pd.Series("", index=source_df.index))

    done_mask = status.eq("done(not leave)")

    for group_key, allowed in DONE_SUBSYSTEM_GROUPS.items():
        mask = done_mask & subsystem.isin(allowed)
        counts = user.loc[mask].replace("", "(ไม่ระบุ User)").value_counts()
        rows = [
            {"user": str(name), "count": int(count)}
            for name, count in counts.items()
        ]
        result[group_key] = {
            "total": int(mask.sum()),
            "rows": rows,
        }

    return result


# Zone columns of the home page; a job's Zone looks like "MNM-AREA1 (Bangkok-ST2)".
HOME_ZONE_RULES = [("SCT", "Bangkok-ST2"), ("CWT", "Bangkok-CWT"), ("ONT", "Bangkok-ONT"), ("TLC", "Bangkok-TLC")]

def build_zone_group_summary(job_df):
    """Pivot like the team's Excel: rows = EDS / FBB / MBB with Critical / Major / Minor
    underneath, columns = zones. Counts the same jobs as OSP Job Aging Summary."""
    zones = [name for name, _ in HOME_ZONE_RULES]
    priorities = ["Critical", "Major", "Minor"]
    empty = lambda: {**{z: 0 for z in zones}, "อื่นๆ": 0, "total": 0}
    groups = [{"group": g, "totals": empty(), "rows": [{"priority": p, **empty()} for p in priorities]}
              for g, _ in OSP_AGING_GROUPS]
    grand = empty()
    if job_df is not None and not job_df.empty and "Sub System" in job_df.columns:
        sub = job_df["Sub System"].fillna("").astype(str).str.strip()
        pri = normalize_priority_series(job_df)
        status = normalize_status_series(job_df)
        zone_text = job_df["Zone"].fillna("").astype(str) if "Zone" in job_df.columns else pd.Series("", index=job_df.index)
        group_of = {s: i for i, (_, subs) in enumerate(OSP_AGING_GROUPS) for s in subs}
        for idx in job_df.index:
            gi = group_of.get(sub.loc[idx])
            p = pri.loc[idx]
            if gi is None or p not in ("critical", "major", "minor") or "done(not leave)" in status.loc[idx]:
                continue
            z = next((name for name, token in HOME_ZONE_RULES if token.lower() in zone_text.loc[idx].lower()), "อื่นๆ")
            g = groups[gi]
            row = g["rows"][["critical", "major", "minor"].index(p)]
            for bucket in (row, g["totals"], grand):
                bucket[z] += 1
                bucket["total"] += 1
    for g in groups:
        g["rows"] = [r for r in g["rows"] if r["total"]]
    cols = zones + (["อื่นๆ"] if grand["อื่นๆ"] else [])
    return {"zones": cols, "groups": groups, "grand": grand}

def build_home_summary():
    """Build the summary tables/cards used by Dashboard OSP BKK."""
    job_df = pd.DataFrame(RAW_DATA) if RAW_DATA else pd.DataFrame()

    # Existing subsystem summary is kept for the chart above the aging table.
    priority_names = ["Critical", "Major", "Minor"]
    subsystem_summary = []
    if not job_df.empty and "Sub System" in job_df.columns:
        subsystem_series = job_df["Sub System"].fillna("").astype(str).str.strip()
        priority_series = normalize_priority_series(job_df)
        for subsystem in VALID_SUBSYSTEMS:
            counts = {name: int(((subsystem_series.eq(subsystem)) & (priority_series.eq(name.lower()))).sum()) for name in priority_names}
            counts["total"] = sum(counts.values())
            subsystem_summary.append({"subsystem": subsystem, **{k.lower(): v for k, v in counts.items()}})
    else:
        subsystem_summary = [{"subsystem": name, "critical": 0, "major": 0, "minor": 0, "total": 0} for name in VALID_SUBSYSTEMS]

    osp_aging_summary = build_osp_aging_summary(job_df)
    zone_group_summary = build_zone_group_summary(job_df)
    # Done(Not Leave) must be counted from the original upload because
    # prepare_job_dataframe() intentionally removes those rows.
    done_source_df = pd.DataFrame(ORIGINAL_DATA) if ORIGINAL_DATA else pd.DataFrame()
    done_not_leave_by_group = build_done_not_leave_by_group(done_source_df)
    done_not_leave_total = int(done_not_leave_by_group.get("all", {}).get("total", 0))

    zone_rules = [
        ("SCT", "Bangkok-ST2"),
        ("CWT", "Bangkok-CWT"),
        ("ONT", "Bangkok-ONT"),
        ("TLC", "Bangkok-TLC"),
    ]
    zone_summary = []
    if not job_df.empty and "Zone" in job_df.columns:
        zone_series = job_df["Zone"].fillna("").astype(str)
        for name, token in zone_rules:
            zone_summary.append({"zone": name, "jobs": int(zone_series.str.contains(token, case=False, na=False).sum())})
    else:
        zone_summary = [{"zone": name, "jobs": 0} for name, _ in zone_rules]
    zone_summary.append({"zone": "Total", "jobs": sum(x["jobs"] for x in zone_summary)})

    team_rows = build_dashboard_data(job_df) if not job_df.empty else empty_dashboard_data()
    missing_keywords = ("ลา", "ไม่มีทีม", "รถเสีย")
    working = onsite = departed = free = missing = late = 0
    team_status_rows = []
    now = datetime.now(ZoneInfo("Asia/Bangkok"))

    for row in team_rows:
        remark = clean_text(row.get("remark", ""))
        remark_cf = remark.casefold()
        if any(word in remark_cf for word in missing_keywords):
            status = "ทีมขาด"
            missing += 1
        else:
            available_at = parse_available_on(remark, now)
            if available_at is not None and available_at > now:
                status = "ทีมเลิกดึก"
                late += 1
            elif row.get("work_status") == "On-site":
                status = "On-site"
                onsite += 1
            elif row.get("work_status") == "Departed":
                status = "Departed"
                departed += 1
            elif row.get("work_status") == "Working":
                status = "Working"
                working += 1
            else:
                status = "ว่าง"
                free += 1
        team_status_rows.append({"zone": row.get("zone", ""), "user": row.get("user", ""), "status": status})

    total_teams = len(team_status_rows)
    return {
        "subsystem_summary": subsystem_summary,
        "osp_aging_summary": osp_aging_summary,
        "zone_group_summary": zone_group_summary,
        "done_not_leave_by_group": done_not_leave_by_group,
        "done_not_leave_total": done_not_leave_total,
        "zone_summary": zone_summary,
        "team_summary": {
            "working": working, "onsite": onsite, "departed": departed,
            "free": free, "missing": missing,
            "late": late, "ready": working + onsite + departed + free, "total": total_teams,
        },
    }


@app.route("/", methods=["GET"])
def index():
    latest=DAILY_OSP_HISTORY[-1] if DAILY_OSP_HISTORY else None
    return render_template("home.html",total_jobs=TOTAL_JOBS,total_critical=TOTAL_CRITICAL,total_major=TOTAL_MAJOR,
        total_minor=TOTAL_MINOR,last_update=LAST_UPDATE,latest_osp=latest,**build_home_summary())

@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if request.method=="POST":
        file=request.files.get("file")
        if not file or not file.filename:
            flash("กรุณาเลือกไฟล์ Excel ก่อน Upload","error"); return redirect("/dashboard")
        filename=secure_filename(file.filename)
        if not filename.lower().endswith((".xlsx",".xls")):
            flash("รองรับเฉพาะไฟล์ .xlsx และ .xls","error"); return redirect("/dashboard")
        path=UPLOAD_FOLDER/filename
        file.save(path)
        try:
            update_global_data(pd.read_excel(path))
            flash(f"Upload สำเร็จ: {filename} | Jobs {TOTAL_JOBS}","success")
            # Resource Monitor follows every upload: refresh the current 30-minute slot now
            # instead of waiting for the next :00 / :30 snapshot.
            try: save_resource_snapshot()
            except Exception: app.logger.exception("Resource snapshot after upload failed")
        except Exception as exc:
            flash(f"อ่านไฟล์ไม่สำเร็จ: {exc}","error")
        return redirect("/dashboard")
    if not DATA: load_latest_excel_into_memory()
    return render_template("index.html",data=apply_group_rowspans(DATA) if DATA else apply_group_rowspans(empty_dashboard_data()),
        total_jobs=TOTAL_JOBS,total_critical=TOTAL_CRITICAL,total_major=TOTAL_MAJOR,total_minor=TOTAL_MINOR,last_update=LAST_UPDATE)

@app.route("/job_monitor")
def job_monitor():
    if not RAW_DATA: load_latest_excel_into_memory()
    return render_template("job_monitor.html",jobs=RAW_DATA,total_critical=TOTAL_CRITICAL,total_major=TOTAL_MAJOR,
        total_minor=TOTAL_MINOR,total_jobs=TOTAL_JOBS,total_sct=TOTAL_SCT,total_cwt=TOTAL_CWT,
        total_ont=TOTAL_ONT,total_tlc=TOTAL_TLC,last_update=LAST_UPDATE)

@app.route("/resource_monitor")
def resource_monitor():
    if not RAW_DATA: load_latest_excel_into_memory()
    dates=sorted({r.get("date") for r in RESOURCE_HISTORY if r.get("date")},reverse=True)
    selected=request.args.get("date","")
    if selected not in dates: selected=dates[0] if dates else now_local().strftime("%Y-%m-%d")
    day_records=sorted([r for r in RESOURCE_HISTORY if r.get("date")==selected],key=lambda r:r.get("time",""))
    slots=[f"{h:02d}:{m:02d}" for h in range(24) for m in (0,30)]
    users=dashboard_teams(); matrix={u["user"]:{} for u in users}
    for rec in day_records:
        for row in rec.get("rows",[]):
            if row.get("user") in matrix:
                cell={k:clean_text(row.get(k,"")) for k in ("job_id","status","priority","create_time","due_status","site")}
                cell["other_jobs"]=[o for o in (row.get("others") or []) if isinstance(o,dict)]
                cell["others"]=max(int(row.get("job_count") or 0)-1,len(cell["other_jobs"]),0)
                matrix[row["user"]][rec.get("time","")]=cell
    def cell_at(user, slot):
        c=matrix[user].get(slot,{})
        return {"job_id":"","status":c} if isinstance(c,str) else c
    display_rows=[]
    for u in users:
        cells=[]; pos=0
        while pos<len(slots):
            cur=cell_at(u["user"],slots[pos])
            jid=clean_text(cur.get("job_id","")); st=clean_text(cur.get("status","")); span=1
            if jid:
                # Same job AND same status merge; a status change (Departed -> On-Site) starts a new cell.
                while pos+span<len(slots):
                    nxt=cell_at(u["user"],slots[pos+span])
                    if clean_text(nxt.get("job_id",""))!=jid or clean_text(nxt.get("status",""))!=st: break
                    span+=1
            last=cell_at(u["user"],slots[pos+span-1])   # latest snapshot of the span: Indue may have become Outdue
            cells.append({"job_id":jid,"status":st,"priority":clean_text(cur.get("priority","")),"site":clean_text(cur.get("site","") or last.get("site","")),
                "create_time":clean_text(cur.get("create_time","")),"due_status":clean_text(last.get("due_status","")),
                "others":last.get("others",0) if jid else 0,"other_jobs":last.get("other_jobs",[]) if jid else [],
                "span":span,"time":slots[pos]})
            pos+=span
        display_rows.append({"zone":u["zone"],"user":u["user"],"company":zone_company(u["zone"]),"cells":cells})
    companies=list(dict.fromkeys(r["company"] for r in display_rows))
    zones=[{"zone":z,"company":zone_company(z)} for z in dict.fromkeys(r["zone"] for r in display_rows)]
    return render_template("resource_monitor.html",records=day_records,selected_date=selected,available_dates=dates,
        last_update=LAST_UPDATE,slots=slots,users=users,matrix=matrix,display_rows=display_rows,
        companies=companies,zones=zones,version=(RESOURCE_HISTORY[-1].get("timestamp","") if RESOURCE_HISTORY else ""))

@app.route("/resource_version")
def resource_version():
    # Polled by an open Resource Monitor page; it reloads when this changes.
    last=RESOURCE_HISTORY[-1] if RESOURCE_HISTORY else {}
    return jsonify(date=last.get("date",""),time=last.get("time",""),stamp=last.get("timestamp",""))

# ---------------------------------------------------------------- Job Map

# The network drawings are AIS internal data: opening them needs this password
# (set in the server's compose file, never in this public repo). Unset = open (local dev).
MAP_PASSWORD = os.environ.get("NETWORK_PASSWORD", "")
MAP_FAILS = {}
TEAM_ZONE = {t["user"].casefold(): t["zone"] for t in TEAM_DATA}
AREA_NAMES = {"1": "SCT", "2": "ONT", "3": "TLC", "4": "CWT"}

def map_password_error():
    """None when the X-Map-Key header is right, else a (json, status) response."""
    if not MAP_PASSWORD:
        return None
    ip, now_ts = client_ip(), time.time()
    fails = [t for t in MAP_FAILS.get(ip, []) if now_ts - t < 600]
    if len(fails) >= 5:
        return jsonify(success=False, message="ใส่รหัสผิดหลายครั้ง ลองใหม่ใน 10 นาที"), 429
    if request.headers.get("X-Map-Key", "") != MAP_PASSWORD:
        MAP_FAILS[ip] = fails + [now_ts]
        return jsonify(success=False, message="รหัสไม่ถูกต้อง"), 401
    MAP_FAILS.pop(ip, None)
    return None

def rebuild_site_table():
    try:
        sites, from_kmz, hist = nm.build_site_table()
        app.logger.info("Site table rebuilt: %s sites (%s from KMZ OLT, %s from job history)", sites, from_kmz, hist)
    except Exception:
        app.logger.exception("Site table rebuild failed")

def map_company(team_zone):
    """Company of the team a job is assigned to — the Job Map's first filter row."""
    if not team_zone:
        return "Workforce"     # Workforce BKK Pool: not dispatched to a team yet
    if team_zone in DASHBOARD_EXCLUDED_ZONES:
        return "AIS"
    return zone_company(team_zone)

def map_jobs():
    now = now_local()
    rows = [dict(r, _done=False) for r in RAW_DATA]
    # Done(Not Leave) jobs are dropped from RAW_DATA (Job Monitor hides them); the map lists
    # them under its "Done" status filter, taken from the original upload.
    if ORIGINAL_DATA:
        odf = pd.DataFrame(ORIGINAL_DATA)
        if {"Sub System", "Status", "Priority"} <= set(odf.columns):
            sub = odf["Sub System"].fillna("").astype(str).str.strip()
            st = normalize_status_series(odf)
            pri = normalize_priority_series(odf)
            done = odf[sub.isin(VALID_SUBSYSTEMS) & st.str.contains("done(not leave)", regex=False)
                       & pri.ne("") & pri.ne("none")]
            rows += [dict(r, _done=True) for r in done.to_dict("records")]
    # Positions written in titles teach us where those sites are, for jobs that have none.
    nm.learn_sites([(site_code_from_title(r.get("Job Title", "")), nm.title_coords(r.get("Job Title", "")))
                    for r in rows if nm.title_coords(r.get("Job Title", ""))])
    kmz = nm.kmz_index()
    out = []
    for r in rows:
        title = clean_text(r.get("Job Title", ""))
        site = site_code_from_title(title)
        lat, lon, precision = nm.locate(title, site, r.get("District Name", ""))
        faults = nm.fault_refs(title)
        if site in kmz:
            nm.locate_faults(site, faults)
        if precision != "job":   # a splitter found in the drawing beats the site / district centre
            hit = next((f for f in faults if f["lat"] is not None), None)
            if hit:
                lat, lon, precision = hit["lat"], hit["lon"], "kmz"
        priority = clean_text(r.get("Priority", ""))
        create = clean_text(r.get("Create Time", ""))
        age = None
        try:
            dt = pd.to_datetime(create, errors="coerce")
            if not pd.isna(dt):
                dt = dt.tz_localize(TZ) if getattr(dt, "tzinfo", None) is None else dt.tz_convert(TZ)
                age = round((now - dt.to_pydatetime()).total_seconds() / 3600, 1)
        except Exception:
            pass
        area = re.search(r"AREA\s*(\d)", clean_text(r.get("Zone", "")), re.I)
        assign = clean_text(r.get("Assign to", ""))
        team_zone = TEAM_ZONE.get(assign.casefold(), "")
        out.append({
            "id": clean_text(r.get("Job ID", r.get("JobID", ""))), "priority": priority,
            "status": clean_text(r.get("Status", "")), "due": "" if r["_done"] else resource_due_status(priority, create, now),
            "create": create, "age_h": age, "sub": clean_text(r.get("Sub System", "")),
            "assign": assign, "team_zone": team_zone, "company": map_company(team_zone), "done": r["_done"],
            "area": f"A{area.group(1)}" if area else "", "area_name": AREA_NAMES.get(area.group(1), "") if area else "",
            "district": clean_text(r.get("District Name", "")), "province": clean_text(r.get("Province Name", "")),
            "site": site, "site_name": clean_text(r.get("Site Name", "")), "title": title[:400],
            "lat": lat, "lon": lon, "precision": precision, "kmz": bool(site and site in kmz), "faults": faults,
        })
    return out

@app.route("/map")
def job_map():
    if not RAW_DATA: load_latest_excel_into_memory()
    return render_template("job_map.html", last_update=LAST_UPDATE, map_locked=bool(MAP_PASSWORD))

@app.route("/api/map/jobs")
def api_map_jobs():
    if not RAW_DATA: load_latest_excel_into_memory()
    return jsonify(updated=LAST_UPDATE, jobs=map_jobs())

@app.route("/api/map/unlock", methods=["POST"])
def api_map_unlock():
    err = map_password_error()
    return err if err else jsonify(success=True)

@app.route("/api/map/kmz/<site>")
def api_map_kmz_versions(site):
    err = map_password_error()
    if err: return err
    versions = nm.kmz_versions(site)
    return jsonify(site=site.upper(), versions=[{"i": i, "title": v["title"], "date": v["date"], "size": v["size"]}
                                                for i, v in enumerate(versions)])

@app.route("/api/map/kmz/<site>/<int:i>")
def api_map_kmz(site, i):
    err = map_password_error()
    if err: return err
    versions = nm.kmz_versions(site)
    if not 0 <= i < len(versions):
        return jsonify(success=False, message="ไม่พบไฟล์ KMZ ของไซต์นี้"), 404
    try:
        gj = nm.kmz_geojson(versions[i]["file"])
    except Exception as exc:
        app.logger.exception("KMZ %s", versions[i]["file"])
        return jsonify(success=False, message=f"เปิดไฟล์ไม่สำเร็จ: {exc}"), 500
    return jsonify(site=site.upper(), title=versions[i]["title"], date=versions[i]["date"], **gj)

@app.route("/daily_osp_remain")
def daily_osp_remain():
    if not RAW_DATA: load_latest_excel_into_memory()
    return render_template("daily_osp_remain.html",records=list(reversed(DAILY_OSP_HISTORY)),
        latest=DAILY_OSP_HISTORY[-1] if DAILY_OSP_HISTORY else None,subsystem_names=VALID_SUBSYSTEMS,
        current_jobs=TOTAL_JOBS,last_update=LAST_UPDATE,schedule_times=DAILY_OSP_TIMES,
        schedule_locked=bool(SCHEDULE_PASSWORD))

@app.route("/daily_osp_schedule",methods=["GET","POST"])
def daily_osp_schedule():
    global DAILY_OSP_TIMES
    if request.method == "GET":
        return jsonify(success=True,times=DAILY_OSP_TIMES)
    body = request.get_json(silent=True) or {}
    if SCHEDULE_PASSWORD:
        ip, now_ts = client_ip(), time.time()
        fails = [t for t in SCHEDULE_FAILS.get(ip, []) if now_ts - t < 600]
        if len(fails) >= 5:
            return jsonify(success=False,message="ใส่รหัสผิดหลายครั้ง ลองใหม่ใน 10 นาที"),429
        if str(body.get("password", "")) != SCHEDULE_PASSWORD:
            SCHEDULE_FAILS[ip] = fails + [now_ts]
            return jsonify(success=False,message="รหัสไม่ถูกต้อง"),401
        SCHEDULE_FAILS.pop(ip, None)
    raw = body.get("times")
    if not isinstance(raw, list):
        return jsonify(success=False,message="รูปแบบข้อมูลไม่ถูกต้อง"),400
    bad = [str(t) for t in raw if not TIME_RE.match(str(t).strip())]
    if bad:
        return jsonify(success=False,message="เวลาไม่ถูกต้อง: "+", ".join(bad)+" (ใช้รูปแบบ HH:MM)"),400
    times = normalize_times(raw)
    if len(times) > 24:
        return jsonify(success=False,message="ตั้งได้สูงสุด 24 รอบต่อวัน"),400
    atomic_save_json(DAILY_OSP_SCHEDULE_FILE, {"times": times, "updated_at": now_local().isoformat()})
    DAILY_OSP_TIMES = times
    return jsonify(success=True,times=times,message="บันทึกรอบสรุปแล้ว")

@app.route("/daily_osp_snapshot",methods=["POST"])
def daily_osp_snapshot():
    try:
        record,created=save_daily_osp_snapshot("Manual",True)
        return jsonify(success=True,created=created,message="บันทึก Snapshot สำเร็จ",record=record)
    except Exception as exc:
        return jsonify(success=False,message=str(exc)),400

def excel_response(frame, sheet, prefix):
    output=BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        frame.to_excel(writer,index=False,sheet_name=sheet)
        ws=writer.book[sheet]; ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
        for cells in ws.columns:
            width=max(len(str(c.value or "")) for c in cells)
            ws.column_dimensions[cells[0].column_letter].width=min(max(width+2,10),45)
    output.seek(0)
    filename=now_local().strftime(prefix+"_%Y%m%d_%H%M%S.xlsx")
    return send_file(output,as_attachment=True,download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/export_excel")
def export_excel():
    if not RAW_DATA: return "ยังไม่มีข้อมูล Job สำหรับ Export กรุณา Upload Excel ก่อน",400
    df=pd.DataFrame(RAW_DATA)
    if "Assign to" in df:
        df.insert(0,"Remark",[REMARKS.get(clean_text(u),"") for u in df["Assign to"]])
        df.insert(0,"Contact",[CONTACTS.get(clean_text(u),"") for u in df["Assign to"]])
    return excel_response(df,"Job Monitor","job_monitor")

@app.route("/export_dashboard_excel")
def export_dashboard_excel():
    rows=DATA or empty_dashboard_data()
    df=pd.DataFrame([{"Zone":r["zone"],"User":r["user"],"Contact":r.get("contact",""),"Area":r.get("area",""),
        "Work Status":r.get("work_status",""),"Job Count":r.get("job_count",0),"Status":r.get("status_text",""),"Remark":r.get("remark","")} for r in rows])
    return excel_response(df,"Dashboard","dashboard")

@app.route("/health")
def health():
    return jsonify(ok=True, loaded_jobs=len(RAW_DATA), teams=len(dashboard_teams()), last_update=LAST_UPDATE)

if __name__ == "__main__":
    load_latest_excel_into_memory()
    if not RESOURCE_HISTORY and RAW_DATA:
        try: save_resource_snapshot()
        except Exception: app.logger.exception("Initial resource snapshot failed")
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or os.environ.get("FLASK_DEBUG") != "1":
        threading.Thread(target=background_scheduler,name="dashboard-scheduler",daemon=True).start()
        if nm.KMZ_DIR.is_dir() and not nm.SITE_TABLE_FILE.exists():
            threading.Thread(target=rebuild_site_table, name="site-table", daemon=True).start()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=os.environ.get("FLASK_DEBUG")=="1")

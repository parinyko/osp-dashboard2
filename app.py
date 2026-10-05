from flask import Flask, render_template, request, redirect, jsonify
import pandas as pd
import os
import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATA = []
RAW_DATA = []
LAST_UPDATE = "-"

TOTAL_JOBS = 0
TOTAL_CRITICAL = 0
TOTAL_MAJOR = 0
TOTAL_MINOR = 0

TOTAL_SCT = 0
TOTAL_CWT = 0
TOTAL_ONT = 0
TOTAL_TLC = 0

REMARKS = {}
REMARK_FILE = "remarks.json"

try:
    if os.path.exists(REMARK_FILE):
        with open(REMARK_FILE, "r", encoding="utf-8") as f:
            REMARKS = json.load(f)
    else:
        REMARKS = {}
except Exception:
    REMARKS = {}
VALID_SUBSYSTEMS = [
    "EDS-OSP",
    "ETS-OSP",
    "FTTB-OSP",
    "FTTH-OSP",
    "FTTX-OSP",
    "Splitter-OSP",
    "Transmission-OSP",
    "EDS SW NODE-OSP",
    "EDS IPLC-OSP"
]
ASSIGN_ORDER = [

"Dmplocallatkrabang A",
    "Dmplocallatkrabang B",
    "Dmplocallatkrabang C",
    "Dmplocalpathumthani A",
    "Dmplocalpathumthani B",
    "Dmplocalpathumthani C",
    "Originlocal Center",
    "Originlocalthungkhru A",
    "Originlocalthungkhru B",
    "Originlocalthungkhru C",
    "Originlocalnonthaburi A",
    "Originlocalnonthaburi B",
    "Originlocalnonthaburi C",
    "Exeds A",
    "Exeds B",
    "Exsct A",
    "Exsct B",
    "Exsct C",
    "Extrsct E",
    "Exbpl A",
    "Exbpl B",
    "Exbpl C",
    "Exbpl D",
    "Exbpl E",
    "Extrbpl F",
    "Extrbpl G",
    "Extlc A",
    "Extlc B",
    "Extlc C",
    "Extlc D",
    "Extlc E",
    "Extrtlc F",
    "Excwt A",
    "Excwt B",
    "Excwt C",
    "Excwt D",
    "Excwt E",
    "Extrcwt F",
    "Extrcwt G",
    "Extrcwt H",
    "Exspare A",
    "Kitsada Wiraphan",
    "Poolsak Saenmee",
    "Chawalit Bunrod",
    "Sittikorn Pantanoo",
    "Phongsakron Topradit",
    "Preecha Ruamsungneon",
    "Piriya Sripoon",
    "Cherdchai Wandee",
    "Piyanut Wattanonda",
    "Ruj Chalanun",
    "Parinya Khoonkrong",
    "Songwat Sintanarot",
    "Boonsom Duangjun",
    "Nares Vongkasigum",
    "Workforce BKK Pool"
]
TEAM_DATA = [

    {"zone": "DMP", "user": "Dmplocallatkrabang A"},
    {"zone": "DMP", "user": "Dmplocallatkrabang B"},
    {"zone": "DMP", "user": "Dmplocallatkrabang C"},
    {"zone": "DMP", "user": "Dmplocalpathumthani A"},
    {"zone": "DMP", "user": "Dmplocalpathumthani B"},
    {"zone": "DMP", "user": "Dmplocalpathumthani C"},

    {"zone": "Origin", "user": "Originlocal Center"},
    {"zone": "Origin", "user": "Originlocalthungkhru A"},
    {"zone": "Origin", "user": "Originlocalthungkhru B"},
    {"zone": "Origin", "user": "Originlocalthungkhru C"},
    {"zone": "Origin", "user": "Originlocalnonthaburi A"},
    {"zone": "Origin", "user": "Originlocalnonthaburi B"},
    {"zone": "Origin", "user": "Originlocalnonthaburi C"},

    {"zone": "EDS BKK", "user": "Exeds A"},
    {"zone": "EDS BKK", "user": "Exeds B"},

    {"zone": "SCT", "user": "Exsct A"},
    {"zone": "SCT", "user": "Exsct B"},
    {"zone": "SCT", "user": "Exsct C"},
    {"zone": "SCT", "user": "Extrsct E"},

    {"zone": "BPL", "user": "Exbpl A"},
    {"zone": "BPL", "user": "Exbpl B"},
    {"zone": "BPL", "user": "Exbpl C"},
    {"zone": "BPL", "user": "Exbpl D"},
    {"zone": "BPL", "user": "Exbpl E"},
    {"zone": "BPL", "user": "Extrbpl F"},
    {"zone": "BPL", "user": "Extrbpl G"},

    {"zone": "TLC", "user": "Extlc A"},
    {"zone": "TLC", "user": "Extlc B"},
    {"zone": "TLC", "user": "Extlc C"},
    {"zone": "TLC", "user": "Extlc D"},
    {"zone": "TLC", "user": "Extlc E"},
    {"zone": "TLC", "user": "Extrtlc F"},

    {"zone": "CWT", "user": "Excwt A"},
    {"zone": "CWT", "user": "Excwt B"},
    {"zone": "CWT", "user": "Excwt C"},
    {"zone": "CWT", "user": "Excwt D"},
    {"zone": "CWT", "user": "Excwt E"},
    {"zone": "CWT", "user": "Extrcwt F"},
    {"zone": "CWT", "user": "Extrcwt G"},
    {"zone": "CWT", "user": "Extrcwt H"},

    {"zone": "Team Spare", "user": "Exspare A"},

    {"zone": "BKK2", "user": "Kitsada Wiraphan"},
    {"zone": "BKK2", "user": "Poolsak Saenmee"},
    {"zone": "BKK2", "user": "Chawalit Bunrod"},

    {"zone": "SPK", "user": "Sittikorn Pantanoo"},
    {"zone": "SPK", "user": "Phongsakron Topradit"},
    {"zone": "SPK", "user": "Preecha Ruamsungneon"},

    {"zone": "NTB", "user": "Piriya Sripoon"},
    {"zone": "NTB", "user": "Cherdchai Wandee"},
    {"zone": "NTB", "user": "Piyanut Wattanonda"},

    {"zone": "AIS", "user": "Ruj Chalanun"},
    {"zone": "AIS", "user": "Parinya Khoonkrong"},
    {"zone": "AIS", "user": "Songwat Sintanarot"},
    {"zone": "AIS", "user": "Boonsom Duangjun"},
    {"zone": "AIS", "user": "Nares Vongkasigum"},
]

# Teams shown/managed on the BKK dashboard. These legacy groups are intentionally excluded.
DASHBOARD_EXCLUDED_ZONES = {"BKK2", "SPK", "NTB", "AIS"}

def dashboard_teams():
    return [team for team in TEAM_DATA if team.get("zone") not in DASHBOARD_EXCLUDED_ZONES]


AREA_DATA = {

    "Dmplocallatkrabang A": "หนองจอก มีนบุรี คลองสามวา คันนายาว  บึงกุ่ม",
    "Dmplocallatkrabang B": "สวนหลวง ลาดกระบัง บางกะปิ ",
    "Dmplocallatkrabang C": "สะพานสูง ประเวศ บางนา",

    "Dmplocalpathumthani A": "เมืองปทุมธานี สามโคก ลาดหลุมแก้ว",
    "Dmplocalpathumthani B": "คลองหลวง หนองเสือ",
    "Dmplocalpathumthani C": "ลำลูกกา ธัญบุรี",

    "Originlocal Center": "",
    "Originlocalthungkhru A": "บางขุนเทียน ราษฎร์บูรณะ จอมทอง ",
    "Originlocalthungkhru B": "ทุ่งครุ บางบอน ทวีวัฒนา",
    "Originlocalthungkhru C": "หนองแขม บางแค ภาษีเจริญ",

    "Originlocalnonthaburi A": "บางใหญ่ บางบัวทอง ไทรน้อย เมืองนนทบุรี ปากเกร็ด",
    "Originlocalnonthaburi B": "บางใหญ่ บางบัวทอง ไทรน้อย เมืองนนทบุรี ปากเกร็ด",
    "Originlocalnonthaburi C": "บางใหญ่ บางบัวทอง ไทรน้อย เมืองนนทบุรี ปากเกร็ด",

    "Exsct A": "ลาดพร้าว จตุจักร บางซื่อ วังทองหลาง ห้วยขวาง ดินแดง พญาไท",
    "Exsct B": "ดุสิต ราชเทวี วัฒนา คลองเตย ปทุมวัน ป้อมปราบศัตรูพ่าย พระนคร สัมพันธวงศ์",
    "Exsct C": "บางรัก สาธร ยานนาวา บางคอแหลม คลองเตย",
    "Extrsct E": "Around the zone (Night)",

    "Exbpl A": "สะพานสูง มีนบุรี หนองจอก ลาดกระบัง รามคำแหง",
    "Exbpl B": "บางพลี(ตอนล่าง) บางเสาธง(ตอนล่าง) บางบ่อ(ตอนล่าง)",
    "Exbpl C": "บางพลี(ตอนบน) บางเสาธง(ตอนบน) บางบ่อ(ตอนบน)",
    "Exbpl D": "บางนา พระประแดง เมืองสมุทรปราการ",
    "Exbpl E": "Around the zone (Night)",
    "Extrbpl F": "คลองเตย พระโขนง สวนหลวง ประเวศ",
    "Extrbpl G": "บางกะปิ วังทองหลาง ห้วยขวาง วัฒนา",

    "Extlc A": "บางขุนเทียน พระสมุทรเจดีย์ พระประแดง ทุ่งครุ ราษฎร์บูรณะ จอมทอง บางบอน",
    "Extlc B": "บางพลัด บางกรวย บางใหญ่ เมืองนนทบุรี (Zone TLC)",
    "Extlc C": "ปากเกร็ด บางบัวทอง ไทรน้อย(ตอนล่าง) ไทรน้อย(ตอนบน)",
    "Extlc D": "Around the zone (Night)",
    "Extlc E": "หนองแขม บางแค ภาษีเจริญ ธนบุรี คลองสาน บางกอกใหญ่ บางกอกน้อย ตลิ่งชัน ทวีวัฒนา",
    "Extrtlc F": "Around the zone (Night)",

    "Excwt A": "Around the zone (Night)",
    "Excwt B": "สามโคก(ฝั่งตะวันออก) เมืองปทุมธานี(ฝั่งตะวันออก) ธัญบุรี(คลอง1-7) คลองหลวง(คลอง1-7)",
    "Excwt C": "ลำลูกกา หนองจอก คลองสามวา มีนบุรี รามอินทรา",
    "Excwt D": "ธัญบุรี(คลอง7 เป็นต้นไป) คลองหลวง(คลอง7 เป็นต้นไป) หนองเสือ",
    "Excwt E": "บางซื่อ หลักสี่ เมืองนนทบุรี ปากเกร็ด ดอนเมือง",
    "Extrcwt F": "เมืองปทุม(ฝั่งตะวันตก) สามโคก(ฝั่งตะวันตก) ลาดหลุมแก้ว",
    "Extrcwt G": "Around the zone (Night)",
    "Extrcwt H": "คันนายาว บึงกุ่ม ลาดพร้าว บางเขน สายไหม จตุจักร",

    "Exeds A": "All Zone (เน้น RRU กับงานภายในห้าง ทุกโซน)",
    "Exeds B": "All Zone",

    "Exspare A": "ปากเกร็ด บางบัวทอง ไทรน้อย"
}

def get_status_color(status_text):
    status_text = str(status_text).strip().lower()
    if not status_text:
        return "#ffffff"
    if "on-site" in status_text or "onsite" in status_text:
        return "#c6efce"
    if "departed" in status_text:
        return "#ffe699"
    if "assigned" in status_text or "accepted" in status_text:
        return "#ffc7ce"
    if "held" in status_text:
        return "#9fd5ff"
    return "#ffffff"


# -----------------------------------------------------------------------------
# Persistent team information
# -----------------------------------------------------------------------------
from io import BytesIO
from threading import Lock, RLock, Thread, Event
from werkzeug.utils import secure_filename
from flask import flash, send_file

CONTACTS = {}
CONTACT_FILE = "contacts.json"
REMARK_LOCK = Lock()
CONTACT_LOCK = Lock()
OSP_LOCK = RLock()
DAILY_OSP_FILE = "daily_osp_remain.json"
DAILY_OSP_MAX_RECORDS = 730
DAILY_OSP_STOP = Event()

# Resource Monitor: keep a 30-minute status history for every dashboard user.
RESOURCE_MONITOR_FILE = "resource_monitor_history.json"
RESOURCE_MONITOR_MAX_RECORDS = 20000
RESOURCE_MONITOR_STOP = Event()
RESOURCE_LOCK = Lock()


def load_json_file(path, default=None):
    default = {} if default is None else default
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else default
    except (OSError, json.JSONDecodeError):
        pass
    return default.copy() if isinstance(default, dict) else default


REMARKS = load_json_file(REMARK_FILE, {})
CONTACTS = load_json_file(CONTACT_FILE, {})


def clean_text(value):
    return str(value or "").strip()


def atomic_save_json(path, data, lock):
    temp_path = f"{path}.tmp"
    with lock:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)


def get_request_value(name):
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        return payload.get(name, "")
    return request.form.get(name, "")


@app.route("/save_remark", methods=["POST"])
def save_remark():
    global REMARKS
    user = clean_text(get_request_value("user"))
    remark = clean_text(get_request_value("remark"))
    if not user:
        return jsonify({"success": False, "message": "ไม่พบ User"}), 400

    REMARKS[user] = remark
    atomic_save_json(REMARK_FILE, REMARKS, REMARK_LOCK)
    return jsonify({"success": True, "user": user, "remark": remark})


@app.route("/save_contact", methods=["POST"])
def save_contact():
    global CONTACTS
    user = clean_text(get_request_value("user"))
    contact = clean_text(get_request_value("contact"))
    if not user:
        return jsonify({"success": False, "message": "ไม่พบ User"}), 400

    CONTACTS[user] = contact
    atomic_save_json(CONTACT_FILE, CONTACTS, CONTACT_LOCK)
    return jsonify({"success": True, "user": user, "contact": contact})


def normalize_status_series(df):
    return df["Status"].fillna("").astype(str).str.strip().str.lower()


def normalize_priority_series(df):
    return df["Priority"].fillna("").astype(str).str.strip().str.lower()


def prepare_job_dataframe(df):
    required = ["Sub System", "Status", "Priority", "Assign to"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("ไม่พบคอลัมน์ที่จำเป็น: " + ", ".join(missing))

    subsystem = df["Sub System"].fillna("").astype(str).str.strip()
    status = normalize_status_series(df)
    priority = normalize_priority_series(df)

    filtered = df[subsystem.isin(VALID_SUBSYSTEMS)].copy()
    status_f = normalize_status_series(filtered)
    priority_f = normalize_priority_series(filtered)
    filtered = filtered[~status_f.str.contains("done(not leave)", regex=False)]
    filtered = filtered[priority_f.ne("") & priority_f.ne("none")].copy()

    order_map = {name: idx for idx, name in enumerate(ASSIGN_ORDER)}
    order_map["Workforce BKK Pool"] = 999999
    filtered["_sort_order"] = (
        filtered["Assign to"].fillna("").astype(str).str.strip().map(order_map).fillna(9999)
    )
    filtered = filtered.sort_values(by=["_sort_order", "Assign to"], kind="stable")
    return filtered.drop(columns=["_sort_order"])


def calculate_totals(job_df):
    priority = normalize_priority_series(job_df)
    zone = job_df["Zone"].fillna("").astype(str) if "Zone" in job_df.columns else pd.Series("", index=job_df.index)
    return {
        "critical": int((priority == "critical").sum()),
        "major": int((priority == "major").sum()),
        "minor": int((priority == "minor").sum()),
        "jobs": int(len(job_df)),
        "sct": int(zone.str.contains("Bangkok-ST2", case=False, na=False).sum()),
        "cwt": int(zone.str.contains("Bangkok-CWT", case=False, na=False).sum()),
        "ont": int(zone.str.contains("Bangkok-ONT", case=False, na=False).sum()),
        "tlc": int(zone.str.contains("Bangkok-TLC", case=False, na=False).sum()),
    }


def build_dashboard_data(df):
    result = []
    status_series = normalize_status_series(df)
    priority_series = normalize_priority_series(df)

    for team in dashboard_teams():
        zone = team["zone"]
        user = team["user"]
        assign_series = df["Assign to"].fillna("").astype(str).str.strip().str.casefold()
        mask = assign_series.eq(user.strip().casefold())
        mask &= ~status_series.str.contains("done(not leave)", regex=False)
        mask &= priority_series.ne("") & priority_series.ne("none")
        mask &= df["Sub System"].fillna("").astype(str).str.strip().isin(VALID_SUBSYSTEMS)
        user_jobs = df.loc[mask]

        statuses = []
        if "Status" in user_jobs.columns:
            statuses = [clean_text(v) for v in user_jobs["Status"].tolist() if clean_text(v)]
        status_text = ", ".join(sorted(set(statuses), key=str.casefold))

        status_cf = status_text.casefold()
        if not user_jobs.empty:
            if "on-site" in status_cf or "onsite" in status_cf:
                work_status = "On-site"
            elif "departed" in status_cf:
                work_status = "Departed"
            else:
                work_status = "Working"
        else:
            work_status = "ว่าง"

        result.append({
            "zone": zone,
            "user": user,
            "area": AREA_DATA.get(user, ""),
            "work_status": work_status,
            "job_count": int(len(user_jobs)),
            "status_text": status_text,
            "status_color": get_status_color(status_text),
            "contact": CONTACTS.get(user, ""),
            "remark": REMARKS.get(user, ""),
        })
    return result


def apply_group_rowspans(rows):
    zone_counts = Counter(row["zone"] for row in rows)
    shown = set()
    for row in rows:
        if row["zone"] not in shown:
            row["show_zone"] = True
            row["rowspan"] = zone_counts[row["zone"]]
            shown.add(row["zone"])
        else:
            row["show_zone"] = False
            row["rowspan"] = 0
    return rows


def update_global_data(df):
    global DATA, RAW_DATA, ORIGINAL_DATA, LAST_UPDATE
    global TOTAL_CRITICAL, TOTAL_MAJOR, TOTAL_MINOR, TOTAL_JOBS
    global TOTAL_SCT, TOTAL_CWT, TOTAL_ONT, TOTAL_TLC

    # Keep a clean copy of the original upload before normal filtering.
    ORIGINAL_DATA = df.fillna("").to_dict("records") if df is not None else []
    job_df = prepare_job_dataframe(df)
    RAW_DATA = job_df.fillna("").to_dict("records")
    totals = calculate_totals(job_df)
    TOTAL_CRITICAL = totals["critical"]
    TOTAL_MAJOR = totals["major"]
    TOTAL_MINOR = totals["minor"]
    TOTAL_JOBS = totals["jobs"]
    TOTAL_SCT = totals["sct"]
    TOTAL_CWT = totals["cwt"]
    TOTAL_ONT = totals["ont"]
    TOTAL_TLC = totals["tlc"]

    DATA = build_dashboard_data(df)
    LAST_UPDATE = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%d/%m/%Y %H:%M:%S")


def empty_dashboard_data():
    rows = []
    for team in dashboard_teams():
        rows.append({
            "zone": team["zone"],
            "user": team["user"],
            "area": AREA_DATA.get(team["user"], ""),
            "work_status": "ว่าง",
            "job_count": 0,
            "status_text": "",
            "status_color": "#ffffff",
            "contact": CONTACTS.get(team["user"], ""),
            "remark": REMARKS.get(team["user"], ""),
        })
    return apply_group_rowspans(rows)


# -----------------------------------------------------------------------------
# Daily Job OSP Remain
# -----------------------------------------------------------------------------
DAILY_OSP_SUBSYSTEMS = [
    "EDS-OSP",
    "ETS-OSP",
    "FTTB-OSP",
    "FTTH-OSP",
    "FTTX-OSP",
    "Splitter-OSP",
    "Transmission-OSP",
    "EDS SW NODE-OSP",
    "EDS IPLC-OSP",
]


def load_daily_osp_history():
    try:
        if not os.path.exists(DAILY_OSP_FILE):
            return []
        with open(DAILY_OSP_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            records = payload.get("records", [])
        else:
            records = payload
        return records if isinstance(records, list) else []
    except (OSError, json.JSONDecodeError):
        return []


DAILY_OSP_HISTORY = load_daily_osp_history()


def save_daily_osp_history():
    payload = {
        "version": 1,
        "updated_at": datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
        "records": DAILY_OSP_HISTORY[-DAILY_OSP_MAX_RECORDS:],
    }
    temp_path = f"{DAILY_OSP_FILE}.tmp"
    with OSP_LOCK:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, DAILY_OSP_FILE)


def get_latest_upload_path():
    candidates = []
    try:
        for name in os.listdir(UPLOAD_FOLDER):
            if name.lower().endswith((".xlsx", ".xls")):
                path = os.path.join(UPLOAD_FOLDER, name)
                if os.path.isfile(path):
                    candidates.append(path)
    except OSError:
        return None
    return max(candidates, key=os.path.getmtime) if candidates else None


def load_latest_excel_into_memory():
    path = get_latest_upload_path()
    if not path:
        return False
    try:
        df = pd.read_excel(path)
        update_global_data(df)
        return True
    except Exception:
        return False


def build_daily_osp_snapshot(slot="Manual"):
    """Create one OSP remain snapshot from the currently loaded job data."""
    if not RAW_DATA:
        load_latest_excel_into_memory()
    if not RAW_DATA:
        raise ValueError("ยังไม่มีข้อมูล Job สำหรับสร้าง Daily Job OSP Remain")

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    job_df = pd.DataFrame(RAW_DATA)
    subsystem_series = job_df["Sub System"].fillna("").astype(str).str.strip()
    priority_series = normalize_priority_series(job_df)

    rows = []
    for subsystem in DAILY_OSP_SUBSYSTEMS:
        mask = subsystem_series.eq(subsystem)
        rows.append({
            "subsystem": subsystem,
            "critical": int((mask & priority_series.eq("critical")).sum()),
            "major": int((mask & priority_series.eq("major")).sum()),
            "minor": int((mask & priority_series.eq("minor")).sum()),
            "total": int(mask.sum()),
        })

    total_critical = sum(r["critical"] for r in rows)
    total_major = sum(r["major"] for r in rows)
    total_minor = sum(r["minor"] for r in rows)
    grand_total = sum(r["total"] for r in rows)

    return {
        "timestamp": now.strftime("%d/%m/%Y %H:%M:%S"),
        "iso_timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "slot": slot,
        "last_update": LAST_UPDATE,
        "totals": {
            "critical": total_critical,
            "major": total_major,
            "minor": total_minor,
            "grand_total": grand_total,
        },
        "subsystems": rows,
    }


def snapshot_key(record):
    return f"{record.get('date','')}|{record.get('slot','')}"


def save_daily_osp_snapshot(slot="Manual", allow_duplicate=False):
    global DAILY_OSP_HISTORY
    record = build_daily_osp_snapshot(slot)
    key = snapshot_key(record)

    with OSP_LOCK:
        if not allow_duplicate and slot in ("06:00", "18:00"):
            for old in DAILY_OSP_HISTORY:
                if snapshot_key(old) == key:
                    return old, False
        DAILY_OSP_HISTORY.append(record)
        DAILY_OSP_HISTORY = DAILY_OSP_HISTORY[-DAILY_OSP_MAX_RECORDS:]
        save_daily_osp_history()
    return record, True


def scheduled_osp_slot(now):
    if now.hour == 6 and now.minute == 0:
        return "06:00"
    if now.hour == 18 and now.minute == 0:
        return "18:00"
    return None


def load_resource_history():
    try:
        if not os.path.exists(RESOURCE_MONITOR_FILE):
            return []
        with open(RESOURCE_MONITOR_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            records = payload.get("records", [])
        else:
            records = payload
        return records if isinstance(records, list) else []
    except (OSError, json.JSONDecodeError):
        return []


RESOURCE_HISTORY = load_resource_history()

# Keep the original uploaded rows so Done(Not Leave) can be summarized
# even though normal dashboard filtering removes those jobs.
ORIGINAL_DATA = []


def save_resource_history():
    payload = {
        "version": 1,
        "updated_at": datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
        "records": RESOURCE_HISTORY[-RESOURCE_MONITOR_MAX_RECORDS:],
    }
    temp_path = f"{RESOURCE_MONITOR_FILE}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, RESOURCE_MONITOR_FILE)


def _find_job_id_column(df):
    """Find the Job ID column without assuming one exact Excel header spelling."""
    if df is None or df.empty:
        return None
    candidates = {
        "job id", "jobid", "job_id", "job no", "job number",
        "job number id", "jobcode", "job code", "job"
    }
    for col in df.columns:
        key = re.sub(r"[^a-z0-9]+", " ", str(col).strip().casefold()).strip()
        if key in candidates:
            return col
    return None


def resource_job_for_user(df, user):
    """Return the selected Job ID and its Current Status for one user."""
    if df is None or df.empty:
        return {"job_id": "", "status": ""}

    assign = df["Assign to"].fillna("").astype(str).str.strip().str.casefold()
    mask = assign.eq(clean_text(user).casefold())
    if "Priority" in df.columns:
        priority = df["Priority"].fillna("").astype(str).str.strip().str.lower()
        mask &= priority.ne("") & priority.ne("none")
    if "Sub System" in df.columns:
        mask &= df["Sub System"].fillna("").astype(str).str.strip().isin(VALID_SUBSYSTEMS)
    if "Status" in df.columns:
        st = df["Status"].fillna("").astype(str).str.strip().str.lower()
        mask &= ~st.str.contains("done(not leave)", regex=False)

    user_jobs = df.loc[mask].copy()
    if user_jobs.empty:
        return {"job_id": "", "status": ""}

    status_col = "Current Status" if "Current Status" in user_jobs.columns else "Status"
    job_col = _find_job_id_column(user_jobs)

    rank = {"on-site": 5, "onsite": 5, "departed": 4, "accepted": 3, "assigned": 2, "held": 1}
    def score(v):
        key = clean_text(v).casefold()
        for k, n in rank.items():
            if k in key:
                return n
        return 0

    best = None
    best_score = -1
    for idx, row in user_jobs.iterrows():
        status = clean_text(row.get(status_col, ""))
        sc = score(status)
        if sc > best_score:
            best = row
            best_score = sc
        elif best is None:
            best = row

    if best is None:
        return {"job_id": "", "status": ""}

    job_id = clean_text(best.get(job_col, "")) if job_col else ""
    status = clean_text(best.get(status_col, ""))
    return {"job_id": job_id, "status": status}


def resource_status_for_user(df, user):
    """Backward-compatible status-only helper."""
    return resource_job_for_user(df, user)["status"]

def build_resource_snapshot(now=None):
    now = now or datetime.now(ZoneInfo("Asia/Bangkok"))
    # Snapshots are aligned to 00/30 minutes.
    minute = 30 if now.minute >= 30 else 0
    stamp = now.replace(minute=minute, second=0, microsecond=0)
    df = pd.DataFrame(RAW_DATA) if RAW_DATA else pd.DataFrame()
    rows = []
    for team in dashboard_teams():
        item = resource_job_for_user(df, team["user"])
        rows.append({
            "zone": team["zone"],
            "user": team["user"],
            "status": item["status"],
            "job_id": item["job_id"],
        })
    return {
        "timestamp": stamp.isoformat(),
        "date": stamp.strftime("%Y-%m-%d"),
        "time": stamp.strftime("%H:%M"),
        "rows": rows,
    }


def save_resource_snapshot(now=None, allow_duplicate=False):
    global RESOURCE_HISTORY
    record = build_resource_snapshot(now)
    key = record["timestamp"]
    with RESOURCE_LOCK:
        if not allow_duplicate and any(r.get("timestamp") == key for r in RESOURCE_HISTORY):
            return next(r for r in RESOURCE_HISTORY if r.get("timestamp") == key), False
        RESOURCE_HISTORY.append(record)
        RESOURCE_HISTORY = RESOURCE_HISTORY[-RESOURCE_MONITOR_MAX_RECORDS:]
        save_resource_history()
    return record, True


def resource_monitor_scheduler():
    last_key = None
    while not RESOURCE_MONITOR_STOP.wait(15):
        now = datetime.now(ZoneInfo("Asia/Bangkok"))
        if now.minute not in (0, 30):
            continue
        key = now.strftime("%Y-%m-%d %H:%M")
        if key == last_key:
            continue
        last_key = key
        try:
            save_resource_snapshot(now)
        except Exception as exc:
            print(f"[Resource Monitor] snapshot failed: {exc}")


def daily_osp_scheduler():
    last_checked_minute = None
    while not DAILY_OSP_STOP.wait(15):
        now = datetime.now(ZoneInfo("Asia/Bangkok"))
        minute_key = now.strftime("%Y-%m-%d %H:%M")
        if minute_key == last_checked_minute:
            continue
        last_checked_minute = minute_key
        slot = scheduled_osp_slot(now)
        if not slot:
            continue
        try:
            save_daily_osp_snapshot(slot)
        except Exception as exc:
            print(f"[Daily OSP] snapshot failed: {exc}")


@app.route("/resource_monitor")
def resource_monitor():
    if not RAW_DATA:
        load_latest_excel_into_memory()
    dates = sorted({r.get("date") for r in RESOURCE_HISTORY if r.get("date")}, reverse=True)
    selected = request.args.get("date", "")
    if selected not in dates:
        selected = dates[0] if dates else datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d")
    day_records = [r for r in RESOURCE_HISTORY if r.get("date") == selected]
    day_records.sort(key=lambda r: r.get("time", ""))
    slots = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
    users = dashboard_teams()
    matrix = {u["user"]: {} for u in users}
    for rec in day_records:
        for row in rec.get("rows", []):
            if row.get("user") in matrix:
                # New snapshots store both Job ID and Current Status.
                # Old history records remain readable as status-only cells.
                matrix[row["user"]][rec.get("time", "")] = {
                    "job_id": clean_text(row.get("job_id", "")),
                    "status": clean_text(row.get("status", "")),
                }

    # Build horizontally merged display cells: consecutive slots with the
    # same Job ID become one cell. This keeps the template simple and makes
    # the visual timeline match the requested layout.
    display_rows = []
    for u in users:
        cells = []
        pos = 0
        while pos < len(slots):
            cur = matrix.get(u["user"], {}).get(slots[pos], {})
            if isinstance(cur, str):
                cur = {"job_id": "", "status": cur}
            jid = clean_text(cur.get("job_id", ""))
            span = 1
            if jid:
                while pos + span < len(slots):
                    nxt = matrix.get(u["user"], {}).get(slots[pos + span], {})
                    if isinstance(nxt, str):
                        nxt = {"job_id": "", "status": nxt}
                    if clean_text(nxt.get("job_id", "")) != jid:
                        break
                    span += 1
            cells.append({"job_id": jid, "status": clean_text(cur.get("status", "")), "span": span})
            pos += span
        display_rows.append({"zone": u["zone"], "user": u["user"], "cells": cells})

    return render_template("resource_monitor.html", records=day_records, selected_date=selected, available_dates=dates, last_update=LAST_UPDATE, slots=slots, users=users, matrix=matrix, display_rows=display_rows)


@app.route("/daily_osp_remain")
def daily_osp_remain():
    if not RAW_DATA:
        load_latest_excel_into_memory()

    records = list(reversed(DAILY_OSP_HISTORY))
    latest = records[0] if records else None
    return render_template(
        "daily_osp_remain.html",
        records=records,
        latest=latest,
        subsystem_names=DAILY_OSP_SUBSYSTEMS,
        current_jobs=TOTAL_JOBS,
        last_update=LAST_UPDATE,
    )


@app.route("/daily_osp_snapshot", methods=["POST"])
def daily_osp_snapshot():
    try:
        record, created = save_daily_osp_snapshot("Manual", allow_duplicate=True)
        return jsonify({
            "success": True,
            "created": created,
            "message": "บันทึก Snapshot สำเร็จ",
            "record": record,
        })
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.route("/export_excel")
def export_excel():
    if not RAW_DATA:
        return "ยังไม่มีข้อมูล Job สำหรับ Export กรุณา Upload Excel ก่อน", 400

    df = pd.DataFrame(RAW_DATA)
    df.insert(0, "Remark", [REMARKS.get(clean_text(u), "") for u in df.get("Assign to", "")])
    df.insert(0, "Contact", [CONTACTS.get(clean_text(u), "") for u in df.get("Assign to", "")])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Job Monitor")
        ws = writer.book["Job Monitor"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for column_cells in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in column_cells)
            ws.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 10), 45)

    output.seek(0)
    filename = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("job_monitor_%Y%m%d_%H%M%S.xlsx")
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/export_dashboard_excel")
def export_dashboard_excel():
    rows = DATA if DATA else empty_dashboard_data()
    df = pd.DataFrame([
        {
            "Zone": r["zone"],
            "User": r["user"],
            "Contact": r.get("contact", ""),
            "Area": r.get("area", ""),
            "Work Status": r.get("work_status", ""),
            "Job Count": r.get("job_count", 0),
            "Status": r.get("status_text", ""),
            "Remark": r.get("remark", ""),
        }
        for r in rows
    ])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dashboard")
        ws = writer.book["Dashboard"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for column_cells in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in column_cells)
            ws.column_dimensions[column_cells[0].column_letter].width = min(max(max_len + 2, 10), 45)

    output.seek(0)
    filename = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("dashboard_%Y%m%d_%H%M%S.xlsx")
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")



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
    ("EDS", ["EDS-OSP", "ETS-OSP", "EDS SW NODE-OSP", "EDS IPLC-OSP"]),
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
    latest_osp = DAILY_OSP_HISTORY[-1] if DAILY_OSP_HISTORY else None
    summary = build_home_summary()
    return render_template(
        "home.html",
        total_jobs=TOTAL_JOBS,
        total_critical=TOTAL_CRITICAL,
        total_major=TOTAL_MAJOR,
        total_minor=TOTAL_MINOR,
        last_update=LAST_UPDATE,
        latest_osp=latest_osp,
        **summary,
    )


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("กรุณาเลือกไฟล์ Excel ก่อน Upload", "error")
            return redirect("/dashboard")

        filename = secure_filename(file.filename)
        if not filename.lower().endswith((".xlsx", ".xls")):
            flash("รองรับเฉพาะไฟล์ .xlsx และ .xls", "error")
            return redirect("/dashboard")

        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            update_global_data(df)
            flash(f"Upload สำเร็จ: {filename} | Jobs {TOTAL_JOBS}", "success")
        except Exception as exc:
            flash(f"อ่านไฟล์ไม่สำเร็จ: {exc}", "error")
        return redirect("/dashboard")

    display_data = apply_group_rowspans(list(DATA)) if DATA else empty_dashboard_data()
    return render_template(
        "index.html",
        data=display_data,
        total_jobs=TOTAL_JOBS,
        total_critical=TOTAL_CRITICAL,
        total_major=TOTAL_MAJOR,
        total_minor=TOTAL_MINOR,
        last_update=LAST_UPDATE,
    )


@app.route("/job_monitor")
def job_monitor():
    return render_template(
        "job_monitor.html",
        jobs=RAW_DATA,
        total_critical=TOTAL_CRITICAL,
        total_major=TOTAL_MAJOR,
        total_minor=TOTAL_MINOR,
        total_jobs=TOTAL_JOBS,
        total_sct=TOTAL_SCT,
        total_cwt=TOTAL_CWT,
        total_ont=TOTAL_ONT,
        total_tlc=TOTAL_TLC,
        last_update=LAST_UPDATE,
    )


if __name__ == "__main__":
    load_latest_excel_into_memory()
    try:
        save_resource_snapshot()
    except Exception as exc:
        print(f"[Resource Monitor] initial snapshot failed: {exc}")
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or os.environ.get("FLASK_DEBUG") != "1":
        Thread(target=daily_osp_scheduler, name="daily-osp-scheduler", daemon=True).start()
        Thread(target=resource_monitor_scheduler, name="resource-monitor-scheduler", daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

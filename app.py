# -*- coding: utf-8 -*-
"""Job Dashboard / Resource Monitor - rebuilt clean Flask application."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from flask import Flask, render_template, request, redirect, jsonify, flash, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
TZ = ZoneInfo("Asia/Bangkok")

REMARK_FILE = BASE_DIR / "remarks.json"
CONTACT_FILE = BASE_DIR / "contacts.json"
DAILY_OSP_FILE = BASE_DIR / "daily_osp_remain.json"
RESOURCE_FILE = BASE_DIR / "resource_monitor_history.json"
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
        return data if isinstance(data, type(default)) else default
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
DAILY_OSP_HISTORY = load_json_file(DAILY_OSP_FILE, [])
RESOURCE_HISTORY = load_json_file(RESOURCE_FILE, [])
DATA, RAW_DATA = [], []
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
        r["zone_rowspan"] = counts[r["zone"]] if r["zone"] not in seen else 0
        seen.add(r["zone"])
    return out

def update_global_data(df):
    global DATA, RAW_DATA, LAST_UPDATE, TOTAL_JOBS, TOTAL_CRITICAL, TOTAL_MAJOR, TOTAL_MINOR
    global TOTAL_SCT, TOTAL_CWT, TOTAL_ONT, TOTAL_TLC
    prepared = prepare_job_dataframe(df)
    totals = calculate_totals(prepared)
    with DATA_LOCK:
        RAW_DATA = df.where(pd.notna(df), None).to_dict(orient="records")
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
    DAILY_OSP_HISTORY = load_json_file(DAILY_OSP_FILE, [])
    return DAILY_OSP_HISTORY

def save_daily_osp_snapshot(slot="Manual", allow_duplicate=False):
    global DAILY_OSP_HISTORY
    if not RAW_DATA: load_latest_excel_into_memory()
    if not RAW_DATA: raise ValueError("ยังไม่มีข้อมูล กรุณา Upload Excel ก่อน")
    df = pd.DataFrame(RAW_DATA)
    prepared = prepare_job_dataframe(df)
    counts = prepared["Sub System"].value_counts().to_dict()
    record = {"date":now_local().strftime("%Y-%m-%d"),"time":now_local().strftime("%H:%M"),
              "slot":slot,"total":len(prepared),"counts":{s:int(counts.get(s,0)) for s in VALID_SUBSYSTEMS}}
    if not allow_duplicate and any(r.get("date")==record["date"] and r.get("time")==record["time"] and r.get("slot")==slot for r in DAILY_OSP_HISTORY):
        return DAILY_OSP_HISTORY[-1], False
    DAILY_OSP_HISTORY.append(record)
    DAILY_OSP_HISTORY = DAILY_OSP_HISTORY[-DAILY_OSP_MAX_RECORDS:]
    atomic_save_json(DAILY_OSP_FILE, DAILY_OSP_HISTORY)
    return record, True

def load_resource_history():
    global RESOURCE_HISTORY
    RESOURCE_HISTORY = load_json_file(RESOURCE_FILE, [])
    return RESOURCE_HISTORY

def save_resource_snapshot():
    global RESOURCE_HISTORY
    stamp = now_local()
    rows = []
    df = pd.DataFrame(RAW_DATA) if RAW_DATA else pd.DataFrame()
    for t in dashboard_teams():
        user=t["user"]
        jobs = df[df["Assign to"].fillna("").astype(str).str.strip().str.casefold()==user.casefold()] if "Assign to" in df else df.iloc[0:0]
        status = ", ".join(dict.fromkeys(clean_text(x) for x in jobs.get("Status",[]) if clean_text(x)))
        first = jobs.iloc[0].to_dict() if not jobs.empty else {}
        rows.append({"zone":t["zone"],"user":user,"status":status,"job_id":clean_text(first.get("Job ID",first.get("JobID",""))),
                     "priority":clean_text(first.get("Priority","")),"create_time":clean_text(first.get("Create Time","")),
                     "due_status":resource_due_status(first.get("Priority",""),first.get("Create Time",""),stamp)})
    rec={"date":stamp.strftime("%Y-%m-%d"),"time":stamp.strftime("%H:%M"),"timestamp":stamp.isoformat(),"rows":rows}
    RESOURCE_HISTORY.append(rec)
    RESOURCE_HISTORY=RESOURCE_HISTORY[-RESOURCE_MONITOR_MAX_RECORDS:]
    atomic_save_json(RESOURCE_FILE,RESOURCE_HISTORY)
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
    while True:
        try:
            now=now_local()
            if now.minute in (0,30):
                save_resource_snapshot()
            if now.minute==0 and now.hour in (8,12,16,20):
                save_daily_osp_snapshot(f"{now.hour:02d}:00")
        except Exception:
            app.logger.exception("Scheduled snapshot failed")
        threading.Event().wait(60)

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

@app.route("/", methods=["GET"])
def index():
    latest=DAILY_OSP_HISTORY[-1] if DAILY_OSP_HISTORY else None
    return render_template("home.html",total_jobs=TOTAL_JOBS,total_critical=TOTAL_CRITICAL,total_major=TOTAL_MAJOR,
        total_minor=TOTAL_MINOR,last_update=LAST_UPDATE,latest_osp=latest)

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
                matrix[row["user"]][rec.get("time","")]={k:clean_text(row.get(k,"")) for k in ("job_id","status","priority","create_time","due_status")}
    display_rows=[]
    for u in users:
        cells=[]; pos=0
        while pos<len(slots):
            cur=matrix[u["user"]].get(slots[pos],{})
            if isinstance(cur,str): cur={"job_id":"","status":cur}
            jid=clean_text(cur.get("job_id","")); span=1
            if jid:
                while pos+span<len(slots):
                    nxt=matrix[u["user"]].get(slots[pos+span],{})
                    if isinstance(nxt,str): nxt={"job_id":"","status":nxt}
                    if clean_text(nxt.get("job_id",""))!=jid: break
                    span+=1
            cells.append({"job_id":jid,"status":clean_text(cur.get("status","")),"priority":clean_text(cur.get("priority","")),
                "create_time":clean_text(cur.get("create_time","")),"due_status":clean_text(cur.get("due_status","")),"span":span})
            pos+=span
        display_rows.append({"zone":u["zone"],"user":u["user"],"cells":cells})
    return render_template("resource_monitor.html",records=day_records,selected_date=selected,available_dates=dates,
        last_update=LAST_UPDATE,slots=slots,users=users,matrix=matrix,display_rows=display_rows)

@app.route("/daily_osp_remain")
def daily_osp_remain():
    if not RAW_DATA: load_latest_excel_into_memory()
    return render_template("daily_osp_remain.html",records=list(reversed(DAILY_OSP_HISTORY)),
        latest=DAILY_OSP_HISTORY[-1] if DAILY_OSP_HISTORY else None,subsystem_names=VALID_SUBSYSTEMS,
        current_jobs=TOTAL_JOBS,last_update=LAST_UPDATE)

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
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=os.environ.get("FLASK_DEBUG")=="1")

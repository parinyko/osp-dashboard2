from flask import Flask, render_template, request, redirect, jsonify
import pandas as pd
import os
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

    {"zone": "WF", "user": "Workforce BKK Pool"},
]

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
from threading import Lock
from werkzeug.utils import secure_filename
from flask import flash, send_file

CONTACTS = {}
CONTACT_FILE = "contacts.json"
REMARK_LOCK = Lock()
CONTACT_LOCK = Lock()


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

    for team in TEAM_DATA:
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

        result.append({
            "zone": zone,
            "user": user,
            "area": AREA_DATA.get(user, ""),
            "work_status": "Working" if len(user_jobs) else "ว่าง",
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
    global DATA, RAW_DATA, LAST_UPDATE
    global TOTAL_CRITICAL, TOTAL_MAJOR, TOTAL_MINOR, TOTAL_JOBS
    global TOTAL_SCT, TOTAL_CWT, TOTAL_ONT, TOTAL_TLC

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
    for team in TEAM_DATA:
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


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("กรุณาเลือกไฟล์ Excel ก่อน Upload", "error")
            return redirect("/")

        filename = secure_filename(file.filename)
        if not filename.lower().endswith((".xlsx", ".xls")):
            flash("รองรับเฉพาะไฟล์ .xlsx และ .xls", "error")
            return redirect("/")

        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            df = pd.read_excel(filepath)
            update_global_data(df)
            flash(f"Upload สำเร็จ: {filename} | Jobs {TOTAL_JOBS}", "success")
        except Exception as exc:
            flash(f"อ่านไฟล์ไม่สำเร็จ: {exc}", "error")
        return redirect("/")

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

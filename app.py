from flask import Flask, render_template, request, redirect, jsonify
import pandas as pd
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

app = Flask(__name__)

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

    if status_text == "":
        return "#ffffff"

    # 1. Onsite
    elif "on-site" in status_text or "onsite" in status_text:
        return "#c6efce"

    # 2. Departed
    elif "departed" in status_text:
        return "#ffe699"

    # 3. Assigned / Accepted
    elif "assigned" in status_text or "accepted" in status_text:
        return "#ffc7ce"

    # 4. Held
    elif "held" in status_text:
        return "#9fd5ff"

    return "#ffffff"


@app.route("/save_remark", methods=["POST"])
def save_remark():

    global REMARKS

    user = request.form.get("user", "")
    remark = request.form.get("remark", "")

    print("SAVE:", user, "=>", remark)

    REMARKS[user] = remark

    with open(REMARK_FILE, "w", encoding="utf-8") as f:
        json.dump(
            REMARKS,
            f,
            ensure_ascii=False,
            indent=4
        )

    return jsonify({"success": True})

@app.route("/", methods=["GET", "POST"])
def index():
    global DATA
    global RAW_DATA
    global LAST_UPDATE
    global TOTAL_CRITICAL
    global TOTAL_MAJOR
    global TOTAL_MINOR
    global TOTAL_JOBS
    global TOTAL_SCT
    global TOTAL_CWT
    global TOTAL_ONT
    global TOTAL_TLC


    if request.method == "POST":

        file = request.files.get("file")

        if file and file.filename:

            filepath = os.path.join(
                UPLOAD_FOLDER,
                file.filename
            )

            file.save(filepath)

            df = pd.read_excel(filepath)

            job_monitor_df = df[
                df["Sub System"]
                .fillna("")
                .astype(str)
                .str.strip()
                .isin(VALID_SUBSYSTEMS)
            ]

            job_monitor_df = job_monitor_df[
                ~job_monitor_df["Status"]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains(
                    "done(not leave)",
                    regex=False
                )
            ]

            job_monitor_df = job_monitor_df[
                job_monitor_df["Priority"]
                .fillna("")
                .astype(str)
                .str.strip()
                .ne("")
            ]

            job_monitor_df = job_monitor_df[
                job_monitor_df["Priority"]
                .astype(str)
                .str.strip()
                .str.lower()
                .ne("none")
            ]
            order_map = {
                name: idx
                for idx, name in enumerate(ASSIGN_ORDER)
            }

            order_map["Workforce BKK Pool"] = 999999

            job_monitor_df["_sort_order"] = (
                job_monitor_df["Assign to"]
                .fillna("")
                .astype(str)
                .map(order_map)
                .fillna(9999)
            )

            job_monitor_df = job_monitor_df.sort_values(
                by=["_sort_order", "Assign to"]
            )

            RAW_DATA = (
                job_monitor_df
                .drop(columns=["_sort_order"])
                .fillna("")
                .to_dict("records")
            )

            if "Sub System" in df.columns:

                total_df = df[
                    df["Sub System"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .isin(VALID_SUBSYSTEMS)
                ]

                total_df = total_df[
                    ~total_df["Status"]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        "done(not leave)",
                        regex=False
                    )
                ]

                # ไม่นับ Priority ว่าง
                total_df = total_df[
                    total_df["Priority"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .ne("")
                ]

                # ไม่นับ Priority = None
                total_df = total_df[
                    total_df["Priority"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .ne("none")
                ]
                TOTAL_CRITICAL = len(
                    total_df[
                        total_df["Priority"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        == "critical"
                        ]
                )

                TOTAL_MAJOR = len(
                    total_df[
                        total_df["Priority"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        == "major"
                        ]
                )

                TOTAL_MINOR = len(
                    total_df[
                        total_df["Priority"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        == "minor"
                        ]
                )
                TOTAL_JOBS = len(total_df)
                TOTAL_SCT = len(
                    total_df[
                        total_df["Zone"]
                        .fillna("")
                        .astype(str)
                        .str.contains("Bangkok-ST2", na=False)
                    ]
                )

                TOTAL_CWT = len(
                    total_df[
                        total_df["Zone"]
                        .fillna("")
                        .astype(str)
                        .str.contains("Bangkok-CWT", na=False)
                    ]
                )

                TOTAL_ONT = len(
                    total_df[
                        total_df["Zone"]
                        .fillna("")
                        .astype(str)
                        .str.contains("Bangkok-ONT", na=False)
                    ]
                )

                TOTAL_TLC = len(
                    total_df[
                        total_df["Zone"]
                        .fillna("")
                        .astype(str)
                        .str.contains("Bangkok-TLC", na=False)
                    ]
                )

            else:

                TOTAL_JOBS = len(df)

                TOTAL_CRITICAL = 0

                TOTAL_MAJOR = 0

                TOTAL_MINOR = 0

            result = []

            if "Assign to" not in df.columns:
                return "ไม่พบคอลัมน์ Assign to"

            for team in TEAM_DATA:

                zone = team["zone"]
                user = team["user"]

                user_jobs = df[
                    (
                            df["Assign to"]
                            .fillna("")
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            ==
                            user.strip().lower()
                    )
                    &
                    (
                        ~df["Status"]
                        .fillna("")
                        .astype(str)
                        .str.lower()
                        .str.contains(
                            "done(not leave)",
                            regex=False
                        )
                    )
                    &
                    (
                        df["Priority"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .ne("")
                    )
                    &
                    (
                        df["Priority"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        .ne("none")
                    )
                    ]

                job_count = len(user_jobs)

                if job_count > 0:
                    work_status = "Working"
                else:
                    work_status = "ว่าง"

                status_list = []

                if "Status" in df.columns:

                    for _, row in user_jobs.iterrows():

                        st = str(
                            row.get("Status", "")
                        ).strip()

                        if (
                            st and
                            st.lower() != "done(not leave)"
                        ):
                            status_list.append(st)

                status_text = ", ".join(
                    sorted(set(status_list))
                )

                result.append({
                    "zone": zone,
                    "user": user,
                    "area": AREA_DATA.get(user, ""),
                    "work_status": work_status,
                    "job_count": job_count,
                    "status_text": status_text,
                    "status_color": get_status_color(
                        status_text
                    ),
                    "remark": REMARKS.get(
                        user,
                        ""
                    )
                })

            DATA = result

            LAST_UPDATE = datetime.now(
                ZoneInfo("Asia/Bangkok")
            ).strftime("%d/%m/%Y %H:%M:%S")

        return redirect("/")

    zone_counts = Counter(
        [row["zone"] for row in DATA]
    )

    shown_zone = set()

    for row in DATA:

        if row["zone"] not in shown_zone:

            row["show_zone"] = True
            row["rowspan"] = zone_counts[
                row["zone"]
            ]

            shown_zone.add(
                row["zone"]
            )

        else:

            row["show_zone"] = False
            row["rowspan"] = 0

    display_data = DATA

    if len(display_data) == 0:

        display_data = []

        zone_counts = Counter(
            [x["zone"] for x in TEAM_DATA]
        )

        shown = set()

        for team in TEAM_DATA:

            zone = team["zone"]

            if zone not in shown:

                show_zone = True
                rowspan = zone_counts[zone]
                shown.add(zone)

            else:

                show_zone = False
                rowspan = 0

            display_data.append({
                "zone": zone,
                "user": team["user"],
                "work_status": "ว่าง",
                "job_count": 0,
                "status_text": "",
                "status_color": "#ffffff",
                "remark": REMARKS.get(
                    team["user"],
                    ""
                ),
                "show_zone": show_zone,
                "rowspan": rowspan
            })

    return render_template(
        "index.html",
        data=display_data,
        total_jobs=TOTAL_JOBS,
        total_critical=TOTAL_CRITICAL,
        total_major=TOTAL_MAJOR,
        total_minor=TOTAL_MINOR,
        last_update=LAST_UPDATE
    )
@app.route("/job_monitor")
def job_monitor():

    print("ROWS =", len(RAW_DATA))

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
        last_update=LAST_UPDATE
    )
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
     
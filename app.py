# RESOURCE STATUS UPDATE
# =======================
# Drop-in code for app.py
#
# Purpose:
# 1) Resource Status order:
#       On-Site
#       Departed
#       Assigned / Accepted (same color)
#       Held
# 2) Display:
#       JOB12345 (Status) — Indue
#       JOB12346 (Status) — Outdue
# 3) Indue / Outdue is ALWAYS calculated from Create Time.
#
# IMPORTANT:
# Replace the existing resource_job_for_user(), build_resource_snapshot(),
# and the display_rows section inside /resource_monitor with the code below.
# Also replace the resource_monitor.html cell display as shown at the end.

# ---------------------------------------------------------------------------
# ADD / REPLACE near resource monitor helpers
# ---------------------------------------------------------------------------

RESOURCE_STATUS_ORDER = {
    "on-site": 1,
    "onsite": 1,
    "departed": 2,
    "assigned": 3,
    "accepted": 3,
    "held": 4,
}


def resource_status_order(status):
    text = clean_text(status).casefold()
    for key, order in RESOURCE_STATUS_ORDER.items():
        if key in text:
            return order
    return 99


def resource_due_status(priority, create_time, now=None):
    """
    Calculate Indue / Outdue strictly from Create Time.

    Critical:
        elapsed < 3 hours  -> Indue
        elapsed >= 3 hours -> Outdue

    Major:
        elapsed < 10 hours  -> Indue
        elapsed >= 10 hours -> Outdue

    Other priorities return blank.
    """
    priority = clean_text(priority).casefold()
    if priority not in ("critical", "major"):
        return ""

    create_dt = _parse_aging_datetime(create_time)
    if create_dt is None:
        return ""

    now = now or datetime.now(ZoneInfo("Asia/Bangkok"))
    elapsed_hours = (now - create_dt).total_seconds() / 3600

    if priority == "critical":
        return "Indue" if elapsed_hours < 3 else "Outdue"

    return "Indue" if elapsed_hours < 10 else "Outdue"


def resource_job_for_user(df, user):
    """
    Return the selected Job ID, Current Status, Priority, Create Time,
    and Due Status for one user.

    Due Status is calculated from Create Time only.
    """
    empty = {
        "job_id": "",
        "status": "",
        "priority": "",
        "create_time": "",
        "due_status": "",
    }

    if df is None or df.empty:
        return empty

    assign = df["Assign to"].fillna("").astype(str).str.strip().str.casefold()
    mask = assign.eq(clean_text(user).casefold())

    if "Priority" in df.columns:
        priority_series = (
            df["Priority"].fillna("").astype(str).str.strip().str.lower()
        )
        mask &= priority_series.ne("") & priority_series.ne("none")
    else:
        priority_series = pd.Series("", index=df.index)

    if "Sub System" in df.columns:
        mask &= (
            df["Sub System"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(VALID_SUBSYSTEMS)
        )

    if "Status" in df.columns:
        st = df["Status"].fillna("").astype(str).str.strip().str.lower()
        mask &= ~st.str.contains("done(not leave)", regex=False)

    user_jobs = df.loc[mask].copy()

    if user_jobs.empty:
        return empty

    status_col = "Current Status" if "Current Status" in user_jobs.columns else "Status"
    job_col = _find_job_id_column(user_jobs)

    # Resource Status priority:
    # On-Site -> Departed -> Assigned/Accepted -> Held
    def score(v):
        return resource_status_order(v)

    # Lower number = higher display priority.
    best = None
    best_score = 999

    for _, row in user_jobs.iterrows():
        status = clean_text(row.get(status_col, ""))
        sc = score(status)

        if best is None or sc < best_score:
            best = row
            best_score = sc

    if best is None:
        return empty

    job_id = clean_text(best.get(job_col, "")) if job_col else ""
    status = clean_text(best.get(status_col, ""))
    priority = clean_text(best.get("Priority", ""))

    create_time = ""
    create_col = _find_column(best.to_frame().T, CREATE_TIME_COLUMN_CANDIDATES)
    if create_col:
        raw_create = best.get(create_col, "")
        if raw_create is not None and not pd.isna(raw_create):
            create_time = clean_text(raw_create)

    due_status = resource_due_status(
        priority=priority,
        create_time=create_time,
    )

    return {
        "job_id": job_id,
        "status": status,
        "priority": priority,
        "create_time": create_time,
        "due_status": due_status,
    }


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
            "priority": item["priority"],
            "create_time": item["create_time"],
            "due_status": item["due_status"],
        })

    return {
        "timestamp": stamp.isoformat(),
        "date": stamp.strftime("%Y-%m-%d"),
        "time": stamp.strftime("%H:%M"),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# REPLACE the matrix/display_rows part inside /resource_monitor
# ---------------------------------------------------------------------------
#
# Keep the beginning of your existing route through:
#
#   matrix = {u["user"]: {} for u in users}
#
# Then use this block:

matrix = {u["user"]: {} for u in users}

for rec in day_records:
    for row in rec.get("rows", []):
        if row.get("user") in matrix:
            matrix[row["user"]][rec.get("time", "")] = {
                "job_id": clean_text(row.get("job_id", "")),
                "status": clean_text(row.get("status", "")),
                "priority": clean_text(row.get("priority", "")),
                "create_time": clean_text(row.get("create_time", "")),
                "due_status": clean_text(row.get("due_status", "")),
            }


display_rows = []

for u in users:
    cells = []
    pos = 0

    while pos < len(slots):
        cur = matrix.get(u["user"], {}).get(slots[pos], {})

        if isinstance(cur, str):
            cur = {
                "job_id": "",
                "status": cur,
                "priority": "",
                "create_time": "",
                "due_status": "",
            }

        jid = clean_text(cur.get("job_id", ""))
        span = 1

        # Merge consecutive slots only when Job ID is the same.
        if jid:
            while pos + span < len(slots):
                nxt = matrix.get(u["user"], {}).get(
                    slots[pos + span],
                    {}
                )

                if isinstance(nxt, str):
                    nxt = {
                        "job_id": "",
                        "status": nxt,
                        "priority": "",
                        "create_time": "",
                        "due_status": "",
                    }

                if clean_text(nxt.get("job_id", "")) != jid:
                    break

                span += 1

        cells.append({
            "job_id": jid,
            "status": clean_text(cur.get("status", "")),
            "priority": clean_text(cur.get("priority", "")),
            "create_time": clean_text(cur.get("create_time", "")),
            "due_status": clean_text(cur.get("due_status", "")),
            "span": span,
        })

        pos += span

    display_rows.append({
        "zone": u["zone"],
        "user": u["user"],
        "cells": cells,
    })


# ---------------------------------------------------------------------------
# resource_monitor.html
# ---------------------------------------------------------------------------
#
# Replace the existing Job ID/status cell content with:
#
# <div class="resource-job">
#     {% if cell.job_id %}
#         <div class="resource-job-line">
#             <strong>{{ cell.job_id }}</strong>
#             <span class="resource-status {{ cell.status|lower|replace(' ', '-') }}">
#                 ({{ cell.status }})
#             </span>
#
#             {% if cell.due_status %}
#                 <span class="resource-due {{ cell.due_status|lower }}">
#                     — {{ cell.due_status }}
#                 </span>
#             {% endif %}
#         </div>
#     {% endif %}
# </div>
#
# CSS:
#
# .resource-job-line {
#     white-space: nowrap;
#     font-size: 13px;
#     font-weight: 600;
# }
#
# .resource-status {
#     margin-left: 3px;
# }
#
# .resource-status.on-site,
# .resource-status.onsite {
#     background: #c6efce;
#     color: #1f5c2b;
#     padding: 2px 6px;
#     border-radius: 5px;
# }
#
# .resource-status.departed {
#     background: #ffe699;
#     color: #6b5200;
#     padding: 2px 6px;
#     border-radius: 5px;
# }
#
# /* Assigned + Accepted = SAME COLOR */
# .resource-status.assigned,
# .resource-status.accepted {
#     background: #ffc7ce;
#     color: #8b1e2d;
#     padding: 2px 6px;
#     border-radius: 5px;
# }
#
# .resource-status.held {
#     background: #9fd5ff;
#     color: #124c70;
#     padding: 2px 6px;
#     border-radius: 5px;
# }
#
# .resource-due {
#     font-weight: 800;
#     margin-left: 4px;
# }
#
# .resource-due.indue {
#     color: #218739;
# }
#
# .resource-due.outdue {
#     color: #d62828;
# }
#
# IMPORTANT:
# Historical snapshots created before this update do not contain
# priority/create_time/due_status. They remain readable, but their old
# cells cannot be retroactively calculated unless a fresh snapshot is made.

import React, { useMemo, useState } from "react";
import { api, invalidate } from "../data.js";
import { useCompany } from "../company.jsx";
import { addMonths, endOfMonth, parseISODate, toISODate } from "../utils.js";

// Monthly job targets for the company on screen. The report scales them to the
// selected date range (a quarter = 3× the monthly target). Blank = no target line.

const toNum = (s) => {
  const v = String(s ?? "").trim();
  if (!v) return null;
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? n : NaN;
};
const toStr = (v) => (v == null ? "" : String(v));

// What each zone / team actually did per month, shown next to every field as a
// starting point. Uses the last 3 complete months — the current month is partial.
function actualMonthly(records, co) {
  if (!records?.length || !co.dateMax) return null;
  const max = parseISODate(co.dateMax);
  const lastFull = toISODate(endOfMonth(max)) === co.dateMax ? max : addMonths(max, -1);
  const end = toISODate(endOfMonth(lastFull));
  const start = toISODate(addMonths(lastFull, -2)) < co.dateMin ? co.dateMin : toISODate(addMonths(lastFull, -2));
  if (start > end) return null;
  const months = new Set();
  const zones = {};
  const teams = {};
  for (const r of records) {
    if (r.d < start || r.d > end) continue;
    months.add(r.d.slice(0, 7));
    zones[r.z] = (zones[r.z] || 0) + 1;
    teams[r.t] = (teams[r.t] || 0) + 1;
  }
  const n = months.size;
  if (!n) return null;
  const per = (obj) => Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, Math.round(v / n)]));
  const z = per(zones);
  const t = per(teams);
  const avg = (keys, m) => {
    const vals = keys.map((k) => m[k] || 0);
    return vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : null;
  };
  return {
    label: `${start.slice(0, 7)} → ${end.slice(0, 7)}`,
    zones: z,
    teams: t,
    zoneAvg: avg(co.zones, z),
    teamAvg: avg(co.allTeams, t),
  };
}

export default function SettingsPanel({ open, onClose, records }) {
  const co = useCompany();
  const t = co.targets || {};
  const actual = useMemo(() => actualMonthly(records, co), [records, co]);
  const hint = (v) => (actual ? `จริง ~${(v || 0).toLocaleString()}/เดือน` : null);
  const [zoneDefault, setZoneDefault] = useState(toStr(t.zone_default));
  const [teamDefault, setTeamDefault] = useState(toStr(t.team_default));
  const [zones, setZones] = useState(() => Object.fromEntries(co.zones.map((z) => [z, toStr(t.zones?.[z])])));
  const [teams, setTeams] = useState(() => Object.fromEntries(co.allTeams.map((x) => [x, toStr(t.teams?.[x])])));
  const [showTeams, setShowTeams] = useState(Object.keys(t.teams || {}).length > 0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  if (!open) return null;

  // Fill only the empty fields with what was actually done, so typed values stay.
  const fillActual = () => {
    if (!actual) return;
    const keep = (cur, v) => (String(cur ?? "").trim() ? cur : toStr(v));
    setZoneDefault((c) => keep(c, actual.zoneAvg));
    setTeamDefault((c) => keep(c, actual.teamAvg));
    setZones((s) => Object.fromEntries(Object.entries(s).map(([k, v]) => [k, keep(v, actual.zones[k] || 0)])));
    setTeams((s) => Object.fromEntries(Object.entries(s).map(([k, v]) => [k, keep(v, actual.teams[k] || 0)])));
    setShowTeams(true);
  };

  const save = async () => {
    const body = {
      zone_default: toNum(zoneDefault),
      team_default: toNum(teamDefault),
      zones: Object.fromEntries(Object.entries(zones).map(([k, v]) => [k, toNum(v)])),
      teams: Object.fromEntries(Object.entries(teams).map(([k, v]) => [k, toNum(v)])),
    };
    const bad = [body.zone_default, body.team_default, ...Object.values(body.zones), ...Object.values(body.teams)].some(Number.isNaN);
    if (bad) {
      setErr("ใส่ได้เฉพาะตัวเลข 0 ขึ้นไป หรือเว้นว่าง");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await api(`/api/settings/${encodeURIComponent(co.slug)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      invalidate("settings");
      onClose();
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div onClick={onClose} style={overlay}>
      <div onClick={(e) => e.stopPropagation()} style={box}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 18, fontWeight: 800 }}>⚙️ ตั้งค่าเป้าหมาย — {co.name}</div>
          <button onClick={onClose} style={closeBtn}>✕</button>
        </div>
        <div style={{ fontSize: 12, color: "#888", margin: "4px 0 16px" }}>
          จำนวนงาน <b>ต่อเดือน</b> · ระบบปรับตามช่วงวันที่ที่เลือกให้เอง · เว้นว่าง = ไม่แสดงเส้นเป้า
        </div>
        {actual && (
          <div style={actualBar}>
            <span>
              ตัวเลข "จริง" ใต้แต่ละช่อง = งานที่ทำได้จริงเฉลี่ยต่อเดือน ช่วง <b>{actual.label}</b>
            </span>
            <button onClick={fillActual} style={fillBtn}>เติมช่องว่างด้วยค่าจริง</button>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <Field label="เป้าต่อโซน (ค่าเริ่มต้น)" value={zoneDefault} onChange={setZoneDefault} hint={actual && `เฉลี่ยทุกโซน ${hint(actual.zoneAvg)}`} />
          <Field label="เป้าต่อทีม (ค่าเริ่มต้น)" value={teamDefault} onChange={setTeamDefault} hint={actual && `เฉลี่ยทุกทีม ${hint(actual.teamAvg)}`} />
        </div>

        <div style={sectionTitle}>เป้าแยกรายโซน (ถ้าไม่เท่าค่าเริ่มต้น)</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10 }}>
          {co.zones.map((z) => (
            <Field key={z} label={z} value={zones[z]} placeholder={zoneDefault || "—"} hint={actual && hint(actual.zones[z])} onChange={(v) => setZones((s) => ({ ...s, [z]: v }))} />
          ))}
        </div>

        <div style={{ ...sectionTitle, display: "flex", alignItems: "center", gap: 10 }}>
          เป้าแยกรายทีม
          <button onClick={() => setShowTeams((v) => !v)} style={linkBtn}>
            {showTeams ? "ซ่อน ▲" : `แสดง ${co.allTeams.length} ทีม ▼`}
          </button>
        </div>
        {showTeams &&
          co.zones.map((z) => (
            <div key={z} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#555", margin: "6px 0" }}>{z}</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 8 }}>
                {co.teamsByZone[z].map((x) => (
                  <Field key={x} label={x} value={teams[x]} placeholder={teamDefault || "—"} hint={actual && hint(actual.teams[x])} onChange={(v) => setTeams((s) => ({ ...s, [x]: v }))} small />
                ))}
              </div>
            </div>
          ))}

        {err && <div style={{ marginTop: 12, color: "#c0392b", fontSize: 12 }}>⚠️ {err}</div>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 18 }}>
          <button onClick={onClose} style={ghost}>ยกเลิก</button>
          <button onClick={save} disabled={busy} style={primary(busy)}>{busy ? "กำลังบันทึก…" : "บันทึก"}</button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, small, hint }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ fontSize: small ? 10 : 11, color: "#666", marginBottom: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={label}>
        {label}
      </div>
      <input
        inputMode="numeric"
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%",
          padding: small ? "5px 8px" : "8px 10px",
          border: "1px solid #d4d4dc",
          borderRadius: 6,
          fontSize: 13,
          boxSizing: "border-box",
        }}
      />
      {hint && <div style={{ fontSize: small ? 9 : 10, color: "#2C7A4D", marginTop: 2 }}>{hint}</div>}
    </label>
  );
}

const overlay = {
  position: "fixed",
  inset: 0,
  background: "rgba(15,12,35,0.55)",
  backdropFilter: "blur(4px)",
  zIndex: 1500,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 24,
};
const box = {
  background: "#fff",
  borderRadius: 14,
  padding: "22px 26px",
  width: "min(820px, 100%)",
  maxHeight: "88vh",
  overflowY: "auto",
  boxShadow: "0 16px 60px rgba(0,0,0,0.30)",
};
const actualBar = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  flexWrap: "wrap",
  gap: 8,
  background: "#f1f8ea",
  color: "#3d5a1a",
  borderRadius: 8,
  padding: "8px 12px",
  fontSize: 12,
  marginBottom: 14,
};
const fillBtn = { background: "#fff", border: "1px solid #2C7A4D88", color: "#2C7A4D", borderRadius: 6, padding: "5px 10px", fontSize: 12, fontWeight: 700, cursor: "pointer" };
const sectionTitle = { fontSize: 13, fontWeight: 700, color: "#1f1f2c", margin: "18px 0 8px" };
const closeBtn = { background: "transparent", border: "none", fontSize: 18, color: "#888", cursor: "pointer" };
const linkBtn = { background: "none", border: "none", color: "#3498DB", cursor: "pointer", fontSize: 12, fontWeight: 700 };
const ghost = { background: "#fff", border: "1px solid #d4d4dc", borderRadius: 8, padding: "9px 16px", cursor: "pointer", fontSize: 13 };
const primary = (busy) => ({
  background: busy ? "#bbb" : "linear-gradient(135deg, #4d6a1f, #6fb720)",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  padding: "9px 18px",
  fontWeight: 700,
  fontSize: 13,
  cursor: busy ? "not-allowed" : "pointer",
});

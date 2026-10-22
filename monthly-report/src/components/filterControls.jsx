import React from "react";
import { MONTHS_TH } from "../theme.js";

// Shared building blocks for filter bars (used by FilterBar and AllCompanyFilterBar).

const pad = (n) => String(n).padStart(2, "0");
export const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

function monthPreset(year, monthIdx) {
  const start = new Date(year, monthIdx, 1);
  const end = new Date(year, monthIdx + 1, 0);
  return {
    label: `${MONTHS_TH[monthIdx]} ${String(year + 543).slice(-2)}`,
    start: iso(start),
    end: iso(end),
  };
}

export function buildPresets(dateMin, dateMax) {
  if (!dateMax) return [];
  const [y, m] = dateMax.slice(0, 7).split("-").map(Number);
  const latest = new Date(y, m - 1, 1);
  // 4 most recent months: this month + 3 prior
  const months = [];
  for (let i = 0; i < 4; i++) {
    const d = new Date(latest.getFullYear(), latest.getMonth() - i, 1);
    months.push(monthPreset(d.getFullYear(), d.getMonth()));
  }
  // Quarter of the latest month
  const qStartMonth = Math.floor(latest.getMonth() / 3) * 3;
  const qStart = new Date(latest.getFullYear(), qStartMonth, 1);
  const qEnd = new Date(latest.getFullYear(), qStartMonth + 3, 0);
  const qLabel = `Q${Math.floor(qStartMonth / 3) + 1} ${String(latest.getFullYear() + 543).slice(-2)}`;
  // Last 6 months ending at latest
  const sixStart = new Date(latest.getFullYear(), latest.getMonth() - 5, 1);
  const sixEnd = new Date(latest.getFullYear(), latest.getMonth() + 1, 0);
  return [
    ...months,
    { label: qLabel, start: iso(qStart), end: iso(qEnd) },
    { label: "6 เดือนล่าสุด", start: iso(sixStart), end: iso(sixEnd) },
    { label: "ทั้งหมด", start: dateMin, end: dateMax },
  ];
}

export function Chip({ active, color, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 12px",
        borderRadius: 16,
        border: active ? "none" : "1px solid #d4d4dc",
        background: active
          ? color || "linear-gradient(135deg, #A8D75A, #6fb720)"
          : "#ffffff",
        color: active ? "#1f3a05" : "#555",
        fontWeight: active ? 700 : 500,
        fontSize: 12,
        cursor: "pointer",
        transition: "all 0.15s",
        boxShadow: active ? "0 2px 6px rgba(0,0,0,0.08)" : "none",
      }}
    >
      {children}
    </button>
  );
}

export function toggle(arr, x) {
  return arr.includes(x) ? arr.filter((y) => y !== x) : [...arr, x];
}

// Like toggle(), but refuses to leave nothing selected. An empty zone/team/priority
// selection filtered every record out (blank report) while a reload restored "all",
// so the same state looked different before and after a refresh.
// `within` limits the check to the chips on screen (teams of the selected zones).
export function toggleKeepOne(arr, x, within = null) {
  const next = toggle(arr, x);
  const shown = within ? next.filter((y) => within.includes(y)) : next;
  return shown.length ? next : arr;
}

export const labelStyle = {
  fontSize: 11,
  color: "#8b8b96",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: 6,
};

export const inputStyle = {
  background: "#ffffff",
  border: "1px solid #d4d4dc",
  borderRadius: 6,
  padding: "6px 10px",
  color: "#1f1f2c",
  fontSize: 13,
};

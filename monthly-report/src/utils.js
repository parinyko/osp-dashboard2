import { useEffect, useState } from "react";
import { MONTHS_EN, MONTHS_TH } from "./theme.js";

export function formatSeconds(s) {
  if (s == null || isNaN(s)) return "—";
  const sign = s < 0 ? "-" : "";
  const abs = Math.abs(Math.round(s));
  const h = Math.floor(abs / 3600);
  const m = Math.floor((abs % 3600) / 60);
  const sec = abs % 60;
  return `${sign}${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export function parseISODate(s) {
  if (!s) return null;
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function toISODate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function inRange(dStr, start, end) {
  return dStr >= start && dStr <= end;
}

// Shift an ISO date by n days in local time. Never go through toISOString():
// it converts to UTC, which lands on the previous day in UTC+ zones (Bangkok).
export function addDaysISO(iso, n) {
  const d = parseISODate(iso);
  d.setDate(d.getDate() + n);
  return toISODate(d);
}

// Calendar days in [start, end], inclusive.
export function rangeDays(startStr, endStr) {
  const s = parseISODate(startStr);
  const e = parseISODate(endStr);
  return Math.max(1, Math.round((e - s) / 86400000) + 1);
}

// Every ISO date in [start, end], inclusive.
export function datesInRange(startStr, endStr) {
  const out = [];
  if (!startStr || !endStr || endStr < startStr) return out;
  for (let d = startStr; d <= endStr; d = addDaysISO(d, 1)) out.push(d);
  return out;
}

// How many months [start, end] covers, counting a partial month by its share of
// days: Mar 1–31 = 1, Jul 1–Sep 30 = 3, Sep 1–15 = 0.5.
export function monthsInRange(startStr, endStr) {
  const s = parseISODate(startStr);
  const e = parseISODate(endStr);
  if (!s || !e || e < s) return 0;
  let total = 0;
  for (let m = startOfMonth(s); m <= e; m = addMonths(m, 1)) {
    const last = endOfMonth(m);
    const from = s > m ? s : m;
    const to = e < last ? e : last;
    total += (Math.round((to - from) / 86400000) + 1) / last.getDate();
  }
  return total;
}

// A per-month target scaled to the selected range, so a quarter is measured
// against 3× the monthly target instead of 1×.
export function targetForRange(monthlyTarget, startStr, endStr) {
  return monthlyTarget * monthsInRange(startStr, endStr);
}

// The six month keys ("YYYY-MM") ending at the month of `endStr`, oldest first.
// Pages 5, 8, 9 and 10 always show this window, whatever the date filter says.
export function lastSixMonths(endStr) {
  const [y, m] = endStr.slice(0, 7).split("-").map(Number);
  const out = [];
  for (let i = 5; i >= 0; i--) {
    const d = new Date(y, m - 1 - i, 1);
    out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  return out;
}

// The calendar month before the month of `endStr`, as [start, end] ISO dates —
// the "Last Month" column on the KPI, ranking and duration pages.
export function prevMonthRange(endStr) {
  const e = parseISODate(endStr) || new Date();
  const prevEnd = new Date(e.getFullYear(), e.getMonth(), 0);
  return [toISODate(startOfMonth(prevEnd)), toISODate(prevEnd)];
}

// Past this many days, per-day charts drop in-bar labels and thin the x-axis.
export const DENSE_DAYS = 45;

// One row per calendar day in [start, end], including days with no jobs so the
// axis is continuous. Rows are keyed by full date: grouping by day-of-month alone
// stacked 5 Jul, 5 Aug and 5 Sep into a single "5" bar on multi-month ranges.
// `label` is the day number within one month, "DD/MM" across months.
export function dailyRows(records, startStr, endStr, init, add) {
  const sameMonth = startStr.slice(0, 7) === endStr.slice(0, 7);
  const rows = new Map();
  for (const d of datesInRange(startStr, endStr)) {
    const label = sameMonth ? String(dayOfMonth(d)) : `${d.slice(8, 10)}/${d.slice(5, 7)}`;
    rows.set(d, { d, label, ...init() });
  }
  for (const r of records) {
    const row = rows.get(r.d);
    if (row) add(row, r);
  }
  return Array.from(rows.values());
}

export function monthLabelEN(year, monthIndex) {
  return `${MONTHS_EN[monthIndex]} ${year}`;
}

export function monthLabelTH(year, monthIndex) {
  return `${MONTHS_TH[monthIndex]} ${String(year + 543).slice(-2)}`;
}

export function startOfMonth(d) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

export function endOfMonth(d) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

export function addMonths(d, n) {
  return new Date(d.getFullYear(), d.getMonth() + n, 1);
}

export function monthKey(dStr) {
  // returns "YYYY-MM"
  return dStr.slice(0, 7);
}

export function monthKeyToLabel(mk) {
  const [y, m] = mk.split("-").map(Number);
  return MONTHS_EN[m - 1];
}

export function monthKeyToYearLabel(mk) {
  const [y, m] = mk.split("-").map(Number);
  return `${MONTHS_EN[m - 1]} ${y}`;
}

export function pct(num, den) {
  if (!den) return 0;
  return (num / den) * 100;
}

export function fmtPct(v, digits = 2) {
  if (v == null || isNaN(v)) return "—";
  return `${v.toFixed(digits)}%`;
}

export function uniq(arr) {
  return Array.from(new Set(arr));
}

export function groupBy(arr, fn) {
  const out = new Map();
  for (const x of arr) {
    const k = fn(x);
    if (!out.has(k)) out.set(k, []);
    out.get(k).push(x);
  }
  return out;
}

export function sum(arr) {
  let s = 0;
  for (const x of arr) s += x || 0;
  return s;
}

export function mean(arr) {
  const vals = arr.filter((v) => v != null && !isNaN(v));
  if (!vals.length) return null;
  return sum(vals) / vals.length;
}

export function dayOfMonth(dStr) {
  return parseInt(dStr.slice(8, 10), 10);
}

// useState-like hook that mirrors its value to localStorage so it survives reloads.
export function usePersistedState(key, defaultValue) {
  const [value, setValue] = useState(() => {
    if (typeof window === "undefined") return defaultValue;
    try {
      const raw = localStorage.getItem(key);
      if (raw == null) return defaultValue;
      return JSON.parse(raw);
    } catch {
      return defaultValue;
    }
  });
  useEffect(() => {
    try {
      if (value == null) localStorage.removeItem(key);
      else localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* quota or disabled */
    }
  }, [key, value]);
  return [value, setValue];
}

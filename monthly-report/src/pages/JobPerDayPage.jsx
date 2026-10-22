import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  LabelList,
  Cell,
} from "recharts";
import PageHeader from "../components/PageHeader.jsx";
import ChartCard from "../components/ChartCard.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { useCompany } from "../company.jsx";
import { COLORS, PRIORITY_ORDER } from "../theme.js";
import { rangeDays, dailyRows, targetForRange, DENSE_DAYS } from "../utils.js";

// Render a reference-line label with a solid white background pill so the
// text stays readable even when bars are tall.
function renderBoxedLabel({ viewBox }, text, color, side) {
  if (!viewBox) return null;
  const x = viewBox.x + 6;
  const offset = side === "top" ? -10 : 14;
  const y = viewBox.y + offset;
  const w = text.length * 6.5 + 14;
  return (
    <g>
      <rect
        x={x - 4}
        y={y - 11}
        width={w}
        height={18}
        rx={4}
        fill="#ffffff"
        stroke={color}
        strokeWidth={1}
        opacity={0.96}
      />
      <text x={x + 3} y={y + 2} fill={color} fontSize={11} fontWeight={700}>
        {text}
      </text>
    </g>
  );
}

function buildDailyPriority(records, start, end) {
  const out = dailyRows(
    records,
    start,
    end,
    () => Object.fromEntries(PRIORITY_ORDER.map((p) => [p, 0])),
    (row, r) => {
      if (r.p) row[r.p] = (row[r.p] || 0) + 1;
    }
  );
  for (const r of out) {
    r._total = PRIORITY_ORDER.reduce((s, p) => s + (r[p] || 0), 0);
  }
  return out;
}

function buildDailyOverdue(records, start, end) {
  const out = dailyRows(
    records,
    start,
    end,
    () => ({ "In Due": 0, "Out Due": 0 }),
    (row, r) => {
      if (r.bw) row[r.bw] = (row[r.bw] || 0) + 1;
    }
  );
  for (const r of out) r._total = (r["In Due"] || 0) + (r["Out Due"] || 0);
  return out;
}

function DailyPriorityChart({ data, target, avg }) {
  const dense = data.length > DENSE_DAYS;
  return (
    <ChartCard title="Job Done Per day">
      <div
        style={{
          padding: "6px 12px 4px",
          fontSize: 12,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div>
          <strong style={{ color: "#333" }}>PRIORITY_ID</strong>
          {PRIORITY_ORDER.map((p) => (
            <span key={p} style={{ marginLeft: 12, color: COLORS.priority[p], fontWeight: 600 }}>
              ● <span style={{ color: "#333" }}>{p}</span>
            </span>
          ))}
        </div>
        <div style={{ display: "flex", gap: 14, fontSize: 11 }}>
          {target != null && (
            <span style={{ color: COLORS.bad, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ display: "inline-block", width: 18, height: 0, borderTop: `2px dashed ${COLORS.bad}` }} />
              JOB TARGET: {target.toFixed(2)}
            </span>
          )}
          <span style={{ color: COLORS.target, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ display: "inline-block", width: 18, height: 0, borderTop: `2px dashed ${COLORS.target}` }} />
            AVG: {avg.toFixed(2)}
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 24, right: 20, left: 10, bottom: 8 }} barCategoryGap={4}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "#444", fontSize: 11 }} axisLine={{ stroke: "#bbb" }} tickLine={false} interval={dense ? "preserveStartEnd" : 0} />
          <YAxis tick={{ fill: "#888", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }} />
          {PRIORITY_ORDER.map((p, i) => (
            <Bar key={p} dataKey={p} stackId="d" fill={COLORS.priority[p]} isAnimationActive={false}>
              {!dense && (
                <LabelList
                  dataKey={p}
                  position="center"
                  style={{ fill: "#fff", fontSize: 10, fontWeight: 700 }}
                  formatter={(v) => (v > 0 ? v : "")}
                />
              )}
              {!dense && i === PRIORITY_ORDER.length - 1 && (
                <LabelList
                  dataKey="_total"
                  position="top"
                  style={{ fill: "#333", fontSize: 11, fontWeight: 700 }}
                  formatter={(v) => (v > 0 ? v : "")}
                  offset={4}
                />
              )}
            </Bar>
          ))}
          {/* Reference lines without overlay labels — labels shown in header legend */}
          {target != null && (
            <ReferenceLine
              y={target}
              stroke={COLORS.bad}
              strokeDasharray="4 4"
              strokeWidth={2}
              ifOverflow="extendDomain"
            />
          )}
          <ReferenceLine
            y={avg}
            stroke={COLORS.target}
            strokeDasharray="3 3"
            strokeWidth={2}
            ifOverflow="extendDomain"
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function DailyOverdueChart({ data }) {
  const dense = data.length > DENSE_DAYS;
  return (
    <ChartCard title="Job Overdue / In Due Per day">
      <div style={{ padding: "6px 12px 4px", fontSize: 12 }}>
        <strong style={{ color: "#333" }}>Before Waive</strong>
        <span style={{ marginLeft: 12, color: COLORS.good, fontWeight: 600 }}>● <span style={{ color: "#333" }}>In Due</span></span>
        <span style={{ marginLeft: 12, color: COLORS.bad, fontWeight: 600 }}>● <span style={{ color: "#333" }}>Out Due</span></span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 24, right: 20, left: 10, bottom: 8 }} barCategoryGap={4}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: "#444", fontSize: 11 }} axisLine={{ stroke: "#bbb" }} tickLine={false} interval={dense ? "preserveStartEnd" : 0} />
          <YAxis tick={{ fill: "#888", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }} />
          <Bar dataKey="In Due" stackId="d" fill={COLORS.good}>
            {!dense && <LabelList dataKey="In Due" position="center" style={{ fill: "#fff", fontSize: 10, fontWeight: 700 }} formatter={(v) => (v > 0 ? v : "")} />}
          </Bar>
          <Bar dataKey="Out Due" stackId="d" fill={COLORS.bad}>
            {!dense && <LabelList dataKey="Out Due" position="center" style={{ fill: "#fff", fontSize: 10, fontWeight: 700 }} formatter={(v) => (v > 0 ? v : "")} />}
            {!dense && <LabelList dataKey="_total" position="top" style={{ fill: "#333", fontSize: 11, fontWeight: 700 }} formatter={(v) => (v > 0 ? v : "")} offset={4} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// No `zone` = the whole company: every zone ticked in the filter bar, added together.
export default function JobPerDayPage({ records, zone }) {
  const f = useFilters();
  const co = useCompany();
  const filtered = useMemo(() => {
    if (!zone) return applyFilters(records, f);
    return applyFilters(records, f, ["zone"]).filter((r) => r.z === zone);
  }, [records, f, zone]);

  const dailyP = useMemo(() => buildDailyPriority(filtered, f.start, f.end), [filtered, f.start, f.end]);
  const dailyO = useMemo(() => buildDailyOverdue(filtered, f.start, f.end), [filtered, f.start, f.end]);

  const days = rangeDays(f.start, f.end);
  // The monthly target scales with the months covered, then spreads over the days:
  // a full quarter stays at ~8.5/day instead of shrinking to 260 / 92 = 2.8/day.
  // Company target = the zone targets added up, only when every selected zone has one.
  const companyZones = co.zones.filter((z) => f.zones.includes(z));
  const zoneTargets = companyZones.map((z) => co.zoneTarget(z));
  const monthly = zone
    ? co.zoneTarget(zone)
    : companyZones.length && zoneTargets.every(Boolean)
    ? zoneTargets.reduce((a, b) => a + b, 0)
    : null;
  const target = monthly ? targetForRange(monthly, f.start, f.end) / days : null;
  const avg = filtered.length / days;

  return (
    <div>
      <PageHeader
        title={`Job total done per day : ${zone || co.name}`}
        subtitle={`ช่วง ${f.start} ถึง ${f.end} · ${filtered.length} งาน / ${days} วัน · ${
          monthly ? `เป้า ${monthly}/เดือน → ${target.toFixed(2)}/วัน` : "ยังไม่ได้ตั้งเป้า"
        } · เฉลี่ยจริง ${avg.toFixed(2)}/วัน`}
      />
      <div style={{ display: "grid", gap: 16 }}>
        <DailyPriorityChart data={dailyP} target={target} avg={avg} />
        <DailyOverdueChart data={dailyO} />
      </div>
    </div>
  );
}

import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LabelList,
} from "recharts";
import PageHeader from "../components/PageHeader.jsx";
import ChartCard from "../components/ChartCard.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { COLORS, MONTHS_EN } from "../theme.js";
import { lastSixMonths, monthKey } from "../utils.js";

const PALETTE = ["#1e3a8a", "#d4a017", "#42a5f5", "#a78bfa", "#5DADE2", "#10b981"];

function topProblemsForRange(records, months) {
  // First, find top 5 SUBCAUSE2 by total count across months
  const total = new Map();
  for (const r of records) {
    if (!r.sc) continue;
    if (!months.includes(monthKey(r.d))) continue;
    total.set(r.sc, (total.get(r.sc) || 0) + 1);
  }
  return Array.from(total.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([k]) => k);
}

function buildSeries(records, months, topProblems) {
  // months -> rows; each row has "month": label and one key per problem
  return months.map((mk) => {
    const [y, m] = mk.split("-").map(Number);
    const row = { mk, month: `${MONTHS_EN[m - 1].slice(0, 3)} ${y}` };
    for (const p of topProblems) row[p] = 0;
    for (const r of records) {
      if (monthKey(r.d) !== mk || !r.sc) continue;
      if (topProblems.includes(r.sc)) row[r.sc]++;
    }
    return row;
  });
}

export default function Page08({ records }) {
  const f = useFilters();
  const months = useMemo(() => lastSixMonths(f.end), [f.end]);
  // Date is overridden to be the 6-month window; zone/team/priority filters still apply
  const filtered = useMemo(() => applyFilters(records, f, ["date"]), [records, f]);
  const topProblems = useMemo(() => topProblemsForRange(filtered, months), [filtered, months]);
  const series = useMemo(
    () => buildSeries(filtered, months, topProblems),
    [filtered, months, topProblems]
  );

  return (
    <div>
      <PageHeader title="TOP 5 Problem Reason" subtitle={`6 เดือนสิ้นสุด ${f.end} · SUBCAUSE2 (REPORT_DATE)`} />
      <ChartCard title="TOP 5 Problem Reason">
        <div style={{ padding: "4px 8px", fontSize: 11, color: "#555" }}>
          <strong>SUBCAUSE2</strong>
          {topProblems.map((p, i) => (
            <span key={p} style={{ marginLeft: 12, color: PALETTE[i % PALETTE.length], fontWeight: 600 }}>
              ● <span style={{ color: "#333" }}>{p}</span>
            </span>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={460}>
          <LineChart data={series} margin={{ top: 30, right: 40, left: 20, bottom: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
            <XAxis dataKey="month" tick={{ fill: "#444", fontSize: 12 }} axisLine={{ stroke: "#bbb" }} tickLine={false} />
            <YAxis
              tick={{ fill: "#888", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              label={{ value: "Count of REPORT_DATE", angle: -90, position: "insideLeft", style: { fill: "#888", fontSize: 11 } }}
            />
            <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }} />
            {topProblems.map((p, i) => (
              <Line
                key={p}
                type="linear"
                dataKey={p}
                stroke={PALETTE[i % PALETTE.length]}
                strokeWidth={2.5}
                dot={{ fill: PALETTE[i % PALETTE.length], r: 4 }}
                isAnimationActive={false}
              >
                <LabelList dataKey={p} position="top" style={{ fill: PALETTE[i % PALETTE.length], fontSize: 11, fontWeight: 700 }} />
              </Line>
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

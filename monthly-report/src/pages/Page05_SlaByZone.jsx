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
import { useCompany } from "../company.jsx";
import { COLORS, MONTHS_EN, SLA_PRIORITIES } from "../theme.js";
import { lastSixMonths, monthKey, pct } from "../utils.js";

function slaSeries(records, zone, months) {
  return months.map((mk) => {
    const recs = records.filter(
      (r) =>
        r.z === zone &&
        monthKey(r.d) === mk &&
        SLA_PRIORITIES.has(r.p)
    );
    const before = pct(
      recs.filter((r) => r.bw === "In Due").length,
      recs.length
    );
    const after = pct(
      recs.filter((r) => r.aw === "Pass").length,
      recs.length
    );
    const [y, m] = mk.split("-").map(Number);
    return {
      mk,
      month: MONTHS_EN[m - 1],
      year: y,
      before: +before.toFixed(2),
      after: +after.toFixed(2),
    };
  });
}

function ZoneSla({ zone, records }) {
  const f = useFilters();
  const months = useMemo(() => lastSixMonths(f.end), [f.end]);
  const series = useMemo(
    () =>
      slaSeries(
        // Skip date+zone+priority filters; we use fixed 6-month window and SLA_PRIORITIES
        applyFilters(records, f, ["date", "zone", "priority"]).filter((r) => r.z === zone),
        zone,
        months
      ),
    [records, f, zone, months]
  );

  return (
    <ChartCard title={`SLA% Performance ${zone}`}>
      <div style={{ display: "flex", gap: 12, padding: "6px 12px 4px", fontSize: 12 }}>
        <span style={{ color: COLORS.bad, fontWeight: 600 }}>● <span style={{ color: "#333" }}>SLA Before %</span></span>
        <span style={{ color: COLORS.good, fontWeight: 600 }}>● <span style={{ color: "#333" }}>SLA After %</span></span>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={series} margin={{ top: 30, right: 30, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: "#444", fontSize: 12 }} axisLine={{ stroke: "#bbb" }} tickLine={false} />
          <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "#888", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(v, n) => [`${v}%`, n === "before" ? "SLA Before" : "SLA After"]}
            contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }}
          />
          <Line
            type="monotone"
            dataKey="before"
            stroke={COLORS.bad}
            strokeWidth={2.5}
            strokeDasharray="6 4"
            dot={{ fill: COLORS.bad, r: 4 }}
            isAnimationActive={false}
          >
            <LabelList dataKey="before" position="bottom" formatter={(v) => `${v.toFixed(2)}%`} style={{ fill: COLORS.bad, fontSize: 11, fontWeight: 700 }} />
          </Line>
          <Line
            type="monotone"
            dataKey="after"
            stroke={COLORS.good}
            strokeWidth={2.5}
            dot={{ fill: COLORS.good, r: 4 }}
            isAnimationActive={false}
          >
            <LabelList dataKey="after" position="top" formatter={(v) => `${v.toFixed(2)}%`} style={{ fill: COLORS.good, fontSize: 11, fontWeight: 700 }} />
          </Line>
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default function Page05({ records }) {
  const f = useFilters();
  const co = useCompany();
  const zones = co.zones.filter((z) => f.zones.includes(z));
  const summary = useMemo(() => {
    const filtered = applyFilters(records, f, ["zone", "priority"]);
    return zones.map((z) => {
      const recs = filtered.filter(
        (r) => r.z === z && SLA_PRIORITIES.has(r.p)
      );
      return {
        zone: z,
        n: recs.length,
        after: pct(recs.filter((r) => r.aw === "Pass").length, recs.length),
      };
    });
  }, [records, f, zones]);

  return (
    <div>
      <PageHeader
        title={`SLA% Zone ${summary.map((s) => `${s.zone} ${s.n ? `${s.after.toFixed(2)}%` : "—"}`).join(" · ")}`}
        subtitle={`เปรียบเทียบ Before/After ย้อนหลัง 6 เดือนสิ้นสุด ${f.end} · ใช้เฉพาะงาน Priority Critical + Major`}
      />
      <div style={{ display: "grid", gap: 16 }}>
        {zones.map((z) => (
          <ZoneSla key={z} zone={z} records={records} />
        ))}
      </div>
    </div>
  );
}

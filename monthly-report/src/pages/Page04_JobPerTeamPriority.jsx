import React, { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList } from "recharts";
import PageHeader from "../components/PageHeader.jsx";
import ChartCard from "../components/ChartCard.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { useCompany } from "../company.jsx";
import { COLORS, PRIORITY_ORDER } from "../theme.js";

// Up to this many teams two zones fit side by side; more teams get the full width
// (always vertical columns with each priority's count inside, as the report has always been read).
const MAX_COLUMNS = 8;

function buildStack(records, zone, teams) {
  return teams
    .map((t) => {
      const recs = records.filter((r) => r.z === zone && r.t === t);
      const row = { team: t };
      let total = 0;
      for (const p of PRIORITY_ORDER) {
        const c = recs.filter((r) => r.p === p).length;
        row[p] = c;
        total += c;
      }
      row._total = total;
      return row;
    });
}

function PriorityLegend() {
  return (
    <div style={{ fontSize: 11, padding: "4px 8px 6px", color: "#666", fontWeight: 600 }}>
      PRIORITY_ID
      {PRIORITY_ORDER.map((p) => (
        <span key={p} style={{ marginLeft: 12, color: COLORS.priority[p] }}>
          ● <span style={{ color: "#333" }}>{p}</span>
        </span>
      ))}
    </div>
  );
}

// Count inside a priority segment — skipped when the segment is too short to hold it,
// so tiny segments don't print numbers on top of each other (the bar total still shows).
function SegmentLabel({ x, y, width, height, value, fontSize }) {
  if (!value || height < fontSize + 2) return null;
  return (
    <text x={x + width / 2} y={y + height / 2} fill="#fff" fontSize={fontSize} fontWeight={700} textAnchor="middle" dominantBaseline="central">
      {value}
    </text>
  );
}

function StackedZone({ data }) {
  if (!data.some((r) => r._total > 0)) return <div style={{ padding: 30, textAlign: "center", color: "#999" }}>ไม่มีงานในช่วงนี้</div>;
  // Many teams (3BB has up to 26 technicians per area): drop the empty ones and slant the names.
  const many = data.length > MAX_COLUMNS;
  const rows = many ? data.filter((r) => r._total > 0) : data;
  const dense = rows.length > 14;
  return (
    <ResponsiveContainer width="100%" height={many ? 440 : 380}>
      <BarChart data={rows} margin={{ top: 30, right: 20, left: 10, bottom: 20 }} barCategoryGap={dense ? "15%" : "25%"}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
        <XAxis
          dataKey="team"
          tick={{ fill: "#444", fontSize: dense ? 10 : 11 }}
          axisLine={{ stroke: "#bbb" }}
          tickLine={false}
          interval={0}
          angle={many ? -35 : -12}
          textAnchor="end"
          height={many ? 100 : 60}
        />
        <YAxis tick={{ fill: "#888", fontSize: 12 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }} />
        {PRIORITY_ORDER.map((p, i) => (
          <Bar key={p} dataKey={p} stackId="a" fill={COLORS.priority[p]} maxBarSize={80} isAnimationActive={false}>
            <LabelList dataKey={p} content={(props) => <SegmentLabel {...props} fontSize={dense ? 10 : 12} />} />
            {i === PRIORITY_ORDER.length - 1 && (
              <LabelList dataKey="_total" position="top" style={{ fill: "#333", fontSize: dense ? 11 : 13, fontWeight: 700 }} offset={6} />
            )}
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function Page04({ records }) {
  const f = useFilters();
  const co = useCompany();
  const filtered = useMemo(() => applyFilters(records, f), [records, f]);
  const zoneEntries = useMemo(
    () =>
      co.zones
        .filter((z) => f.zones.includes(z))
        .map((z) => [z, buildStack(filtered, z, co.teamsByZone[z].filter((t) => f.teams.includes(t)))]),
    [filtered, co, f.zones, f.teams]
  );
  // Two zones side by side only when both are short column charts.
  const twoCols = zoneEntries.length >= 2 && zoneEntries.every(([, d]) => d.length <= MAX_COLUMNS);

  return (
    <div>
      <PageHeader title="Job per Team and Priority" subtitle={`ช่วง ${f.start} ถึง ${f.end}`} />
      <div style={{ display: "grid", gridTemplateColumns: twoCols ? "1fr 1fr" : "1fr", gap: 20 }}>
        {zoneEntries.map(([z, d]) => (
          <div key={z}>
            <div
              style={{
                background: "linear-gradient(90deg, #DDE9A0 0%, #E3CB8E 100%)",
                color: "#5b4d20",
                padding: "10px 16px",
                borderRadius: 8,
                fontWeight: 700,
                fontSize: 18,
                textAlign: "center",
                marginBottom: 12,
                boxShadow: "0 4px 10px rgba(0,0,0,0.12)",
              }}
            >
              PRIORITY {z}
            </div>
            <ChartCard title="Job Total and Priority">
              <PriorityLegend />
              <StackedZone data={d} />
            </ChartCard>
          </div>
        ))}
      </div>
    </div>
  );
}

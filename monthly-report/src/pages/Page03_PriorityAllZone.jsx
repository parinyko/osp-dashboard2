import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
  LabelList,
} from "recharts";
import PageHeader from "../components/PageHeader.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { COLORS, PRIORITY_ORDER } from "../theme.js";

export default function Page03({ records }) {
  const f = useFilters();
  const rows = useMemo(() => {
    const filtered = applyFilters(records, f, ["priority"]);
    return PRIORITY_ORDER.map((p) => ({
      priority: p,
      count: filtered.filter((r) => r.p === p).length,
    }));
  }, [records, f]);
  const yMax = Math.max(...rows.map((r) => r.count), 1) * 1.2;

  return (
    <div>
      <PageHeader title="Priority All Zone" subtitle={`ช่วง ${f.start} ถึง ${f.end}`} />
      <div
        style={{
          background: "#fff",
          color: "#1f1f2c",
          borderRadius: 12,
          padding: 20,
          boxShadow: "0 8px 28px rgba(0,0,0,0.18)",
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: "#444",
            marginBottom: 12,
            letterSpacing: "0.05em",
          }}
        >
          PRIORITY IN ZONE
        </div>
        <ResponsiveContainer width="100%" height={460}>
          <BarChart data={rows} margin={{ top: 40, right: 30, left: 20, bottom: 20 }} barCategoryGap="30%">
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e2e2" vertical={false} />
            <XAxis dataKey="priority" tick={{ fill: "#444", fontSize: 13 }} axisLine={{ stroke: "#bbb" }} tickLine={false} />
            <YAxis
              domain={[0, Math.ceil(yMax / 20) * 20]}
              tick={{ fill: "#888", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
            <Bar dataKey="count" radius={[2, 2, 0, 0]} maxBarSize={120}>
              {rows.map((r, i) => (
                <Cell key={i} fill={COLORS.priority[r.priority]} />
              ))}
              <LabelList dataKey="count" position="top" style={{ fill: "#1f1f2c", fontSize: 16, fontWeight: 700 }} offset={8} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 16,
          marginTop: 20,
        }}
      >
        {rows.map((r) => (
          <div
            key={r.priority}
            style={{
              background: "#ffffff",
              border: `1px solid ${COLORS.priority[r.priority]}55`,
              borderRadius: 12,
              padding: 14,
              textAlign: "center",
              boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
            }}
          >
            <div style={{ fontSize: 11, color: "#8b8b96", textTransform: "uppercase", marginBottom: 4 }}>
              {r.priority}
            </div>
            <div style={{ fontSize: 26, fontWeight: 700, color: COLORS.priority[r.priority] }}>
              {r.count.toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

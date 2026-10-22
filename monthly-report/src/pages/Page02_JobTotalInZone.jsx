import React, { useMemo } from "react";
import {
  ComposedChart,
  Bar,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
  ResponsiveContainer,
  LabelList,
} from "recharts";
import PageHeader from "../components/PageHeader.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { useCompany } from "../company.jsx";
import { COLORS } from "../theme.js";
import { targetForRange } from "../utils.js";

// Target marker for zones whose targets differ: a dashed tick across the bar.
function TargetTick({ cx, cy, payload }) {
  if (cx == null || cy == null || payload?.target == null) return null;
  const w = 70;
  const text = `เป้า ${payload.target}`;
  return (
    <g>
      <line x1={cx - w / 2} x2={cx + w / 2} y1={cy} y2={cy} stroke="#42a5f5" strokeWidth={3} strokeDasharray="6 4" />
      <text x={cx + w / 2 + 4} y={cy + 4} fill="#1e7fc7" fontSize={11} fontWeight={700}>
        {text}
      </text>
    </g>
  );
}

export default function Page02({ records }) {
  const f = useFilters();
  const co = useCompany();
  const rows = useMemo(() => {
    const filtered = applyFilters(records, f);
    return co.zones
      .filter((z) => f.zones.includes(z))
      .map((z) => {
        const monthly = co.zoneTarget(z);
        // Targets are per month: a quarter is judged against 3×, half a month against ½×.
        const target = monthly ? Math.max(1, Math.round(targetForRange(monthly, f.start, f.end))) : null;
        return { zone: z, count: filtered.filter((r) => r.z === z).length, target, monthly };
      });
  }, [records, f, co]);

  const targets = rows.map((r) => r.target).filter((t) => t != null);
  const uniform = targets.length === rows.length && targets.length > 0 && targets.every((t) => t === targets[0]);
  const total = rows.reduce((s, r) => s + r.count, 0);
  const yMax = Math.max(...targets.map((t) => t * 1.1), ...rows.map((r) => r.count * 1.2), 50);
  const color = (r) => (r.target == null ? COLORS.neutralBar : r.count >= r.target ? "#2ECC71" : "#E74C3C");
  const monthlyNote = uniform
    ? `เป้าหมาย ${targets[0]} งาน / โซน (${rows[0].monthly} งาน / เดือน)`
    : targets.length
    ? "เป้าหมายแยกตามโซน (ดูเส้นประในกราฟ)"
    : "ยังไม่ได้ตั้งเป้าหมาย";

  return (
    <div>
      <PageHeader
        title={`Job Total in Zone — Total ${total.toLocaleString()} Job`}
        subtitle={`ช่วง ${f.start} ถึง ${f.end} — ${monthlyNote}`}
      />
      <div style={{ background: "#fff", borderRadius: 12, padding: 20, boxShadow: "0 8px 28px rgba(0,0,0,0.18)" }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#444", marginBottom: 12, letterSpacing: "0.05em" }}>
          JOB TOTAL IN ZONE
        </div>
        <ResponsiveContainer width="100%" height={460}>
          <ComposedChart data={rows} margin={{ top: 40, right: 60, left: 20, bottom: 20 }} barCategoryGap="35%">
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e2e2" vertical={false} />
            <XAxis dataKey="zone" tick={{ fill: "#444", fontSize: 13 }} axisLine={{ stroke: "#bbb" }} tickLine={false} />
            <YAxis
              domain={[0, Math.ceil(yMax / 50) * 50]}
              tick={{ fill: "#888", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              label={{ value: "Count of JB_ID", angle: -90, position: "insideLeft", offset: 0, style: { fill: "#888", fontSize: 12 } }}
            />
            <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
            {uniform && (
              <ReferenceLine
                y={targets[0]}
                stroke="#42a5f5"
                strokeDasharray="8 6"
                strokeWidth={2.5}
                label={({ viewBox }) => {
                  const x = viewBox.x + 8;
                  const y = viewBox.y - 8;
                  const text = `Job Target ${targets[0]} Per Area`;
                  return (
                    <g>
                      <rect x={x - 6} y={y - 12} width={text.length * 6.8 + 12} height={18} rx={3} fill="#fff" stroke="#42a5f5" strokeWidth={1} opacity={0.95} />
                      <text x={x} y={y + 1} fill="#1e7fc7" fontSize={12} fontWeight={600}>{text}</text>
                    </g>
                  );
                }}
              />
            )}
            <Bar dataKey="count" radius={[2, 2, 0, 0]} maxBarSize={140} isAnimationActive={false}>
              {rows.map((r) => (
                <Cell key={r.zone} fill={color(r)} />
              ))}
              <LabelList dataKey="count" position="top" style={{ fill: "#1f1f2c", fontSize: 20, fontWeight: 700 }} offset={10} />
            </Bar>
            {!uniform && targets.length > 0 && (
              <Scatter dataKey="target" shape={<TargetTick />} isAnimationActive={false} />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 16, marginTop: 20 }}>
        {rows.map((r) => (
          <SummaryCard
            key={r.zone}
            label={r.zone}
            value={r.count}
            color={color(r)}
            note={r.target == null ? "ไม่มีเป้า" : r.count >= r.target ? "ถึงเป้า" : `ต่ำกว่าเป้า ${r.target - r.count}`}
          />
        ))}
        <SummaryCard label="รวมทั้งหมด" value={total} color="#42a5f5" note="all selected zones" />
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color, note }) {
  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #e6e6ea",
        borderRadius: 12,
        padding: 18,
        textAlign: "center",
        boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
      }}
    >
      <div style={{ fontSize: 11, color: "#8b8b96", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 30, fontWeight: 700, color }}>{value.toLocaleString()}</div>
      <div style={{ fontSize: 11, color: "#8b8b96", marginTop: 2 }}>{note}</div>
    </div>
  );
}

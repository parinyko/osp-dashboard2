import React, { useMemo, useState } from "react";
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
import ChartCard from "../components/ChartCard.jsx";
import { useFilters, applyFilters } from "../filters.jsx";

const PENDING_TOKEN = "รอลงข้อมูล";

const PALETTE = [
  "#3498DB", "#27AE60", "#F39C12", "#9B59B6", "#E67E22",
  "#16A085", "#E74C3C", "#34495E", "#1ABC9C", "#D35400",
  "#7F8C8D", "#8E44AD", "#F1C40F", "#2980B9", "#C0392B",
];

function colorFor(name, i) {
  if (name === PENDING_TOKEN) return "#E74C3C";
  if (name === "ไม่มีการแก้ไข") return "#7F8C8D";
  return PALETTE[i % PALETTE.length];
}

export default function DashSolutionSummary({ records }) {
  const f = useFilters();
  const [topN, setTopN] = useState(15);
  const filtered = useMemo(() => applyFilters(records, f), [records, f]);

  const summary = useMemo(() => {
    const map = new Map();
    let totalWithSol = 0;
    let blank = 0;
    for (const r of filtered) {
      const s = r.sol;
      if (!s) {
        blank++;
        continue;
      }
      totalWithSol++;
      map.set(s, (map.get(s) || 0) + 1);
    }
    const rows = Array.from(map.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
    return { rows, totalWithSol, blank, total: filtered.length };
  }, [filtered]);

  const { rows, totalWithSol, blank, total } = summary;
  const pending = rows.find((r) => r.name === PENDING_TOKEN)?.count || 0;
  const pendingPct = totalWithSol > 0 ? (pending / totalWithSol) * 100 : 0;
  const displayed = rows.slice(0, topN);
  const remaining = rows.slice(topN);
  const remainingCount = remaining.reduce((s, r) => s + r.count, 0);

  return (
    <div>
      <PageHeader
        title="🗄️ Solution Summary — สรุปรายงานวิธีแก้ไข"
        subtitle={`ช่วง ${f.start} ถึง ${f.end} · ${rows.length} รูปแบบของ Solution`}
      />

      {/* Summary cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 14,
          marginBottom: 18,
        }}
      >
        <StatCard label="ทั้งหมด" value={total} color="#34495E" />
        <StatCard label="มี Solution" value={totalWithSol} color="#27AE60" />
        <StatCard label="ยังไม่มี / ว่าง" value={blank} color="#95A5A6" />
        <StatCard
          label={`🚨 ${PENDING_TOKEN}`}
          value={pending}
          color="#E74C3C"
          subtitle={`${pendingPct.toFixed(1)}% ของงานที่มี Solution`}
        />
      </div>

      {/* Bar chart */}
      <ChartCard title={`TOP ${topN} วิธีแก้ไขที่พบบ่อย`}>
        <div style={{ padding: "6px 12px 8px", display: "flex", justifyContent: "flex-end", gap: 6 }}>
          {[10, 15, 20, 30, 50].map((n) => (
            <button
              key={n}
              onClick={() => setTopN(n)}
              style={{
                padding: "4px 10px",
                fontSize: 11,
                border: topN === n ? "1px solid #4d6a1f" : "1px solid #d4d4dc",
                background: topN === n ? "#4d6a1f" : "#fff",
                color: topN === n ? "#fff" : "#666",
                borderRadius: 12,
                cursor: "pointer",
                fontWeight: topN === n ? 700 : 500,
              }}
            >
              TOP {n}
            </button>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={Math.max(320, displayed.length * 28 + 60)}>
          <BarChart
            data={displayed}
            layout="vertical"
            margin={{ top: 8, right: 60, left: 12, bottom: 8 }}
          >
            <CartesianGrid horizontal={false} stroke="#eee" />
            <XAxis type="number" tick={{ fill: "#888", fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: "#333", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={300}
              interval={0}
            />
            <Tooltip
              formatter={(v) => [v.toLocaleString(), "จำนวน"]}
              contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              {displayed.map((row, i) => (
                <Cell key={row.name} fill={colorFor(row.name, i)} />
              ))}
              <LabelList
                dataKey="count"
                position="right"
                style={{ fill: "#333", fontSize: 12, fontWeight: 700 }}
                formatter={(v) => v.toLocaleString()}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Full table */}
      <div style={{ marginTop: 18 }}>
        <ChartCard title="ตารางรายการ Solution ทั้งหมด">
          <div style={{ maxHeight: 460, overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead style={{ position: "sticky", top: 0 }}>
                <tr style={{ background: "#f4f4f4", color: "#444" }}>
                  <th style={{ textAlign: "left", padding: "8px 10px", width: 40 }}>#</th>
                  <th style={{ textAlign: "left", padding: "8px 10px" }}>Solution</th>
                  <th style={{ textAlign: "right", padding: "8px 10px", width: 100 }}>จำนวน</th>
                  <th style={{ textAlign: "right", padding: "8px 10px", width: 80 }}>%</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const isPending = r.name === PENDING_TOKEN;
                  return (
                    <tr
                      key={r.name}
                      style={{
                        borderBottom: "1px solid #f0f0f3",
                        background: isPending ? "#fdecea" : "transparent",
                        color: isPending ? "#9c2a18" : "#1f1f2c",
                        fontWeight: isPending ? 700 : 500,
                      }}
                    >
                      <td style={{ padding: "6px 10px", color: "#999" }}>{i + 1}</td>
                      <td style={{ padding: "6px 10px" }}>
                        {isPending && <span style={{ marginRight: 6 }}>🚨</span>}
                        {r.name}
                      </td>
                      <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "DM Mono, monospace" }}>
                        {r.count.toLocaleString()}
                      </td>
                      <td style={{ padding: "6px 10px", textAlign: "right", color: "#888" }}>
                        {((r.count / totalWithSol) * 100).toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr style={{ background: "#fafafc", fontWeight: 700 }}>
                  <td colSpan={2} style={{ padding: "8px 10px" }}>รวม (มี Solution)</td>
                  <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "DM Mono, monospace" }}>
                    {totalWithSol.toLocaleString()}
                  </td>
                  <td style={{ padding: "8px 10px", textAlign: "right" }}>100.00%</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </ChartCard>
      </div>
    </div>
  );
}

function StatCard({ label, value, color, subtitle }) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #ececef",
        borderRadius: 12,
        padding: "14px 16px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
        borderLeft: `4px solid ${color}`,
      }}
    >
      <div style={{ fontSize: 11, color: "#8b8b96", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color, marginTop: 4 }}>
        {(value || 0).toLocaleString()}
      </div>
      {subtitle && (
        <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{subtitle}</div>
      )}
    </div>
  );
}

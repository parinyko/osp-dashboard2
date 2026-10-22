import React, { useMemo } from "react";
import PageHeader from "../components/PageHeader.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { useCompany } from "../company.jsx";
import { pct, fmtPct, prevMonthRange } from "../utils.js";

function band(sla) {
  if (sla >= 90) return { label: "Excellent", color: "#27AE60", bg: "#E8F8EE", icon: "▲" };
  if (sla >= 80) return { label: "Good", color: "#3498DB", bg: "#EAF4FB", icon: "●" };
  if (sla >= 60) return { label: "Warning", color: "#F39C12", bg: "#FEF5E7", icon: "◆" };
  return { label: "Critical", color: "#E74C3C", bg: "#FDECEA", icon: "▼" };
}

function bandRange(sla) {
  if (sla >= 90) return "90–100%";
  if (sla >= 80) return "80–90%";
  if (sla >= 60) return "60–80%";
  return "< 60%";
}

function teamStats(records, team) {
  const recs = records.filter((r) => r.t === team);
  const pass = recs.filter((r) => r.aw === "Pass").length;
  return { sla: pct(pass, recs.length), n: recs.length, pass };
}

function ArcGauge({ value, color }) {
  // semicircle gauge: radius 40, centered at (50, 50) so the chip sits in 100x55
  const v = Math.max(0, Math.min(100, value || 0));
  const r = 36;
  const cx = 50;
  const cy = 50;
  // background full half-circle path
  const bgPath = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  // foreground proportional to value
  const angle = Math.PI * (v / 100); // 0..pi from left to right
  const x = cx - r * Math.cos(angle);
  const y = cy - r * Math.sin(angle);
  const largeArc = 0;
  const sweep = 1;
  const fgPath = v <= 0 ? "" : `M ${cx - r} ${cy} A ${r} ${r} 0 ${largeArc} ${sweep} ${x} ${y}`;
  return (
    <svg viewBox="0 0 100 60" width="120" height="72" style={{ overflow: "visible" }}>
      <path d={bgPath} stroke="#eef0f3" strokeWidth={10} fill="none" strokeLinecap="round" />
      {fgPath && <path d={fgPath} stroke={color} strokeWidth={10} fill="none" strokeLinecap="round" />}
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize={18} fontWeight={800} fill={color}>
        {isNaN(v) ? "—" : v.toFixed(2)}
      </text>
      <text x={cx} y={cy + 10} textAnchor="middle" fontSize={9} fill="#888">%</text>
    </svg>
  );
}

function KPICard({ team, current, previous, n, pass }) {
  const b = band(current);
  const delta = (current || 0) - (previous || 0);
  const deltaPos = delta > 0.005;
  const deltaNeg = delta < -0.005;
  const deltaColor = deltaPos ? "#27AE60" : deltaNeg ? "#E74C3C" : "#999";
  const deltaSymbol = deltaPos ? "▲" : deltaNeg ? "▼" : "—";

  return (
    <div
      style={{
        background: "#fff",
        color: "#1f1f2c",
        borderRadius: 14,
        overflow: "hidden",
        boxShadow: "0 6px 16px rgba(0,0,0,0.08)",
        border: "1px solid #ececef",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header with status band */}
      <div
        style={{
          padding: "12px 16px",
          background: b.bg,
          borderBottom: `1px solid ${b.color}33`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div
            style={{
              fontSize: 10,
              color: "#888",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              fontWeight: 600,
            }}
          >
            Team
          </div>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#1f1f2c", marginTop: 1 }} title={team}>
            {team}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            background: "#fff",
            border: `1px solid ${b.color}`,
            color: b.color,
            borderRadius: 12,
            padding: "3px 10px",
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          <span style={{ fontSize: 10 }}>{b.icon}</span>
          <span>{b.label}</span>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: "14px 16px 12px", display: "flex", gap: 12, alignItems: "center" }}>
        <ArcGauge value={current} color={b.color} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11, color: "#888", lineHeight: 1.2 }}>
            ระดับ <span style={{ color: b.color, fontWeight: 700 }}>{bandRange(current)}</span>
          </div>
          <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
            Last Month
            <div style={{ fontSize: 14, fontWeight: 700, color: "#1f1f2c", fontFamily: "DM Mono, monospace" }}>
              {fmtPct(previous)}
            </div>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ padding: "0 16px 8px" }}>
        <div style={{ position: "relative", height: 8, background: "#f0f0f3", borderRadius: 4, overflow: "hidden" }}>
          <div
            style={{
              width: `${Math.min(100, Math.max(0, current || 0))}%`,
              height: "100%",
              background: `linear-gradient(90deg, ${b.color}99, ${b.color})`,
              transition: "width 0.3s",
            }}
          />
          {/* 90% target tick */}
          <div
            style={{
              position: "absolute",
              left: "90%",
              top: -2,
              bottom: -2,
              width: 2,
              background: "#1f1f2c66",
              borderRadius: 1,
            }}
            title="Target 90%"
          />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "#aaa", marginTop: 3 }}>
          <span>0%</span>
          <span style={{ color: "#666" }}>Target 90%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Footer stats */}
      <div
        style={{
          padding: "8px 16px 12px",
          borderTop: "1px solid #f0f0f3",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: 11,
        }}
      >
        <div style={{ color: "#888" }}>
          Pass <span style={{ color: "#27AE60", fontWeight: 700 }}>{pass.toLocaleString()}</span>{" / "}
          <span style={{ color: "#444", fontWeight: 600 }}>{n.toLocaleString()}</span> jobs
        </div>
        <div
          style={{
            color: deltaColor,
            fontWeight: 700,
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <span>{deltaSymbol}</span>
          <span>{Math.abs(delta).toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
}

export default function Page22({ records }) {
  const f = useFilters();
  const co = useCompany();
  const [prevStart, prevEnd] = useMemo(() => prevMonthRange(f.end), [f.end]);
  const currRecs = useMemo(() => applyFilters(records, f), [records, f]);
  const prevRecs = useMemo(
    () => applyFilters(records, { ...f, start: prevStart, end: prevEnd }),
    [records, f, prevStart, prevEnd]
  );
  const cards = co.allFilterTeams.filter((t) => f.teams.includes(t)).map((t) => {
    const cur = teamStats(currRecs, t);
    const prev = teamStats(prevRecs, t);
    return {
      team: t,
      current: cur.sla,
      previous: prev.sla,
      n: cur.n,
      pass: cur.pass,
      prevN: prev.n,
    };
  }).filter((c) => c.n > 0 || c.prevN > 0);

  return (
    <div>
      <PageHeader
        title="KPI SLA % Per Team"
        subtitle={`เทียบ ${prevStart}…${prevEnd} กับ ${f.start}…${f.end}`}
      />
      {cards.length === 0 && (
        <div style={{ background: "#fff", borderRadius: 12, padding: 40, textAlign: "center", color: "#999" }}>
          ไม่มีงานในช่วงนี้
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${cards.length > 9 ? 4 : 3}, 1fr)`, gap: 16 }}>
        {cards.map((c) => (
          <KPICard key={c.team} {...c} />
        ))}
      </div>
      <div
        style={{
          marginTop: 18,
          padding: "10px 14px",
          background: "#fafafc",
          border: "1px dashed #d4d4dc",
          borderRadius: 8,
          fontSize: 11,
          color: "#666",
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          justifyContent: "center",
        }}
      >
        <span><span style={{ background: "#E8F8EE", color: "#27AE60", padding: "2px 10px", borderRadius: 10, fontWeight: 700 }}><span style={{ fontSize: 9, marginRight: 4 }}>▲</span>Excellent</span> ≥ 90%</span>
        <span><span style={{ background: "#EAF4FB", color: "#3498DB", padding: "2px 10px", borderRadius: 10, fontWeight: 700 }}><span style={{ fontSize: 9, marginRight: 4 }}>●</span>Good</span> 80–90%</span>
        <span><span style={{ background: "#FEF5E7", color: "#F39C12", padding: "2px 10px", borderRadius: 10, fontWeight: 700 }}><span style={{ fontSize: 9, marginRight: 4 }}>◆</span>Warning</span> 60–80%</span>
        <span><span style={{ background: "#FDECEA", color: "#E74C3C", padding: "2px 10px", borderRadius: 10, fontWeight: 700 }}><span style={{ fontSize: 9, marginRight: 4 }}>▼</span>Critical</span> &lt; 60%</span>
      </div>
    </div>
  );
}

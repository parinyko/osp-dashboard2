import React, { useMemo, useState } from "react";
import PageHeader from "../components/PageHeader.jsx";
import ChartCard from "../components/ChartCard.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { useCompany } from "../company.jsx";

const PENDING_TOKEN = "รอลงข้อมูล";

function dayLabel(iso) {
  if (!iso) return "—";
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

export default function DashPendingByTeam({ records }) {
  const f = useFilters();
  const co = useCompany();
  const [searchQ, setSearchQ] = useState("");

  // Skip the global team filter so every team with pending jobs shows up; the
  // zone filter still narrows it down.
  const pending = useMemo(
    () => applyFilters(records, f, ["team"]).filter((r) => r.sol === PENDING_TOKEN),
    [records, f]
  );

  const groups = useMemo(() => {
    const map = new Map();
    for (const r of pending) {
      const team = r.t || r.a || "(unknown)";
      if (!map.has(team)) map.set(team, { team, zone: r.z, list: [] });
      map.get(team).list.push(r);
    }
    for (const g of map.values()) g.list.sort((a, b) => (b.d || "").localeCompare(a.d || ""));
    return Array.from(map.values())
      .map((g) => ({ ...g, count: g.list.length }))
      .sort((a, b) => b.count - a.count);
  }, [pending]);

  const zonesWithPending = new Set(groups.map((g) => g.zone)).size;
  const oldest = pending.reduce((m, r) => (!m || r.d < m ? r.d : m), null);

  const matchSearch = (r) => {
    if (!searchQ.trim()) return true;
    const q = searchQ.trim().toLowerCase();
    return (
      (r.jb || "").toLowerCase().includes(q) ||
      (r.d || "").includes(q) ||
      (r.prb || "").toLowerCase().includes(q) ||
      (r.sc || "").toLowerCase().includes(q)
    );
  };

  return (
    <div>
      <PageHeader
        title="🚨 งานที่รอลงข้อมูล (Pending Solution)"
        subtitle={`ช่วง ${f.start} ถึง ${f.end} · ใช้ REPORT_DATE · Solution = "${PENDING_TOKEN}"`}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 18 }}>
        <StatCard label="รวมงานที่รอลง" value={pending.length} color="#E74C3C" />
        <StatCard label="ทีมที่มีรายการ" value={groups.length} color="#3498DB" />
        <StatCard label="โซนที่มีรายการ" value={zonesWithPending} color="#27AE60" />
        <StatCard label="งานที่ค้างนานสุด" value={oldest || "—"} color="#F39C12" raw />
      </div>

      <div
        style={{
          background: "#fff",
          border: "1px solid #ececef",
          borderRadius: 12,
          padding: 14,
          marginBottom: 14,
          display: "flex",
          gap: 12,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <input
          type="search"
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          placeholder="ค้นหา JB_ID / วันที่ / Problem / SUBCAUSE2"
          style={{
            flex: 1,
            minWidth: 240,
            padding: "8px 12px",
            border: "1px solid #d4d4dc",
            borderRadius: 8,
            fontSize: 13,
            color: "#1f1f2c",
          }}
        />
        <span style={{ fontSize: 11, color: "#888" }}>
          พบ {groups.length} ทีม · {pending.length.toLocaleString()} งาน
        </span>
      </div>

      {groups.length === 0 && (
        <div style={{ background: "#fff", border: "1px dashed #d4d4dc", borderRadius: 12, padding: 40, textAlign: "center", color: "#888" }}>
          🎉 ไม่มีงานที่รอลงข้อมูลในช่วงนี้
        </div>
      )}

      <div style={{ display: "grid", gap: 14 }}>
        {groups.map((g) => {
          const visible = g.list.filter(matchSearch);
          return (
            <TeamPanel
              key={g.team}
              team={g.team}
              zone={g.zone}
              color={co.zoneColor(g.zone)}
              total={g.count}
              visibleCount={visible.length}
              records={visible}
            />
          );
        })}
      </div>
    </div>
  );
}

function TeamPanel({ team, zone, color, total, visibleCount, records }) {
  // Group by report-date so we can show "day-by-day" view
  const byDay = useMemo(() => {
    const map = new Map();
    for (const r of records) {
      const k = r.d;
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(r);
    }
    return Array.from(map.entries())
      .sort((a, b) => b[0].localeCompare(a[0]));
  }, [records]);

  return (
    <ChartCard
      headerStyle={{
        background: `linear-gradient(135deg, ${color} 0%, ${color}cc 100%)`,
        color: "#fff",
        textAlign: "left",
      }}
      title={
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 4px" }}>
          <span>{team} <span style={{ fontWeight: 500, opacity: 0.85 }}>· {zone}</span></span>
          <span style={{ fontSize: 12, fontWeight: 500, opacity: 0.9 }}>
            {visibleCount === total
              ? `${total.toLocaleString()} รายการรอลง`
              : `${visibleCount.toLocaleString()} / ${total.toLocaleString()} รายการ`}
          </span>
        </div>
      }
    >
      {records.length === 0 ? (
        <div style={{ padding: 20, textAlign: "center", color: "#aaa", fontSize: 12 }}>
          ไม่พบรายการที่ตรงกับการค้นหา
        </div>
      ) : (
        <div style={{ maxHeight: 420, overflow: "auto" }}>
          {byDay.map(([day, items]) => (
            <div key={day} style={{ marginBottom: 12 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  background: "#f7f7fa",
                  borderRadius: 6,
                  marginBottom: 6,
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#444",
                }}
              >
                <span style={{ color: "#E74C3C" }}>📅</span>
                <span>{day}</span>
                <span style={{ color: "#999", fontWeight: 500 }}>({dayLabel(day)})</span>
                <span style={{ marginLeft: "auto", color: "#888", fontWeight: 500 }}>
                  {items.length} งาน
                </span>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                  gap: 8,
                  padding: "0 4px",
                }}
              >
                {items.map((r) => (
                  <JobChip key={r.jb || r.d + r.a} r={r} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </ChartCard>
  );
}

function JobChip({ r }) {
  return (
    <div
      style={{
        padding: "8px 10px",
        background: "#fdecea",
        border: "1px solid #f8b4ad",
        borderRadius: 8,
        fontSize: 12,
        lineHeight: 1.4,
      }}
      title={`Problem: ${r.prb || "—"}\nSUBCAUSE2: ${r.sc || "—"}`}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span
          style={{
            fontWeight: 700,
            color: "#9c2a18",
            fontFamily: "DM Mono, monospace",
          }}
        >
          {r.jb || "—"}
        </span>
        {r.p && (
          <span style={{ fontSize: 10, color: "#888", fontWeight: 600 }}>{r.p}</span>
        )}
      </div>
      <div style={{ fontSize: 11, color: "#666", marginTop: 2 }}>
        {r.sc ? r.sc.slice(0, 60) + (r.sc.length > 60 ? "…" : "") : (r.prb || "—")}
      </div>
    </div>
  );
}

function StatCard({ label, value, color, subtitle, raw }) {
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
        {raw ? value : (value || 0).toLocaleString()}
      </div>
      {subtitle && (
        <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{subtitle}</div>
      )}
    </div>
  );
}

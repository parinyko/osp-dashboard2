import React, { useMemo } from "react";
import PageHeader from "../components/PageHeader.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { useCompany } from "../company.jsx";
import { mean, formatSeconds, prevMonthRange } from "../utils.js";

const MEDAL_COLORS = ["#F5C518", "#B8B8C0", "#CD7F32"]; // gold, silver, bronze
const WORST_COLORS = ["#E74C3C", "#F39C12", "#F1C40F"]; // red, orange, yellow (descending severity)

function teamAvgFor(records, teams, key) {
  return teams
    .map((t) => {
      const recs = records.filter((r) => r.t === t);
      const m = mean(recs.map((r) => r[key]));
      return { team: t, count: recs.length, sec: m };
    })
    .filter((r) => r.sec != null);
}

// Build a map: team -> { rank, sec, count } for the given sort direction.
// fastest=true sorts ascending (rank 1 = fastest); false sorts descending.
function rankMap(items, fastest) {
  const sorted = [...items].sort((a, b) => (fastest ? a.sec - b.sec : b.sec - a.sec));
  const m = new Map();
  sorted.forEach((r, i) => m.set(r.team, { rank: i + 1, sec: r.sec, count: r.count }));
  return m;
}

function RankDelta({ current, previous }) {
  if (previous == null) {
    return (
      <span style={{ color: "#aaa", fontSize: 10, fontWeight: 600 }} title="ไม่มีข้อมูลเดือนก่อน">
        NEW
      </span>
    );
  }
  const diff = previous - current; // positive = moved up in rank (better)
  if (diff === 0) {
    return (
      <span style={{ color: "#888", fontSize: 11, fontWeight: 700 }} title="อันดับเท่าเดือนก่อน">
        —
      </span>
    );
  }
  if (diff > 0) {
    return (
      <span style={{ color: "#27AE60", fontSize: 11, fontWeight: 700 }} title={`อันดับดีขึ้น ${diff}`}>
        ▲ {diff}
      </span>
    );
  }
  return (
    <span style={{ color: "#E74C3C", fontSize: 11, fontWeight: 700 }} title={`อันดับแย่ลง ${Math.abs(diff)}`}>
      ▼ {Math.abs(diff)}
    </span>
  );
}

function RankRow({ rank, team, count, sec, max, color, mode, prevRank, prevSec }) {
  const widthPct = max ? Math.min(100, (sec / max) * 100) : 0;
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "32px 1fr 70px 110px 56px",
        alignItems: "center",
        padding: "10px 12px",
        background: rank === 1 ? `${color}15` : "#fafafc",
        borderLeft: `4px solid ${color}`,
        borderRadius: 8,
        marginBottom: 6,
        columnGap: 10,
      }}
    >
      <div
        style={{
          width: 26,
          height: 26,
          borderRadius: 13,
          background: color,
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 13,
          fontWeight: 800,
        }}
      >
        {rank}
      </div>
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: "#1f1f2c",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={team}
        >
          {team}
        </div>
        <div style={{ fontSize: 10, color: "#8b8b96", marginTop: 1 }}>
          N = {count.toLocaleString()}
          {prevRank != null && (
            <span style={{ marginLeft: 6 }}>
              · เดือนก่อน #{prevRank} {prevSec != null && `(${formatSeconds(prevSec)})`}
            </span>
          )}
        </div>
      </div>
      <div style={{ position: "relative", height: 6, background: "#ececef", borderRadius: 3 }}>
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            height: "100%",
            width: `${widthPct}%`,
            background: mode === "best" ? "#27AE60" : "#E74C3C",
            borderRadius: 3,
            opacity: 0.6,
          }}
        />
      </div>
      <div
        style={{
          fontFamily: "DM Mono, monospace",
          fontSize: 14,
          fontWeight: 700,
          color: color,
          textAlign: "right",
        }}
      >
        {formatSeconds(sec)}
      </div>
      <div style={{ textAlign: "right" }}>
        <RankDelta current={rank} previous={prevRank} />
      </div>
    </div>
  );
}

function SectionLabel({ symbol, symbolColor, text, textColor }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: 8,
        color: textColor,
        fontSize: 13,
        fontWeight: 700,
      }}
    >
      <span
        style={{
          width: 20,
          height: 20,
          borderRadius: 4,
          background: symbolColor,
          color: "#fff",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 11,
          fontWeight: 800,
          flexShrink: 0,
        }}
      >
        {symbol}
      </span>
      <span>{text}</span>
    </div>
  );
}

function RankingCard({ label, sublabel, items, prevItems, average }) {
  if (!items.length) {
    return (
      <div style={{ background: "#fff", borderRadius: 14, padding: 24, textAlign: "center", color: "#999" }}>
        ไม่มีข้อมูล
      </div>
    );
  }

  const fastest = [...items].sort((a, b) => a.sec - b.sec).slice(0, 3);
  const slowest = [...items].sort((a, b) => b.sec - a.sec).slice(0, 3);
  const maxSec = Math.max(...items.map((r) => r.sec));

  // Pre-compute previous-month rank maps for the same metric.
  const prevFastest = rankMap(prevItems, true);  // fastest = rank 1
  const prevSlowest = rankMap(prevItems, false); // slowest = rank 1

  return (
    <div
      style={{
        background: "#fff",
        borderRadius: 14,
        overflow: "hidden",
        boxShadow: "0 6px 16px rgba(0,0,0,0.08)",
        border: "1px solid #ececef",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(135deg, #3c4a5a 0%, #2b3744 100%)",
          color: "#fff",
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "3px solid #7CC242",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 4,
              height: 38,
              borderRadius: 2,
              background: "#7CC242",
            }}
          />
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: "-0.01em" }}>{label}</div>
            <div style={{ fontSize: 11, opacity: 0.85, marginTop: 2 }}>{sublabel}</div>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 10, opacity: 0.7, letterSpacing: "0.06em", textTransform: "uppercase" }}>
            เฉลี่ยรวม
          </div>
          <div style={{ fontSize: 19, fontWeight: 800, fontFamily: "DM Mono, monospace" }}>
            {formatSeconds(average)}
          </div>
        </div>
      </div>

      {/* Best section */}
      <div style={{ padding: "12px 14px 6px" }}>
        <SectionLabel
          symbol="▲"
          symbolColor="#27AE60"
          text="TOP 3 — ดีที่สุด (เร็วที่สุด)"
          textColor="#1d6b3a"
        />
        {fastest.map((r, i) => {
          const prev = prevFastest.get(r.team);
          return (
            <RankRow
              key={`b-${r.team}`}
              rank={i + 1}
              team={r.team}
              count={r.count}
              sec={r.sec}
              max={maxSec}
              color={MEDAL_COLORS[i]}
              mode="best"
              prevRank={prev?.rank}
              prevSec={prev?.sec}
            />
          );
        })}
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: "#ececef", margin: "4px 14px" }} />

      {/* Worst section */}
      <div style={{ padding: "10px 14px 14px" }}>
        <SectionLabel
          symbol="▼"
          symbolColor="#E74C3C"
          text="TOP 3 — ต้องปรับปรุง (ช้าที่สุด)"
          textColor="#9c2a18"
        />
        {slowest.map((r, i) => {
          const prev = prevSlowest.get(r.team);
          return (
            <RankRow
              key={`w-${r.team}`}
              rank={i + 1}
              team={r.team}
              count={r.count}
              sec={r.sec}
              max={maxSec}
              color={WORST_COLORS[i]}
              mode="worst"
              prevRank={prev?.rank}
              prevSec={prev?.sec}
            />
          );
        })}
      </div>
    </div>
  );
}

export default function Page21({ records }) {
  const f = useFilters();
  const co = useCompany();
  const teams = co.allFilterTeams;
  const [prevStart, prevEnd] = useMemo(() => prevMonthRange(f.end), [f.end]);

  const filtered = useMemo(() => applyFilters(records, f), [records, f]);
  const prevFiltered = useMemo(
    () => applyFilters(records, { ...f, start: prevStart, end: prevEnd }),
    [records, f, prevStart, prevEnd]
  );

  const departToOnsite = useMemo(() => teamAvgFor(filtered, teams, "do"), [filtered, teams]);
  const onsiteToDone = useMemo(() => teamAvgFor(filtered, teams, "od"), [filtered, teams]);
  const prevDepartToOnsite = useMemo(() => teamAvgFor(prevFiltered, teams, "do"), [prevFiltered, teams]);
  const prevOnsiteToDone = useMemo(() => teamAvgFor(prevFiltered, teams, "od"), [prevFiltered, teams]);

  const avg = (items) => mean(items.map((x) => x.sec));

  return (
    <div>
      <PageHeader
        title="Average Overall Ranking of Team"
        subtitle={`เทียบ ${prevStart}…${prevEnd} กับ ${f.start}…${f.end} · ${departToOnsite.length} ทีมที่มีงานในช่วงนี้`}
      />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        <RankingCard
          label="Depart → Onsite"
          sublabel="ระยะเวลาเดินทาง"
          items={departToOnsite}
          prevItems={prevDepartToOnsite}
          average={avg(departToOnsite)}
        />
        <RankingCard
          label="Onsite → Done"
          sublabel="ระยะเวลาทำงานหน้างาน"
          items={onsiteToDone}
          prevItems={prevOnsiteToDone}
          average={avg(onsiteToDone)}
        />
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
          textAlign: "center",
          display: "flex",
          flexWrap: "wrap",
          gap: 14,
          justifyContent: "center",
        }}
      >
        <span>
          <span style={{ color: "#27AE60", fontWeight: 800, marginRight: 4 }}>▲</span>
          เร็วที่สุด = เหรียญทอง/เงิน/ทองแดง ·
          <span style={{ color: "#E74C3C", fontWeight: 800, margin: "0 4px" }}>▼</span>
          ช้าที่สุด = สีตามระดับ
        </span>
        <span>·</span>
        <span>
          <span style={{ color: "#27AE60", fontWeight: 700, marginRight: 3 }}>▲ N</span>
          อันดับดีขึ้น N ตำแหน่งเทียบเดือนก่อน ·
          <span style={{ color: "#E74C3C", fontWeight: 700, margin: "0 3px" }}>▼ N</span>
          แย่ลง ·
          <span style={{ color: "#888", fontWeight: 700, margin: "0 3px" }}>—</span>
          เท่าเดิม ·
          <span style={{ color: "#aaa", fontWeight: 600, marginLeft: 3 }}>NEW</span>
          ไม่มีข้อมูลเดือนก่อน
        </span>
      </div>
    </div>
  );
}

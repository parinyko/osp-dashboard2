import React, { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList } from "recharts";
import PageHeader from "../components/PageHeader.jsx";
import ChartCard from "../components/ChartCard.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { useCompany } from "../company.jsx";
import { MONTHS_EN, SLA_PRIORITIES, TEAM_PALETTE, pick } from "../theme.js";
import { lastSixMonths, monthKey, pct } from "../utils.js";

// Value labels on every dot only stay readable for a handful of lines.
const MAX_LABELLED_TEAMS = 4;

function buildSeries(records, months, teams, kind) {
  return months.map((mk) => {
    const [, m] = mk.split("-").map(Number);
    const row = { mk, month: MONTHS_EN[m - 1] };
    for (const t of teams) {
      const recs = records.filter((r) => monthKey(r.d) === mk && r.t === t);
      // A month without Critical/Major jobs has no SLA — leave a gap, not 0%.
      if (!recs.length) {
        row[t] = null;
        continue;
      }
      const v =
        kind === "before"
          ? pct(recs.filter((r) => r.bw === "In Due").length, recs.length)
          : pct(recs.filter((r) => r.aw === "Pass").length, recs.length);
      row[t] = +v.toFixed(2);
    }
    return row;
  });
}

// Offset each team's label around its dot so three close lines don't collide.
function makeTeamLabel(teamIndex, color) {
  return function TeamLabel({ x, y, value }) {
    if (value == null || x == null || y == null) return null;
    const offsets = [
      { dx: 8, dy: -8, anchor: "start" },
      { dx: 6, dy: 18, anchor: "start" },
      { dx: -8, dy: -8, anchor: "end" },
      { dx: -6, dy: 18, anchor: "end" },
    ];
    const o = offsets[teamIndex % offsets.length];
    return (
      <text x={x + o.dx} y={y + o.dy} fill={color} fontSize={11} fontWeight={700} textAnchor={o.anchor}>
        {Number(value).toFixed(2)}%
      </text>
    );
  };
}

function TeamLineChart({ data, teams, label }) {
  const labelled = teams.length <= MAX_LABELLED_TEAMS;
  return (
    <ChartCard title={`SLA% Performance ${label} Per team`}>
      <div style={{ padding: "4px 8px", fontSize: 11, color: "#555", display: "flex", flexWrap: "wrap", columnGap: 10, rowGap: 4 }}>
        <strong>ASSIGN_TO</strong>
        {teams.map((t, i) => (
          <span key={t} style={{ color: pick(TEAM_PALETTE, i), fontWeight: 600, whiteSpace: "nowrap" }}>
            ● <span style={{ color: "#333" }}>{t}</span>
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={labelled ? 280 : 320}>
        <LineChart data={data} margin={{ top: 36, right: 36, left: 10, bottom: 28 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: "#444", fontSize: 12 }} axisLine={{ stroke: "#bbb" }} tickLine={false} />
          <YAxis domain={[0, 115]} ticks={[0, 20, 40, 60, 80, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "#888", fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: "#fff", border: "1px solid #ddd", borderRadius: 6 }}
            formatter={(v) => (v == null ? "—" : `${v}%`)}
            itemSorter={(item) => -(item.value ?? -1)}
          />
          {teams.map((t, i) => {
            const color = pick(TEAM_PALETTE, i);
            return (
              <Line key={t} type="linear" dataKey={t} stroke={color} strokeWidth={labelled ? 2.5 : 1.8} dot={{ fill: color, r: labelled ? 4 : 3 }} isAnimationActive={false}>
                {labelled && <LabelList dataKey={t} content={makeTeamLabel(i, color)} />}
              </Line>
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default function SlaPerTeamPage({ records, zone }) {
  const f = useFilters();
  const co = useCompany();
  const months = useMemo(() => lastSixMonths(f.end), [f.end]);
  const filtered = useMemo(
    () =>
      applyFilters(records, f, ["date", "zone", "team", "priority"])
        .filter((r) => r.z === zone)
        .filter((r) => SLA_PRIORITIES.has(r.p)),
    [records, f, zone]
  );
  // Teams with at least one SLA job in the six-month window.
  const teams = useMemo(() => {
    const seen = new Set(filtered.filter((r) => months.includes(monthKey(r.d))).map((r) => r.t));
    return co.teamsByZone[zone].filter((t) => seen.has(t));
  }, [filtered, months, co, zone]);
  const beforeSeries = useMemo(() => buildSeries(filtered, months, teams, "before"), [filtered, months, teams]);
  const afterSeries = useMemo(() => buildSeries(filtered, months, teams, "after"), [filtered, months, teams]);

  return (
    <div>
      <PageHeader
        title={`SLA% Performance ${zone}`}
        subtitle={`Before & After per team — 6 เดือนสิ้นสุด ${f.end} · ใช้เฉพาะงาน Priority Critical + Major`}
      />
      {teams.length === 0 ? (
        <div style={{ background: "#fff", borderRadius: 12, padding: 40, textAlign: "center", color: "#999" }}>
          ไม่มีงาน Critical / Major ในโซนนี้ช่วง 6 เดือนที่ผ่านมา
        </div>
      ) : (
        <div style={{ display: "grid", gap: 16 }}>
          <TeamLineChart data={beforeSeries} teams={teams} label="Before" />
          <TeamLineChart data={afterSeries} teams={teams} label="After" />
        </div>
      )}
    </div>
  );
}

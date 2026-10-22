import React, { useMemo } from "react";
import PageHeader from "../components/PageHeader.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { COLORS } from "../theme.js";
import { mean, formatSeconds, prevMonthRange } from "../utils.js";

const PRIORITIES = ["Critical", "Major", "Minor"];

// Color thresholds (in seconds).
const THRESHOLDS = {
  accept_to_depart: 5 * 60, // 5 minutes
  depart_to_onsite: 45 * 60, // 45 minutes
  onsite_to_done: 2 * 60 * 60, // 2 hours
};

const THRESHOLD_LABEL = {
  accept_to_depart: "5 นาที",
  depart_to_onsite: "45 นาที",
  onsite_to_done: "2 ชั่วโมง",
};

const METRICS = [
  { key: "accept_to_depart", label: "Accept → Depart" },
  { key: "depart_to_onsite", label: "Depart → Onsite" },
  { key: "onsite_to_done", label: "Onsite → Done" },
];

function avgForPriority(records, priority) {
  const recs = records.filter((r) => r.p === priority);
  return {
    accept_to_depart: mean(recs.map((r) => r.ad)),
    depart_to_onsite: mean(recs.map((r) => r.do)),
    onsite_to_done: mean(recs.map((r) => r.od)),
    count: recs.length,
  };
}

function trendInfo(currentSec, prevSec) {
  if (currentSec == null || prevSec == null) return null;
  const diff = currentSec - prevSec;
  if (Math.abs(diff) < 1) return { dir: "flat", pct: 0 };
  const pct = prevSec > 0 ? (diff / prevSec) * 100 : 0;
  return { dir: diff > 0 ? "up" : "down", pct: Math.abs(pct), diff };
}

function MetricRow({ metric, current, prev }) {
  const threshold = THRESHOLDS[metric.key];
  const curSec = current[metric.key];
  const prevSec = prev[metric.key];
  const over = (sec) => sec != null && sec > threshold;
  const colorPrev = over(prevSec) ? "#E74C3C" : "#6b6b78";
  const colorCur = over(curSec) ? "#E74C3C" : "#2563EB";
  const t = trendInfo(curSec, prevSec);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 90px 90px 50px",
        alignItems: "center",
        padding: "10px 12px",
        background: "#f7f7fa",
        borderRadius: 8,
        marginBottom: 6,
        fontSize: 13,
        fontWeight: 600,
        columnGap: 6,
      }}
    >
      <div style={{ color: "#1f1f2c" }}>
        {metric.label}
        <div style={{ fontSize: 10, color: "#9a9aaf", fontWeight: 400, marginTop: 2 }}>
          เกณฑ์ &gt; {THRESHOLD_LABEL[metric.key]}
        </div>
      </div>
      <div style={{ textAlign: "right", color: colorPrev, fontFamily: "DM Mono, monospace", fontSize: 14 }}>
        {formatSeconds(prevSec)}
      </div>
      <div style={{ textAlign: "right", color: colorCur, fontFamily: "DM Mono, monospace", fontSize: 14, fontWeight: 700 }}>
        {formatSeconds(curSec)}
      </div>
      <div style={{ textAlign: "right", fontSize: 11 }}>
        {t ? (
          <span
            style={{
              color: t.dir === "up" ? "#E74C3C" : t.dir === "down" ? "#27AE60" : "#999",
              fontWeight: 700,
            }}
          >
            {t.dir === "up" ? "▲" : t.dir === "down" ? "▼" : "—"} {t.pct.toFixed(0)}%
          </span>
        ) : (
          <span style={{ color: "#ccc" }}>—</span>
        )}
      </div>
    </div>
  );
}

function PriorityCard({ name, current, prev, prevMonth, curMonth }) {
  const accent = COLORS.priority[name];
  return (
    <div
      style={{
        background: "#fff",
        borderRadius: 14,
        overflow: "hidden",
        boxShadow: "0 6px 16px rgba(0,0,0,0.08)",
        border: "1px solid #ececef",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header strip — priority color */}
      <div
        style={{
          background: `linear-gradient(135deg, ${accent} 0%, ${accent}dd 100%)`,
          color: "#fff",
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div style={{ fontSize: 11, opacity: 0.85, fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
            Priority
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, marginTop: 2 }}>{name}</div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, opacity: 0.95 }}>
          <div>{current.count.toLocaleString()} jobs</div>
          <div style={{ opacity: 0.75, marginTop: 2 }}>vs {prev.count.toLocaleString()} เดือนก่อน</div>
        </div>
      </div>

      {/* Column headers */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 90px 90px 50px",
          padding: "8px 12px 4px",
          fontSize: 10,
          color: "#8b8b96",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          fontWeight: 700,
          columnGap: 6,
        }}
      >
        <div>ขั้นตอน</div>
        <div style={{ textAlign: "right" }}>{prevMonth}</div>
        <div style={{ textAlign: "right", color: "#2563EB" }}>{curMonth}</div>
        <div style={{ textAlign: "right" }}>Δ</div>
      </div>

      {/* Metric rows */}
      <div style={{ padding: "0 12px 14px" }}>
        {METRICS.map((m) => (
          <MetricRow key={m.key} metric={m} current={current} prev={prev} />
        ))}
      </div>
    </div>
  );
}

export default function AvgDurationPage({ records, zone }) {
  const f = useFilters();
  const [prevStart, prevEnd] = useMemo(() => prevMonthRange(f.end), [f.end]);

  const currentRecs = useMemo(
    () => applyFilters(records, f, ["zone"]).filter((r) => r.z === zone),
    [records, f, zone]
  );
  const prevRecs = useMemo(
    () =>
      applyFilters(records, { ...f, start: prevStart, end: prevEnd }, ["zone"]).filter((r) => r.z === zone),
    [records, f, prevStart, prevEnd, zone]
  );

  const prevMonth = prevStart.slice(0, 7);
  const curMonth = f.start.slice(0, 7) === f.end.slice(0, 7) ? f.start.slice(0, 7) : `${f.start.slice(0, 7)} → ${f.end.slice(0, 7)}`;

  const cards = PRIORITIES.map((p) => ({
    name: p,
    current: avgForPriority(currentRecs, p),
    prev: avgForPriority(prevRecs, p),
  }));

  return (
    <div>
      <PageHeader
        title={`Average Overall Working Duration — ${zone}`}
        subtitle={`เทียบ ${prevStart}…${prevEnd} กับ ${f.start}…${f.end}`}
      />
      <div
        style={{
          background: "#fff",
          border: "1px solid #e6e6ea",
          borderRadius: 12,
          padding: 24,
          boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
        }}
      >
        <div
          style={{
            fontSize: 18,
            fontWeight: 700,
            marginBottom: 18,
            color: "#1f1f2c",
            textAlign: "center",
          }}
        >
          📊 Average Overall Working Duration of <span style={{ textDecoration: "underline" }}>{zone}</span> Zone
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          {cards.map((c) => (
            <PriorityCard
              key={c.name}
              {...c}
              prevMonth={prevMonth}
              curMonth={curMonth}
            />
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
            gap: 14,
            justifyContent: "center",
          }}
        >
          <span>
            <span style={{ display: "inline-block", width: 10, height: 10, background: "#6b6b78", borderRadius: 2, marginRight: 5, verticalAlign: "middle" }} />
            เดือนก่อน
          </span>
          <span>
            <span style={{ display: "inline-block", width: 10, height: 10, background: "#2563EB", borderRadius: 2, marginRight: 5, verticalAlign: "middle" }} />
            ช่วงที่เลือก
          </span>
          <span>
            <span style={{ display: "inline-block", width: 10, height: 10, background: "#E74C3C", borderRadius: 2, marginRight: 5, verticalAlign: "middle" }} />
            เกินเกณฑ์ (Accept→Depart &gt; 5น · Depart→Onsite &gt; 45น · Onsite→Done &gt; 2 ชม.)
          </span>
          <span>
            <span style={{ color: "#E74C3C", fontWeight: 700, marginRight: 3 }}>▲</span>
            แย่ลง vs เดือนก่อน ·
            <span style={{ color: "#27AE60", fontWeight: 700, margin: "0 3px" }}>▼</span>
            ดีขึ้น
          </span>
        </div>
      </div>
    </div>
  );
}

import React, { useEffect, useMemo, useRef, useState } from "react";
import PageHeader from "../components/PageHeader.jsx";
import { useFilters, applyFilters } from "../filters.jsx";
import { useCompany } from "../company.jsx";
import { COLORS, PRIORITY_ORDER } from "../theme.js";
import { addDaysISO, usePersistedState } from "../utils.js";

// Threshold (in seconds) for each stage SLA — supplied by the user
const TH_ACCEPT_S = 5 * 60;        // assign → accept  ≤ 5 min
const TH_TRAVEL_S = 45 * 60;       // initiate → onsite ≤ 45 min
const TH_WORK_S = 2 * 60 * 60;     // onsite → report  ≤ 2 hr

const PRIORITY_COLOR = COLORS.priority;
const ROW_H = 24;            // px per lane
const BAR_H = 16;
const PAD_TOP = 50;          // top of chart area (below time axis)
const LEFT_W = 200;          // left label column width
const HOUR_PX_DEFAULT = 30;  // pixels per hour at default zoom

function parseTs(s) {
  if (!s) return null;
  const t = Date.parse(s);
  return Number.isFinite(t) ? t : null;
}

function diffSec(aIso, bIso) {
  const a = parseTs(aIso), b = parseTs(bIso);
  if (a == null || b == null) return null;
  return Math.round((b - a) / 1000);
}

function fmtDur(sec) {
  if (sec == null) return "—";
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  return `${m}m`;
}

function fmtClock(iso) {
  if (!iso) return "—";
  return iso.slice(11, 16); // HH:MM
}

function fmtDateClock(iso) {
  if (!iso) return "—";
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)}`;
}

// Greedy lane packing: assign each interval to the lowest non-overlapping lane.
function packLanes(items) {
  const sorted = [...items].sort((a, b) => a.start - b.start);
  const laneEnds = []; // end-time of each lane
  for (const it of sorted) {
    let placed = false;
    for (let i = 0; i < laneEnds.length; i++) {
      if (laneEnds[i] <= it.start) {
        it.lane = i;
        laneEnds[i] = it.end;
        placed = true;
        break;
      }
    }
    if (!placed) {
      it.lane = laneEnds.length;
      laneEnds.push(it.end);
    }
  }
  return { items: sorted, laneCount: laneEnds.length || 1 };
}

function computeIndicators(r) {
  // Each indicator: { key, label, ok, value, hint }
  const acceptS = diffSec(r.gt, r.at);
  const travelS = diffSec(r.it, r.nt);
  const workS = diffSec(r.nt, r.rt);
  return {
    accept: {
      ok: acceptS != null && acceptS <= TH_ACCEPT_S,
      seconds: acceptS,
      label: "Accept ≤ 5m",
    },
    travel: {
      ok: travelS != null && travelS <= TH_TRAVEL_S,
      seconds: travelS,
      label: "Travel ≤ 45m",
    },
    work: {
      ok: workS != null && workS <= TH_WORK_S,
      seconds: workS,
      label: "Work ≤ 2h",
    },
  };
}

export default function DashJobGantt({ records }) {
  const f = useFilters();
  const co = useCompany();
  const [groupBy, setGroupBy] = usePersistedState("osp.gantt.groupBy", "team");
  const [hoverId, setHoverId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [zoom, setZoom] = usePersistedState("osp.gantt.zoom", 1);
  const [search, setSearch] = useState("");
  const [searchMsg, setSearchMsg] = useState(null); // {type: "ok"|"err", text}
  const [flashJb, setFlashJb] = useState(null);
  const [containerW, setContainerW] = useState(0);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const scrollRef = useRef(null);
  // Pending scroll target — set on successful search; consumed by effect after layout.
  const pendingScrollRef = useRef(null);

  // Observe the scroll container width so the chart stretches to fill the page
  // when zoomed-out content would otherwise leave empty space on the right.
  useEffect(() => {
    if (!scrollRef.current || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width;
      if (w) setContainerW(w);
    });
    ro.observe(scrollRef.current);
    return () => ro.disconnect();
  }, []);

  // Local date range — independent from global FilterBar.
  // Default: most-recent single day available in the data.
  const dataMaxDate = useMemo(() => {
    let max = "";
    for (const r of records) if (r.d && r.d > max) max = r.d;
    return max || f.dateMax || f.end;
  }, [records, f.dateMax, f.end]);
  const dataMinDate = useMemo(() => {
    let min = "";
    for (const r of records) if (r.d && (!min || r.d < min)) min = r.d;
    return min || f.dateMin || f.start;
  }, [records, f.dateMin, f.start]);

  const [localStart, setLocalStart] = usePersistedState(
    `osp.gantt.${co.slug}.start`,
    dataMaxDate
  );
  const [localEnd, setLocalEnd] = usePersistedState(
    `osp.gantt.${co.slug}.end`,
    dataMaxDate
  );

  // If data window shifts (e.g., after upload), nudge local range to stay valid.
  useEffect(() => {
    if (localEnd > dataMaxDate) setLocalEnd(dataMaxDate);
    if (localStart > dataMaxDate) setLocalStart(dataMaxDate);
    if (localStart < dataMinDate) setLocalStart(dataMinDate);
  }, [dataMinDate, dataMaxDate]); // eslint-disable-line react-hooks/exhaustive-deps

  // Build an override filter so the rest of the page still respects zone/team/priority
  // from the global FilterBar — only the date range is local.
  const localFilter = useMemo(
    () => ({ ...f, start: localStart, end: localEnd }),
    [f, localStart, localEnd]
  );

  // Filter + restrict to records with both accept + report timestamps
  const visible = useMemo(() => {
    const filtered = applyFilters(records, localFilter);
    return filtered.filter((r) => r.at && r.rt);
  }, [records, localFilter]);

  // Time domain — from local date range
  const [tMin, tMax] = useMemo(() => {
    const start = new Date(`${localStart}T00:00:00`).getTime();
    const end = new Date(`${localEnd}T23:59:59`).getTime();
    return [start, end];
  }, [localStart, localEnd]);

  const applyPreset = (days) => {
    // days = 1 → single most-recent day; otherwise N days ending at dataMaxDate
    const end = dataMaxDate;
    const start = addDaysISO(end, -(days - 1));
    setLocalStart(start < dataMinDate ? dataMinDate : start);
    setLocalEnd(end);
  };

  // Search JB_ID across ALL records (not just visible) — substring, case-insensitive.
  const handleSearch = (rawQ) => {
    const q = (rawQ ?? search).trim().toLowerCase();
    setSearchMsg(null);
    if (!q) {
      setFlashJb(null);
      return;
    }
    const matches = [];
    for (const r of records) {
      if (!r.jb || !r.at || !r.rt) continue;
      const jb = r.jb.toLowerCase();
      if (jb === q || jb.includes(q)) {
        matches.push(r);
        if (matches.length >= 50) break; // cap to keep things snappy
      }
    }
    if (matches.length === 0) {
      setFlashJb(null);
      setSearchMsg({ type: "err", text: `ไม่พบ JB ที่ตรงกับ "${rawQ ?? search}"` });
      return;
    }
    const r = matches[0];
    // Snap local date range to that job's day so the bar is visible.
    const day = r.d;
    setLocalStart(day);
    setLocalEnd(day);
    setFlashJb(r.jb);
    pendingScrollRef.current = r.jb;
    setSearchMsg({
      type: "ok",
      text:
        matches.length === 1
          ? `พบ: ${r.jb} (${r.t || r.a}) · ${r.d}`
          : `พบ ${matches.length} รายการ — กระโดดไปอันแรก: ${r.jb} (${r.d})`,
    });
  };

  // After re-render (when dates/zoom change), scroll the matched bar into view.
  useEffect(() => {
    const target = pendingScrollRef.current;
    if (!target || !scrollRef.current) return;
    // Two RAFs: wait one frame for React to commit, another for layout to settle.
    const id = requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        const el = scrollRef.current?.querySelector(
          `[data-jb="${CSS.escape(target)}"]`
        );
        if (el && scrollRef.current) {
          const barRect = el.getBoundingClientRect();
          const contRect = scrollRef.current.getBoundingClientRect();
          scrollRef.current.scrollLeft +=
            barRect.left - contRect.left - contRect.width / 2 + barRect.width / 2;
          scrollRef.current.scrollTop +=
            barRect.top - contRect.top - contRect.height / 2 + barRect.height / 2;
        }
        pendingScrollRef.current = null;
      })
    );
    return () => cancelAnimationFrame(id);
  }, [flashJb, localStart, localEnd, zoom, groupBy]);

  // Auto-fade the highlight after a few seconds.
  useEffect(() => {
    if (!flashJb) return;
    const t = setTimeout(() => setFlashJb(null), 6000);
    return () => clearTimeout(t);
  }, [flashJb]);

  const durationHours = Math.max(1, (tMax - tMin) / 3600000);
  // Default px/hour tuned for the most-used 1–2 day views — dense enough to read
  // hourly (or 30-min when zoomed once). Wider ranges fall back to coarser density.
  const autoHourPx = durationHours <= 24 ? 56 : durationHours <= 48 ? 32 : durationHours <= 168 ? 18 : 5;
  const wantedHourPx = autoHourPx * zoom;
  // Stretch the chart to fill available container width if the wanted size is smaller.
  const minChartW = Math.max(600, containerW - LEFT_W - 2);
  const wantedChartW = Math.round(durationHours * wantedHourPx);
  const chartW = Math.max(minChartW, wantedChartW);
  // Effective px/hour after the stretch — used for tick density.
  const hourPx = chartW / durationHours;

  // Group + pack
  const groups = useMemo(() => {
    const map = new Map();
    for (const r of visible) {
      const key =
        groupBy === "none"
          ? "(ทั้งหมด)"
          : groupBy === "team"
          ? r.t || "(ไม่ระบุทีม)"
          : r.a || "(ไม่ระบุ assignee)";
      if (!map.has(key)) map.set(key, []);
      const start = parseTs(r.at);
      const end = parseTs(r.rt);
      if (start == null || end == null || end < start) continue;
      map.get(key).push({
        r,
        start,
        end: Math.max(end, start + 60_000), // ensure visible width
      });
    }
    const arr = Array.from(map.entries()).map(([name, items]) => {
      const packed = packLanes(items);
      return { name, items: packed.items, laneCount: packed.laneCount };
    });
    arr.sort((a, b) => a.name.localeCompare(b.name));
    return arr;
  }, [visible, groupBy]);

  // Layout
  const groupGap = 6;
  const labelH = 22;
  const groupHeights = groups.map(
    (g) => labelH + g.laneCount * ROW_H + groupGap
  );
  const totalH = PAD_TOP + groupHeights.reduce((a, b) => a + b, 0) + 30;
  const groupOffsets = [];
  {
    let y = PAD_TOP;
    for (let i = 0; i < groups.length; i++) {
      groupOffsets.push(y);
      y += groupHeights[i];
    }
  }

  // X scale
  const xOf = (ms) => LEFT_W + ((ms - tMin) / (tMax - tMin)) * chartW;
  const widthOf = (ms) => Math.max(2, (ms / (tMax - tMin)) * chartW);

  // Time ticks — step adapts to current px/hour so labels never overlap.
  // Labels are HH:MM by default; midnight ticks in multi-day view show DD/MM
  // instead (acts as a day separator label).
  const ticks = useMemo(() => {
    const out = [];
    const HOUR = 3600000;
    // All non-midnight labels are HH:MM (~36px). Midnight DD/MM (~38px).
    // Both fit comfortably in 38–42px.
    const MIN_PX = 40;
    let stepMs;
    if (hourPx * 0.25 >= MIN_PX) stepMs = 0.25 * HOUR;       // 15 min
    else if (hourPx * 0.5 >= MIN_PX) stepMs = 0.5 * HOUR;    // 30 min
    else if (hourPx >= MIN_PX) stepMs = HOUR;                 // 1 h
    else if (hourPx * 2 >= MIN_PX) stepMs = 2 * HOUR;
    else if (hourPx * 3 >= MIN_PX) stepMs = 3 * HOUR;
    else if (hourPx * 6 >= MIN_PX) stepMs = 6 * HOUR;
    else if (hourPx * 12 >= MIN_PX) stepMs = 12 * HOUR;
    else stepMs = 24 * HOUR;

    // Start from local midnight of tMin so day boundaries align with local clock.
    const start = new Date(tMin);
    start.setHours(0, 0, 0, 0);
    let t0 = start.getTime();
    while (t0 + stepMs <= tMin) t0 += stepMs;

    const multiDay = durationHours > 24;
    for (let t = t0; t <= tMax; t += stepMs) {
      const d = new Date(t);
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      const mo = String(d.getMonth() + 1).padStart(2, "0");
      const isMidnight = d.getHours() === 0 && d.getMinutes() === 0;
      let label, isDayLabel = false;
      if (stepMs >= 24 * HOUR) {
        label = `${day}/${mo}`;
        isDayLabel = true;
      } else if (multiDay && isMidnight) {
        label = `${day}/${mo}`;
        isDayLabel = true;
      } else {
        label = `${hh}:${mm}`;
      }
      out.push({ t, label, isDayLabel });
    }
    return out;
  }, [tMin, tMax, durationHours, hourPx]);

  const totalJobs = visible.length;
  const cappedNotice = totalJobs > 1500;

  return (
    <div style={{ color: "#1f1f2c" }}>
      <PageHeader
        title="Job Timeline (Gantt)"
        subtitle="ไทม์ไลน์งานจริง · accept → report · สีตาม priority · เครื่องหมายตาม SLA แต่ละ stage"
      />

      {/* Controls */}
      <div style={controlBar}>
        <div>
          <div style={ctrlLabel}>ช่วงวันที่ (เฉพาะหน้านี้)</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input
              type="date"
              value={localStart}
              min={dataMinDate}
              max={localEnd}
              onChange={(e) => setLocalStart(e.target.value)}
              style={dateInput}
            />
            <span style={{ color: "#8b8b96" }}>—</span>
            <input
              type="date"
              value={localEnd}
              min={localStart}
              max={dataMaxDate}
              onChange={(e) => setLocalEnd(e.target.value)}
              style={dateInput}
            />
          </div>
          <div style={{ fontSize: 10, color: "#aaa", marginTop: 3 }}>
            ตัวกรองนี้ไม่กระทบหน้าอื่น · zone/team/priority ใช้จาก filter ด้านบน
          </div>
        </div>

        <div>
          <div style={ctrlLabel}>เลือกเร็ว</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button onClick={() => applyPreset(1)} style={chip(localStart === localEnd && localEnd === dataMaxDate)}>
              วันล่าสุด
            </button>
            <button onClick={() => applyPreset(7)} style={chip(false)}>7 วัน</button>
            <button onClick={() => applyPreset(30)} style={chip(false)}>30 วัน</button>
          </div>
        </div>

        <div>
          <div style={ctrlLabel}>จัดกลุ่ม</div>
          <div style={{ display: "flex", gap: 6 }}>
            {[
              ["none", "ไม่จัดกลุ่ม"],
              ["team", "ตามทีม"],
              ["assignee", "ตาม ASSIGN_TO"],
            ].map(([k, l]) => (
              <button
                key={k}
                onClick={() => setGroupBy(k)}
                style={chip(groupBy === k)}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div style={ctrlLabel}>Zoom</div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <button
              onClick={() => setZoom((z) => Math.max(0.25, +(z / 1.5).toFixed(3)))}
              style={iconBtn}
              title="Zoom out"
            >
              −
            </button>
            <button
              onClick={() => setZoom(1)}
              style={{ ...iconBtn, minWidth: 56, fontSize: 11, fontWeight: 600 }}
              title="Reset zoom (fit)"
            >
              {Math.round(zoom * 100)}%
            </button>
            <button
              onClick={() => setZoom((z) => Math.min(20, +(z * 1.5).toFixed(3)))}
              style={iconBtn}
              title="Zoom in"
            >
              +
            </button>
          </div>
        </div>

        <div>
          <div style={ctrlLabel}>ค้นหา JB_ID</div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSearch();
            }}
            style={{ display: "flex", gap: 4 }}
          >
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="เช่น JB26-0001234"
              style={{ ...dateInput, width: 180 }}
            />
            <button type="submit" style={searchBtn} title="ค้นหา + กระโดดไปแท่ง">
              🔍
            </button>
            {search && (
              <button
                type="button"
                onClick={() => {
                  setSearch("");
                  setSearchMsg(null);
                  setFlashJb(null);
                }}
                style={iconBtn}
                title="เคลียร์"
              >
                ✕
              </button>
            )}
          </form>
          {searchMsg && (
            <div
              style={{
                fontSize: 10,
                marginTop: 3,
                color: searchMsg.type === "ok" ? "#1d6b3a" : "#9c2a18",
              }}
            >
              {searchMsg.text}
            </div>
          )}
        </div>

        <div style={{ marginLeft: "auto", fontSize: 12, color: "#666", textAlign: "right" }}>
          {totalJobs.toLocaleString()} jobs · {groups.length}{" "}
          {groupBy === "none" ? "row" : "group"}
          <div style={{ fontSize: 10, color: "#aaa", marginTop: 2 }}>
            {localStart} → {localEnd} · {Math.round(hourPx)} px/hr
          </div>
        </div>
      </div>

      {/* Legend */}
      <div style={legendRow}>
        <span style={legendTitle}>Priority:</span>
        {PRIORITY_ORDER.map((p) => (
          <span key={p} style={legendItem}>
            <span style={{ ...swatch, background: PRIORITY_COLOR[p] }} />
            {p}
          </span>
        ))}
        <span style={{ ...legendTitle, marginLeft: 14 }}>SLA stage:</span>
        <span style={legendItem}>
          <span style={{ ...dot, background: "#27AE60" }} />
          ผ่าน
        </span>
        <span style={legendItem}>
          <span style={{ ...dot, background: "#E74C3C" }} />
          เกิน
        </span>
        <span style={{ ...legendTitle, marginLeft: 14 }}>กรอบ:</span>
        <span style={legendItem}>
          <span style={{ ...swatchOutline, borderStyle: "solid" }} /> In Due
        </span>
        <span style={legendItem}>
          <span style={{ ...swatchOutline, borderStyle: "dashed" }} /> Out Due
        </span>
      </div>

      {cappedNotice && (
        <div style={warn}>
          ⚠ มี {totalJobs.toLocaleString()} jobs ในช่วงที่เลือก — Gantt อาจ render ช้า
          แนะนำให้ย่อช่วงวันที่ใน Filter ด้านบน
        </div>
      )}

      {/* Gantt SVG */}
      {visible.length === 0 ? (
        <div style={emptyBox}>ไม่มีข้อมูลในช่วงที่เลือก</div>
      ) : (
        <div
          ref={scrollRef}
          style={{
            background: "#fff",
            borderRadius: 10,
            border: "1px solid #e6e6ea",
            overflow: "auto",
            maxHeight: "70vh",
            position: "relative",
          }}
        >
          <svg
            width={LEFT_W + chartW}
            height={totalH}
            style={{ display: "block", fontFamily: "inherit", fontSize: 11 }}
          >
            {/* Time axis */}
            <g>
              <rect x={0} y={0} width={LEFT_W + chartW} height={PAD_TOP} fill="#fafafc" />
              {ticks.map((tk, i) => (
                <g key={i}>
                  <line
                    x1={xOf(tk.t)}
                    y1={PAD_TOP - 6}
                    x2={xOf(tk.t)}
                    y2={totalH}
                    stroke={tk.isDayLabel ? "#c4ccd6" : "#eee"}
                    strokeWidth={tk.isDayLabel ? 1.2 : 1}
                  />
                  <text
                    x={xOf(tk.t)}
                    y={PAD_TOP - 12}
                    textAnchor="middle"
                    fill={tk.isDayLabel ? "#333" : "#666"}
                    fontWeight={tk.isDayLabel ? 700 : 400}
                  >
                    {tk.label}
                  </text>
                </g>
              ))}
              {/* day separators when >24h — align to local midnight */}
              {durationHours > 24 &&
                (() => {
                  const out = [];
                  const dayMs = 24 * 3600000;
                  const d0 = new Date(tMin);
                  d0.setHours(0, 0, 0, 0);
                  let t = d0.getTime();
                  while (t < tMin) t += dayMs;
                  for (; t <= tMax; t += dayMs) {
                    out.push(
                      <line
                        key={t}
                        x1={xOf(t)}
                        y1={0}
                        x2={xOf(t)}
                        y2={totalH}
                        stroke="#d0d6df"
                        strokeWidth={1.5}
                      />
                    );
                  }
                  return out;
                })()}
              {/* Left label column background */}
              <rect
                x={0}
                y={0}
                width={LEFT_W}
                height={totalH}
                fill="#ffffff"
              />
              <line x1={LEFT_W} y1={0} x2={LEFT_W} y2={totalH} stroke="#d0d6df" />
            </g>

            {/* Groups */}
            {groups.map((g, gi) => {
              const y0 = groupOffsets[gi];
              return (
                <g key={g.name}>
                  {/* Group label */}
                  <rect
                    x={0}
                    y={y0}
                    width={LEFT_W + chartW}
                    height={labelH}
                    fill="#f2f4f7"
                  />
                  <text
                    x={10}
                    y={y0 + labelH / 2 + 4}
                    fill="#333"
                    fontWeight={700}
                  >
                    {g.name}
                  </text>
                  <text
                    x={LEFT_W - 8}
                    y={y0 + labelH / 2 + 4}
                    textAnchor="end"
                    fill="#888"
                    fontSize={10}
                  >
                    {g.items.length} jobs · {g.laneCount} lane
                  </text>

                  {/* Bars */}
                  {g.items.map((it, ii) => {
                    const r = it.r;
                    const ind = computeIndicators(r);
                    const x = xOf(it.start);
                    const w = Math.max(2, xOf(it.end) - x);
                    const y = y0 + labelH + it.lane * ROW_H + (ROW_H - BAR_H) / 2;
                    const color = PRIORITY_COLOR[r.p] || "#888";
                    const inDue = r.bw === "In Due";
                    const key = r.jb || `${gi}-${ii}-${it.start}`;
                    const isHover = hoverId === key;
                    const isFlash = flashJb && r.jb === flashJb;
                    return (
                      <g
                        key={key}
                        data-jb={r.jb || ""}
                        onMouseEnter={(e) => {
                          setHoverId(key);
                          setMousePos({ x: e.clientX, y: e.clientY });
                        }}
                        onMouseMove={(e) =>
                          setMousePos({ x: e.clientX, y: e.clientY })
                        }
                        onMouseLeave={() => setHoverId(null)}
                        onClick={() => setSelected(r)}
                        style={{ cursor: "pointer" }}
                      >
                        {isFlash && (
                          <rect
                            x={x - 5}
                            y={y - 5}
                            width={w + 10}
                            height={BAR_H + 10}
                            rx={6}
                            fill="none"
                            stroke="#FFB300"
                            strokeWidth={2.5}
                            opacity={0.95}
                          >
                            <animate
                              attributeName="stroke-width"
                              values="2;4;2"
                              dur="1.2s"
                              repeatCount="indefinite"
                            />
                          </rect>
                        )}
                        <rect
                          x={x}
                          y={y}
                          width={w}
                          height={BAR_H}
                          rx={3}
                          fill={color}
                          opacity={isHover || isFlash ? 1 : 0.92}
                          stroke={inDue ? "#1d3d11" : "#9c2a18"}
                          strokeWidth={isHover ? 1.5 : 0.8}
                          strokeDasharray={inDue ? "0" : "3,2"}
                        />
                        {/* 3 SLA indicator dots inside bar (when wide enough) */}
                        {w >= 14 && (
                          <>
                            <circle
                              cx={x + 4}
                              cy={y + BAR_H / 2}
                              r={2.2}
                              fill={
                                ind.accept.seconds == null
                                  ? "rgba(255,255,255,0.4)"
                                  : ind.accept.ok
                                  ? "#27AE60"
                                  : "#E74C3C"
                              }
                              stroke="rgba(0,0,0,0.25)"
                              strokeWidth={0.4}
                            />
                            <circle
                              cx={x + w / 2}
                              cy={y + BAR_H / 2}
                              r={2.2}
                              fill={
                                ind.travel.seconds == null
                                  ? "rgba(255,255,255,0.4)"
                                  : ind.travel.ok
                                  ? "#27AE60"
                                  : "#E74C3C"
                              }
                              stroke="rgba(0,0,0,0.25)"
                              strokeWidth={0.4}
                            />
                            <circle
                              cx={x + w - 4}
                              cy={y + BAR_H / 2}
                              r={2.2}
                              fill={
                                ind.work.seconds == null
                                  ? "rgba(255,255,255,0.4)"
                                  : ind.work.ok
                                  ? "#27AE60"
                                  : "#E74C3C"
                              }
                              stroke="rgba(0,0,0,0.25)"
                              strokeWidth={0.4}
                            />
                          </>
                        )}
                        {/* JB_ID label inside bar (when wide enough) */}
                        {r.jb && w >= 70 && (
                          <text
                            x={x + 10}
                            y={y + BAR_H / 2 + 3.5}
                            fontSize={10}
                            fontWeight={600}
                            fill="rgba(0,0,0,0.78)"
                            style={{ pointerEvents: "none" }}
                          >
                            {w < 110 ? r.jb.replace(/^JB/, "") : r.jb}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </g>
              );
            })}
          </svg>

        </div>
      )}

      {/* Tooltip — fixed in viewport, follows the cursor */}
      {hoverId &&
        (() => {
          let job = null;
          for (const g of groups) {
            for (const it of g.items) {
              const k =
                it.r.jb ||
                `${groups.indexOf(g)}-${g.items.indexOf(it)}-${it.start}`;
              if (k === hoverId) {
                job = it.r;
                break;
              }
            }
            if (job) break;
          }
          if (!job) return null;
          const TT_W = 340;
          const TT_H = 200;
          const vw = typeof window !== "undefined" ? window.innerWidth : 1200;
          const vh = typeof window !== "undefined" ? window.innerHeight : 800;
          // Prefer below-right of cursor; flip if it would overflow.
          let left = mousePos.x + 16;
          let top = mousePos.y + 16;
          if (left + TT_W > vw - 8) left = mousePos.x - TT_W - 16;
          if (top + TT_H > vh - 8) top = mousePos.y - TT_H - 16;
          if (left < 8) left = 8;
          if (top < 8) top = 8;
          return (
            <div style={{ ...tooltipStyle, left, top }}>
              <GanttTooltip r={job} />
            </div>
          );
        })()}

      {selected && (
        <JobDetailModal r={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function StageRow({ label, from, to, threshold }) {
  const sec = diffSec(from, to);
  const ok = sec != null && sec <= threshold;
  const color = sec == null ? "#888" : ok ? "#27AE60" : "#E74C3C";
  return (
    <tr>
      <td style={{ padding: "2px 8px 2px 0", color: "#666" }}>{label}</td>
      <td style={{ padding: "2px 8px 2px 0", color: "#444" }}>
        {fmtClock(from)} → {fmtClock(to)}
      </td>
      <td style={{ padding: "2px 0", color, fontWeight: 600 }}>
        {fmtDur(sec)} {sec != null && (ok ? "✓" : "✗")}
      </td>
    </tr>
  );
}

function GanttTooltip({ r }) {
  return (
    <div style={{ fontSize: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 4 }}>
        {r.jb || "(no JB)"} · {r.p || "—"}
      </div>
      <div style={{ color: "#666", fontSize: 11, marginBottom: 4 }}>
        {r.t || r.a} · {fmtDateClock(r.at)} → {fmtClock(r.rt)}
      </div>
      <table>
        <tbody>
          <StageRow label="Accept" from={r.gt} to={r.at} threshold={TH_ACCEPT_S} />
          <StageRow label="Travel" from={r.it} to={r.nt} threshold={TH_TRAVEL_S} />
          <StageRow label="Work" from={r.nt} to={r.rt} threshold={TH_WORK_S} />
        </tbody>
      </table>
      <div style={{ marginTop: 4, fontSize: 11, color: r.bw === "In Due" ? "#1d6b3a" : "#9c2a18" }}>
        SLA: {r.bw || "—"} {r.aw ? `· ${r.aw}` : ""}
      </div>
    </div>
  );
}

function JobDetailModal({ r, onClose }) {
  return (
    <div onClick={onClose} style={modalOverlay}>
      <div onClick={(e) => e.stopPropagation()} style={modalBox}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 16, fontWeight: 800 }}>
            {r.jb || "(ไม่มี JB_ID)"}{" "}
            <span style={{ ...priorityBadge, background: PRIORITY_COLOR[r.p] || "#888" }}>
              {r.p || "—"}
            </span>
          </div>
          <button onClick={onClose} style={modalClose}>✕</button>
        </div>
        <div style={{ fontSize: 12, color: "#666", marginTop: 2 }}>
          {r.t || r.a} · {r.z} · {r.zid || ""}
        </div>
        <div style={{ marginTop: 12, fontSize: 12 }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              <tr><td style={tdLabel}>สร้างงาน (Create)</td><td style={tdVal}>{fmtDateClock(r.ct)}</td></tr>
              <tr><td style={tdLabel}>ส่งงาน (Assign)</td><td style={tdVal}>{fmtDateClock(r.gt)}</td></tr>
              <tr><td style={tdLabel}>รับงาน (Accept)</td><td style={tdVal}>{fmtDateClock(r.at)} · ⏱ {fmtDur(diffSec(r.gt, r.at))} {diffSec(r.gt, r.at) != null && (diffSec(r.gt, r.at) <= TH_ACCEPT_S ? "✓ ≤5m" : "✗ >5m")}</td></tr>
              <tr><td style={tdLabel}>เริ่มเดินทาง (Initiate)</td><td style={tdVal}>{fmtDateClock(r.it)}</td></tr>
              <tr><td style={tdLabel}>ถึงไซต์ (Onsite)</td><td style={tdVal}>{fmtDateClock(r.nt)} · ⏱ {fmtDur(diffSec(r.it, r.nt))} {diffSec(r.it, r.nt) != null && (diffSec(r.it, r.nt) <= TH_TRAVEL_S ? "✓ ≤45m" : "✗ >45m")}</td></tr>
              <tr><td style={tdLabel}>เสร็จงาน (Report)</td><td style={tdVal}>{fmtDateClock(r.rt)} · ⏱ {fmtDur(diffSec(r.nt, r.rt))} {diffSec(r.nt, r.rt) != null && (diffSec(r.nt, r.rt) <= TH_WORK_S ? "✓ ≤2h" : "✗ >2h")}</td></tr>
              <tr><td style={tdLabel}>SLA</td><td style={tdVal}>Before Waive: <b>{r.bw || "—"}</b> · After Waive: <b>{r.aw || "—"}</b></td></tr>
              {r.prb && <tr><td style={tdLabel}>Problem</td><td style={tdVal}>{r.prb}</td></tr>}
              {r.sol && <tr><td style={tdLabel}>Solution</td><td style={tdVal}>{r.sol}</td></tr>}
              {r.sc && <tr><td style={tdLabel}>SUBCAUSE2</td><td style={tdVal}>{r.sc}</td></tr>}
              {r.ro && <tr><td style={tdLabel}>สาเหตุ Overdue</td><td style={tdVal}>{r.ro}</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------- styles ----------
const controlBar = {
  display: "flex",
  gap: 16,
  alignItems: "flex-end",
  padding: "10px 14px",
  background: "#fff",
  border: "1px solid #e6e6ea",
  borderRadius: 10,
  marginBottom: 10,
};
const ctrlLabel = { fontSize: 11, color: "#888", marginBottom: 4 };
const dateInput = {
  background: "#fff",
  border: "1px solid #d4d4dc",
  borderRadius: 6,
  padding: "5px 10px",
  color: "#1f1f2c",
  fontSize: 12,
};
const iconBtn = {
  background: "#fff",
  border: "1px solid #d4d4dc",
  borderRadius: 6,
  width: 28,
  height: 26,
  fontSize: 14,
  fontWeight: 700,
  color: "#555",
  cursor: "pointer",
  padding: 0,
};
const searchBtn = {
  background: "linear-gradient(135deg, #A8D75A, #6fb720)",
  color: "#1f3a05",
  border: "none",
  borderRadius: 6,
  width: 32,
  height: 26,
  fontSize: 13,
  cursor: "pointer",
  padding: 0,
};
const chip = (active) => ({
  padding: "6px 12px",
  borderRadius: 14,
  border: active ? "none" : "1px solid #d4d4dc",
  background: active ? "linear-gradient(135deg, #A8D75A, #6fb720)" : "#fff",
  color: active ? "#1f3a05" : "#555",
  fontWeight: active ? 700 : 500,
  fontSize: 12,
  cursor: "pointer",
});

const legendRow = {
  display: "flex",
  gap: 10,
  alignItems: "center",
  padding: "8px 14px",
  background: "#fff",
  border: "1px solid #e6e6ea",
  borderRadius: 10,
  marginBottom: 10,
  flexWrap: "wrap",
  fontSize: 11,
  color: "#555",
};
const legendTitle = { fontWeight: 700, color: "#333" };
const legendItem = { display: "inline-flex", alignItems: "center", gap: 4 };
const swatch = {
  display: "inline-block",
  width: 12,
  height: 12,
  borderRadius: 2,
};
const swatchOutline = {
  display: "inline-block",
  width: 14,
  height: 10,
  borderRadius: 2,
  borderWidth: 1.5,
  borderColor: "#1f1f2c",
  background: "#fff",
};
const dot = { display: "inline-block", width: 8, height: 8, borderRadius: 4 };

const warn = {
  padding: "8px 12px",
  background: "#fff5d6",
  color: "#856404",
  border: "1px solid #ffeaa7",
  borderRadius: 8,
  fontSize: 12,
  marginBottom: 10,
};
const emptyBox = {
  padding: 40,
  textAlign: "center",
  color: "#888",
  background: "#fff",
  borderRadius: 10,
  border: "1px solid #e6e6ea",
};

const tooltipStyle = {
  position: "fixed",
  width: "max-content",
  maxWidth: 340,
  background: "rgba(255,255,255,0.98)",
  border: "1px solid #d4d4dc",
  borderRadius: 8,
  padding: "8px 10px",
  boxShadow: "0 6px 20px rgba(0,0,0,0.18)",
  pointerEvents: "none",
  zIndex: 1100,
};

const modalOverlay = {
  position: "fixed",
  inset: 0,
  background: "rgba(15,12,35,0.55)",
  backdropFilter: "blur(4px)",
  zIndex: 1600,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 24,
};
const modalBox = {
  background: "#fff",
  borderRadius: 14,
  padding: "22px 26px",
  width: "min(720px, 100%)",
  maxHeight: "85vh",
  overflowY: "auto",
  boxShadow: "0 16px 60px rgba(0,0,0,0.30)",
};
const modalClose = {
  background: "transparent",
  border: "none",
  fontSize: 18,
  color: "#888",
  cursor: "pointer",
};
const priorityBadge = {
  display: "inline-block",
  marginLeft: 8,
  padding: "2px 8px",
  fontSize: 11,
  borderRadius: 10,
  color: "#fff",
};
const tdLabel = {
  padding: "5px 10px 5px 0",
  color: "#666",
  width: 160,
  verticalAlign: "top",
  borderBottom: "1px solid #f3f3f5",
};
const tdVal = {
  padding: "5px 0",
  color: "#1f1f2c",
  verticalAlign: "top",
  borderBottom: "1px solid #f3f3f5",
};

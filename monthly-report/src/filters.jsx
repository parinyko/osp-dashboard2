import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { PRIORITY_ORDER } from "./theme.js";
import { useCompany } from "./company.jsx";
import { inRange, parseISODate, toISODate, startOfMonth, endOfMonth } from "./utils.js";

const FilterCtx = createContext(null);

// Default range = the whole latest month that has data (not today's month): on the
// 1st, before the new month's Excel is uploaded, today's month would be empty.
function defaultRange(dateMax) {
  const anchor = parseISODate(dateMax) || new Date();
  return { start: toISODate(startOfMonth(anchor)), end: toISODate(endOfMonth(anchor)) };
}

function loadPersisted(key, zoneList, teamList) {
  try {
    const obj = JSON.parse(localStorage.getItem(key) || "null");
    if (!obj || typeof obj !== "object") return null;
    const keep = (arr, allowed) => (Array.isArray(arr) ? arr.filter((x) => allowed.includes(x)) : null);
    return {
      start: typeof obj.start === "string" ? obj.start : null,
      end: typeof obj.end === "string" ? obj.end : null,
      zones: keep(obj.zones, zoneList),
      teams: keep(obj.teams, teamList),
      priorities: keep(obj.priorities, PRIORITY_ORDER),
    };
  } catch {
    return null;
  }
}

// One filter state per company (mount with key={slug}): zone and team names differ
// between companies, so sharing them would select nothing.
export function FilterProvider({ children }) {
  const co = useCompany();
  const key = `osp.filters.${co.slug}.v1`;
  // The "อื่นๆ" zone (jobs matching no zone) starts unselected, like the original DMP
  // report which only ever counted its named zones.
  const defaultZones = co.zones.length ? co.zones : co.filterZones;
  const persisted = useMemo(() => loadPersisted(key, co.filterZones, co.allFilterTeams), [key]); // eslint-disable-line react-hooks/exhaustive-deps
  const [start, setStart] = useState(() => persisted?.start || defaultRange(co.dateMax).start);
  const [end, setEnd] = useState(() => persisted?.end || defaultRange(co.dateMax).end);
  const [zones, setZones] = useState(() => (persisted?.zones?.length ? persisted.zones : defaultZones));
  const [teams, setTeams] = useState(() => (persisted?.teams?.length ? persisted.teams : co.allFilterTeams));
  const [priorities, setPriorities] = useState(() =>
    persisted?.priorities?.length ? persisted.priorities : PRIORITY_ORDER
  );

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify({ start, end, zones, teams, priorities }));
    } catch {
      /* quota / disabled */
    }
  }, [key, start, end, zones, teams, priorities]);

  const value = useMemo(
    () => ({
      start, end, zones, teams, priorities,
      dateMin: co.dateMin,
      dateMax: co.dateMax,
      setStart, setEnd, setZones, setTeams, setPriorities,
      reset: () => {
        try {
          localStorage.removeItem(key);
        } catch {
          /* ignore */
        }
        const d = defaultRange(co.dateMax);
        setStart(d.start);
        setEnd(d.end);
        setZones(defaultZones);
        setTeams(co.allFilterTeams);
        setPriorities(PRIORITY_ORDER);
      },
    }),
    [start, end, zones, teams, priorities, co, key, defaultZones]
  );

  return <FilterCtx.Provider value={value}>{children}</FilterCtx.Provider>;
}

export function useFilters() {
  const v = useContext(FilterCtx);
  if (!v) throw new Error("useFilters must be inside <FilterProvider />");
  return v;
}

// Apply all filters except those listed in `skip` (e.g., skip "date" or "zone").
export function applyFilters(records, f, skip = []) {
  const skipSet = new Set(skip);
  const out = [];
  for (const r of records) {
    if (!skipSet.has("date") && !inRange(r.d, f.start, f.end)) continue;
    if (!skipSet.has("zone") && !f.zones.includes(r.z)) continue;
    if (!skipSet.has("team") && r.t && !f.teams.includes(r.t)) continue;
    if (!skipSet.has("priority") && r.p && !f.priorities.includes(r.p)) continue;
    out.push(r);
  }
  return out;
}

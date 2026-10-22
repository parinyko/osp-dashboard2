import React, { createContext, useContext, useMemo } from "react";
import { OTHER_ZONE, ZONE_PALETTE, pick } from "./theme.js";

// The company whose report is on screen: its zones (display order), the teams of
// each zone, and its monthly targets. Every page reads zones/teams from here
// instead of the DMP-only constants the original report had hard-coded.

const CompanyCtx = createContext(null);

const uniq = (arr) => Array.from(new Set(arr));

export function CompanyProvider({ company, settings, children }) {
  const value = useMemo(() => {
    const zones = company.zones.map((z) => z.name);
    const teamsByZone = Object.fromEntries(company.zones.map((z) => [z.name, z.teams]));
    const hasOther = company.other_jobs > 0;
    if (hasOther) teamsByZone[OTHER_ZONE] = company.other_teams;
    const t = settings?.targets?.[company.slug] || {};
    const num = (v) => (typeof v === "number" && v > 0 ? v : null);
    return {
      slug: company.slug,
      name: company.name,
      total: company.total,
      dateMin: company.date_min,
      dateMax: company.date_max,
      zones,                                   // zones that get report pages
      filterZones: hasOther ? [...zones, OTHER_ZONE] : zones,
      teamsByZone,
      // A person can work in several areas (3BB, NY CABLE), so a team may sit under
      // more than one zone — company-wide team lists are de-duplicated.
      allTeams: uniq(zones.flatMap((z) => teamsByZone[z])),
      allFilterTeams: uniq(Object.values(teamsByZone).flat()),
      zoneTarget: (z) => num(t.zones?.[z]) ?? num(t.zone_default),
      teamTarget: (team) => num(t.teams?.[team]) ?? num(t.team_default),
      targets: t,
      zoneColor: (z) => (z === OTHER_ZONE ? "#95A5A6" : pick(ZONE_PALETTE, zones.indexOf(z))),
    };
  }, [company, settings]);
  return <CompanyCtx.Provider value={value}>{children}</CompanyCtx.Provider>;
}

export function useCompany() {
  const v = useContext(CompanyCtx);
  if (!v) throw new Error("useCompany must be inside <CompanyProvider />");
  return v;
}

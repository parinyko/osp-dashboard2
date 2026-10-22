"""Which company, zone and team a job belongs to.

Each contractor names its ASSIGN_TO accounts differently, so each gets its own rule:

  DMP      Dmplocal<zone> <A-C>              zone from the name, team = the account
  Origin   Originlocal<zone> <A-C> / Center  same, plus a one-team "Center" zone
  Express  Ex<grp> X / Extr<grp> X           team accounts
           Express<tier><grp> <name>         people, grouped as "<GRP> <Tier>"
           no group in the name              the "สำรอง" (reserve) zone, team = the person
  others   3BB, NY CABLE, any new company    zone = MNM area of the site, team = the person

Jobs that fit no zone of their company land in OTHER_ZONE: they still count in the
company's data but get no per-zone report pages (DMP's PM accounts, for example).
"""
from __future__ import annotations

import re

OTHER_ZONE = "อื่นๆ"
EXPRESS_RESERVE = "สำรอง"
UNKNOWN_TEAM = "(ไม่ระบุ)"


# ---------- company ----------

_COMPANY_RULES = [
    # (slug, display name, keyword found in WFM_COMPANY, zone rule)
    ("dmp", "DMP Advance Solution Network", "dmp", "dmp"),
    ("origin", "Origin Fiber", "origin", "origin"),
    ("express", "Ex-Press Data Network", "express", "express"),
    ("3bb", "3BB", "3bb", "mnm"),
    ("nycable", "NY CABLE", "ny cable", "mnm"),
]


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "co-" + format(abs(hash(name)) % 10**8, "08d")


def company_of(raw: str | None) -> tuple[str, str, str]:
    """WFM_COMPANY -> (slug, display name, zone rule)."""
    name = (raw or "").strip()
    key = name.lower().replace("-", "")
    for slug, display, kw, rule in _COMPANY_RULES:
        if kw.replace("-", "") in key:
            return slug, display, rule
    if not name:
        return "unknown", "ไม่ระบุบริษัท", "mnm"
    return _slugify(name), name, "mnm"


# ---------- zone / team per rule ----------

def _dmp(a: str):
    al = a.lower()
    zone = "Latkrabang" if "dmplocallatkrabang" in al else "Pathumthani" if "dmplocalpathumthani" in al else None
    if not zone:
        return OTHER_ZONE, a, (9, a)
    m = re.match(r"(?i)^dmplocal(latkrabang|pathumthani)\s*([a-z])\b", a)
    team = f"Dmplocal{m.group(1).lower()} {m.group(2).upper()}" if m else a
    return zone, team, (0, team)


def _origin(a: str):
    al = a.lower()
    for key, zone in (("originlocalthungkhru", "Thungkhru"), ("originlocalnonthaburi", "Nonthaburi")):
        if key in al:
            m = re.match(r"(?i)^originlocal(thungkhru|nonthaburi)\s*([a-z])\b", a)
            team = f"Originlocal{m.group(1).lower()} {m.group(2).upper()}" if m else a
            return zone, team, (0, team)
    if al.startswith("originlocal"):
        return "Center", "Originlocal Center", (0, "Originlocal Center")
    return OTHER_ZONE, a, (9, a)


EXPRESS_GROUPS = ("sct", "bpl", "cwt", "tlc", "eds")
_TIER_ORDER = {"Mini": 0, "Macro": 1, "Local": 2, "Express": 3}


def _express(a: str):
    first, _, rest = a.strip().partition(" ")
    tok = first.lower()
    if tok.startswith("express"):
        body = tok[len("express"):]
        grp = next((g for g in EXPRESS_GROUPS if g in body), None)
        if grp:
            if "mini" in body:
                tier = "Mini"
            elif "macro" in body or "marco" in body:
                tier = "Macro"
            elif "local" in body:
                tier = "Local"
            else:
                tier = "Express"
            team = f"{grp.upper()} {tier}"
            return grp.upper(), team, (1, _TIER_ORDER[tier], team)
    elif tok.startswith("ex"):
        body = tok[2:]
        tr = body.startswith("tr")
        if tr:
            body = body[2:]
        if body in EXPRESS_GROUPS:
            letter = rest.strip()
            if re.fullmatch(r"[A-Za-z]", letter):
                team = f"Ex{'tr' if tr else ''}{body} {letter.upper()}"
            else:
                team = a
            return body.upper(), team, (0, team)
    return EXPRESS_RESERVE, a, (2, a)


_MNM = re.compile(r"(?i)AREA\s*(\d+)\s*\(([^)]*)\)")


def mnm_area(zid: str | None) -> tuple[int, str] | None:
    """"MNM-AREA2 (Bangkok-ONT)" -> (2, "ONT")."""
    if not zid:
        return None
    m = _MNM.search(zid)
    if not m:
        return None
    label = m.group(2).strip()
    label = label.split("-")[-1].strip() or label
    return int(m.group(1)), label


def _mnm(a: str, zid: str | None):
    area = mnm_area(zid)
    team = a or UNKNOWN_TEAM
    if not area:
        return OTHER_ZONE, team, (9, team)
    return area[1], team, (0, team)


# Fixed zone order for companies whose zones come from ASSIGN_TO. MNM-area
# companies are ordered by area number instead (see zone_order()).
FIXED_ZONES = {
    "dmp": ["Latkrabang", "Pathumthani"],
    "origin": ["Thungkhru", "Nonthaburi", "Center"],
    "express": ["SCT", "BPL", "CWT", "TLC", "EDS", EXPRESS_RESERVE],
}


def classify(company_raw: str | None, assign_to: str | None, zone_by_site: str | None) -> dict:
    """-> {slug, company, rule, zone, team, sort}. `sort` orders teams within a zone."""
    slug, display, rule = company_of(company_raw)
    a = (assign_to or "").strip()
    if rule == "dmp":
        zone, team, sort = _dmp(a) if a else (OTHER_ZONE, UNKNOWN_TEAM, (9,))
    elif rule == "origin":
        zone, team, sort = _origin(a) if a else (OTHER_ZONE, UNKNOWN_TEAM, (9,))
    elif rule == "express":
        zone, team, sort = _express(a) if a else (OTHER_ZONE, UNKNOWN_TEAM, (9,))
    else:
        zone, team, sort = _mnm(a, zone_by_site)
    return {"slug": slug, "company": display, "rule": rule, "zone": zone, "team": team, "sort": sort}


def zone_order(slug: str, rule: str, zones_seen: dict[str, int | None]) -> list[str]:
    """Report zones of a company, in display order. `zones_seen` maps zone -> MNM
    area number (None for non-MNM zones). OTHER_ZONE never gets its own pages."""
    present = [z for z in zones_seen if z != OTHER_ZONE]
    if slug in FIXED_ZONES:
        return [z for z in FIXED_ZONES[slug] if z in present]
    return sorted(present, key=lambda z: (zones_seen[z] if zones_seen[z] is not None else 99, z))

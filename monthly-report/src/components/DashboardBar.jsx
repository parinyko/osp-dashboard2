import { useEffect, useRef, useState } from "react";
import { BASE } from "../data.js";

// The OSP dashboard's green app bar, so the Monthly Report (served under /monthly on the
// dashboard's domain) has the same page menu and account button as every other page.
// Shown only when mounted under a base path; a standalone run has no dashboard to go back to.

const LINKS = [
  ["/", "หน้าแรก", "M3 11 12 4l9 7|M5 10v10h14V10"],
  ["/dashboard", "Status Team", "M2.5 20c1-3.5 3.5-5.5 6.5-5.5s5.5 2 6.5 5.5|M16 4.5a3.5 3.5 0 0 1 0 7M18 14.8c1.8.8 3 2.6 3.5 5.2", [9, 8, 3.5]],
  ["/team_done", "Team Done", "m8 12 3 3 5-6", null, true],
  ["/job_monitor", "Job Monitor", "M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"],
  ["/daily_osp_remain", "Daily OSP", "M3 20h18|m4 16 5-5 4 3 7-7"],
  ["/resource_monitor", "Resource Monitor", "M12 7v5l3 2", [12, 12, 9]],
  ["/map", "Job Map", "M3 7l6-3 6 3 6-3v13l-6 3-6-3-6 3V7Z|M9 4v13M15 7v13"],
];

const C = { ink: "#1F3322", ink2: "#315A28", muted: "#637361", line: "#D6E6CE", line2: "#CFE0C5", soft: "#F7FBF5", on: "#E3F1D6", brand: "#4F8F18" };
const svg = { width: 16, height: 16, flex: "none", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };

function Icon({ d, circle, box, size = 16 }) {
  return (
    <svg viewBox="0 0 24 24" style={{ ...svg, width: size, height: size }} aria-hidden="true">
      {box && <rect x="3" y="3" width="18" height="18" rx="3" />}
      {circle && <circle cx={circle[0]} cy={circle[1]} r={circle[2]} />}
      {d.split("|").map((p) => <path key={p} d={p} />)}
    </svg>
  );
}

const linkStyle = (on) => ({
  display: "inline-flex", alignItems: "center", gap: 6, height: 34, padding: "0 12px", borderRadius: 9,
  border: `1px solid ${on ? "#A9CF8A" : C.line2}`, background: on ? C.on : C.soft, color: on ? "#264D1E" : C.ink2,
  fontSize: 13, fontWeight: 600, textDecoration: "none", whiteSpace: "nowrap",
});

function Account() {
  const [me, setMe] = useState(null);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    fetch("/api/me", { credentials: "same-origin", cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => setMe(j?.user || null))
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!open) return;
    const close = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const esc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("click", close); document.removeEventListener("keydown", esc); };
  }, [open]);
  if (!me) return null;
  const person = "M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6";
  const item = { display: "flex", alignItems: "center", gap: 9, padding: "8px 9px", borderRadius: 8, color: C.ink2, fontSize: 13, fontWeight: 600, textDecoration: "none" };
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button" onClick={() => setOpen((v) => !v)} aria-haspopup="menu" aria-expanded={open} aria-label={`บัญชีผู้ใช้ ${me.name}`} title={me.name}
        style={{ width: 38, height: 38, borderRadius: "50%", border: `1px solid ${open ? "#A9CF8A" : C.line2}`, background: open ? C.on : "#fff", color: C.ink2,
          display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", padding: 0, boxShadow: "0 2px 8px rgba(30,60,20,.08)" }}
      >
        <Icon d={person} circle={[12, 8, 4]} size={19} />
      </button>
      {open && (
        <div role="menu" style={{ position: "absolute", right: 0, top: "calc(100% + 8px)", zIndex: 1000, width: 240, background: "#fff", border: `1px solid ${C.line}`,
          borderRadius: 12, boxShadow: "0 14px 36px rgba(30,60,20,.16)", padding: 6, display: "flex", flexDirection: "column", gap: 2 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 8px 10px", borderBottom: `1px solid ${C.line}`, marginBottom: 4 }}>
            <span style={{ width: 34, height: 34, borderRadius: "50%", background: C.on, color: "#264D1E", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
              <Icon d={person} circle={[12, 8, 4]} size={18} />
            </span>
            <span style={{ minWidth: 0 }}>
              <b style={{ display: "block", fontSize: 13.5, color: C.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{me.name}</b>
              <small style={{ display: "block", fontSize: 11.5, color: C.muted }}>
                {me.role === "admin" ? "ผู้ดูแลระบบ" : "ผู้ใช้"}{me.company ? ` · ${me.company}` : ""}
              </small>
            </span>
          </div>
          {me.role === "admin" && (
            <a role="menuitem" href="/admin/users" style={item}>
              <Icon d="M2.5 20c1-3.5 3.5-5.5 6.5-5.5s5.5 2 6.5 5.5|M16 4.5a3.5 3.5 0 0 1 0 7M18 14.8c1.8.8 3 2.6 3.5 5.2" circle={[9, 8, 3.5]} />จัดการผู้ใช้
            </a>
          )}
          <a role="menuitem" href="/logout" style={{ ...item, color: "#B42318" }}>
            <Icon d="M14 4h5v16h-5|M10 8l-4 4 4 4M6 12h10" />ออกจากระบบ
          </a>
        </div>
      )}
    </div>
  );
}

export default function DashboardBar() {
  if (!BASE) return null;
  return (
    <header
      style={{
        display: "flex", alignItems: "center", gap: "10px 14px", padding: "9px 18px", flexWrap: "wrap", position: "relative", zIndex: 30,
        fontFamily: '"IBM Plex Sans Thai", Tahoma, sans-serif', color: C.ink,
        background: "linear-gradient(135deg,#FFFFFF 0%,#F4FAEF 55%,#DFF1C9 100%)", borderBottom: `1px solid ${C.line}`,
      }}
    >
      <a href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", color: C.brand }}>
        <Icon d="M6 3h8l4 4v14H6z|M14 3v4h4M9 12h6M9 16h6" size={28} />
        <span>
          <b style={{ display: "block", fontSize: 20, fontWeight: 700, lineHeight: 1.15 }}>Monthly Report</b>
          <small style={{ display: "block", fontSize: 12, color: C.muted }}>Dashboard OSP BKK · Team Performance</small>
        </span>
      </a>
      <nav aria-label="หน้าอื่น" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {LINKS.map(([href, label, d, circle, box]) => (
          <a key={href} href={href} title={label} style={linkStyle(false)}>
            <Icon d={d} circle={circle} box={box} />
            <span className="dbar-label">{label}</span>
          </a>
        ))}
        <a href={BASE + "/"} title="Monthly Report" aria-current="page" style={linkStyle(true)}>
          <Icon d="M6 3h8l4 4v14H6z|M14 3v4h4M9 12h6M9 16h6" />
          <span className="dbar-label">Monthly Report</span>
        </a>
      </nav>
      <span style={{ flex: 1 }} />
      <Account />
    </header>
  );
}

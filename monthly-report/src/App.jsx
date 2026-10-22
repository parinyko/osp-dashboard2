import React, { useEffect, useMemo, useRef, useState } from "react";
import { useAuth, LoginScreen } from "./auth.jsx";
import { useCompanies, useSettings, useCompanyData } from "./data.js";
import { usePath, parseRoute, navigate, companyUrl } from "./router.js";
import { CompanyProvider, useCompany } from "./company.jsx";
import { FilterProvider } from "./filters.jsx";
import FilterBar from "./components/FilterBar.jsx";
import UploadPanel from "./components/UploadPanel.jsx";
import SettingsPanel from "./components/SettingsPanel.jsx";
import Landing from "./components/Landing.jsx";
import DashboardBar from "./components/DashboardBar.jsx";
import { captureAllPages, exportToPDF, exportToPPTX } from "./export.js";
import { toISODate } from "./utils.js";

import Page01Cover from "./pages/Page01_Cover.jsx";
import Page02 from "./pages/Page02_JobTotalInZone.jsx";
import Page03 from "./pages/Page03_PriorityAllZone.jsx";
import Page04 from "./pages/Page04_JobPerTeamPriority.jsx";
import Page05 from "./pages/Page05_SlaByZone.jsx";
import JobPerDayPage from "./pages/JobPerDayPage.jsx";
import Page08 from "./pages/Page08_TopProblemReason.jsx";
import SlaPerTeamPage from "./pages/SlaPerTeamPage.jsx";
import TotalJobOverviewPage from "./pages/TotalJobOverviewPage.jsx";
import AvgDurationPage from "./pages/AvgDurationPage.jsx";
import Page21 from "./pages/Page21_AvgRanking.jsx";
import Page22 from "./pages/Page22_KPISla.jsx";
import DashSolutionSummary from "./pages/DashSolutionSummary.jsx";
import DashPendingByTeam from "./pages/DashPendingByTeam.jsx";
import DashJobGantt from "./pages/DashJobGantt.jsx";

// The report follows the original PDF's order, minus its per-team overview pages
// (old 12–14, 16–18). Pages that were "one per DMP zone" now repeat for every zone
// of the company, so DMP gets 17 pages and Express, with six zones, gets 33
// (Job per day also has one company-wide page before the zone ones).
export function buildNav(zones) {
  const items = [
    { id: "cover", t: "Cover / หน้าปก", c: Page01Cover },
    { id: "jobtotal", t: "Job Total in Zone", c: Page02 },
    { id: "priority", t: "Priority All Zone", c: Page03 },
    { id: "jobperteam", t: "Job per team & priority", c: Page04 },
    { id: "sla", t: "SLA% by Zone", c: Page05 },
    { id: "jobperday", t: "Job per day — ทั้งบริษัท", c: JobPerDayPage },
    ...zones.map((z) => ({ id: `jobperday.${z}`, t: `Job per day — ${z}`, c: JobPerDayPage, props: { zone: z } })),
    { id: "top5", t: "TOP 5 Problem Reason", c: Page08 },
    ...zones.map((z) => ({ id: `slateam.${z}`, t: `SLA% per team — ${z}`, c: SlaPerTeamPage, props: { zone: z } })),
    ...zones.map((z) => ({ id: `overview.${z}`, t: `Overview — ${z} Zone`, c: TotalJobOverviewPage, props: { zone: z } })),
    ...zones.map((z) => ({ id: `avgdur.${z}`, t: `Avg Duration — ${z}`, c: AvgDurationPage, props: { zone: z } })),
    { id: "ranking", t: "Avg Overall Ranking", c: Page21 },
    { id: "kpisla", t: "KPI SLA % Per Team", c: Page22 },
  ];
  return items.map((it, i) => ({ ...it, n: String(i + 1) }));
}

const DASH = [
  { id: "d1", n: "D1", t: "Solution Summary", c: DashSolutionSummary },
  { id: "d2", n: "D2", t: "งานรอลงข้อมูล (รายทีม)", c: DashPendingByTeam },
  { id: "d3", n: "D3", t: "Job Timeline (Gantt)", c: DashJobGantt },
];

export default function App() {
  const auth = useAuth();
  // Viewing can be open (no view password); admins still sign in to upload / set targets.
  const [wantLogin, setWantLogin] = useState(false);
  if (auth.loading) return <Splash text="กำลังโหลด…" />;
  if (!auth.role || wantLogin)
    return (
      <LoginScreen
        onLogin={async (pw) => {
          await auth.login(pw);
          setWantLogin(false);
        }}
        onCancel={auth.role ? () => setWantLogin(false) : null}
      />
    );
  const adminLogin = auth.auth && auth.role === "viewer" ? () => setWantLogin(true) : null;
  return <Shell auth={{ ...auth, adminLogin }} />;
}

function Shell({ auth }) {
  const route = parseRoute(usePath());
  const companies = useCompanies();
  const settings = useSettings();
  const [uploadOpen, setUploadOpen] = useState(false);
  const isAdmin = auth.role === "admin";

  if ((companies.loading && !companies.data) || (settings.loading && !settings.data)) return <Splash text="กำลังโหลดข้อมูล…" />;
  if (companies.error || settings.error) return <Splash text={`Error: ${(companies.error || settings.error).message}`} error />;

  const meta = companies.data;
  const company = route.kind === "company" ? meta.companies.find((c) => c.slug === route.slug) : null;
  const upload = <UploadPanel open={uploadOpen} onClose={() => setUploadOpen(false)} />;

  if (!company) {
    return (
      <>
        <DashboardBar />
        <Landing
          meta={meta}
          isAdmin={isAdmin}
          onUpload={() => setUploadOpen(true)}
          onLogout={auth.logout}
          showLogout={auth.auth && isAdmin}
          onAdminLogin={auth.adminLogin}
          notice={route.kind === "company" ? `ไม่พบบริษัท "${route.slug}" ในข้อมูลล่าสุด` : null}
        />
        {upload}
      </>
    );
  }

  return (
    <>
      <CompanyProvider key={company.slug} company={company} settings={settings.data}>
        <FilterProvider>
          <CompanyView
            companies={meta.companies}
            pageId={route.pageId}
            isAdmin={isAdmin}
            auth={auth}
            generatedAt={meta.generated_at}
            onUpload={() => setUploadOpen(true)}
          />
        </FilterProvider>
      </CompanyProvider>
      {upload}
    </>
  );
}

function CompanyView({ companies, pageId, isAdmin, auth, generatedAt, onUpload }) {
  const co = useCompany();
  const { data, error } = useCompanyData(co.slug);
  const nav = useMemo(() => buildNav(co.zones), [co.zones]);
  const all = useMemo(() => [...nav, ...DASH], [nav]);
  const [exportId, setExportId] = useState(null); // page shown while exporting
  const [present, setPresent] = useState(false);
  const [exportState, setExportState] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const exportTargetRef = useRef(null);

  const urlId = all.some((p) => p.id === pageId) ? pageId : nav[0].id;
  const activeId = exportId || urlId;
  const active = all.find((p) => p.id === activeId);
  const go = (id) => navigate(companyUrl(co.slug, id));

  const runExport = async (kind) => {
    if (exportState) return;
    setExportState({ kind, i: 0, total: nav.length, label: "เริ่ม…" });
    try {
      const shots = await captureAllPages({
        nav,
        setActiveId: setExportId,
        getTargetEl: () => exportTargetRef.current,
        onProgress: (i, total, label) => setExportState({ kind, i, total, label }),
      });
      setExportState({ kind, i: nav.length, total: nav.length, label: "กำลังสร้างไฟล์…" });
      const stamp = toISODate(new Date());
      const opts = { filename: `${co.slug}-monthly-report-${stamp}.${kind}`, title: `${co.name} — Monthly Report` };
      if (kind === "pdf") await exportToPDF(shots, opts);
      else await exportToPPTX(shots, opts);
    } catch (err) {
      console.error(err);
      alert("Export error: " + (err?.message || err));
    } finally {
      setExportId(null);
      setExportState(null);
    }
  };

  // Present mode: ESC exits, arrows flip report pages.
  useEffect(() => {
    if (!present) return undefined;
    const onKey = (e) => {
      const el = e.target;
      const typing = el instanceof HTMLElement && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName));
      const idx = nav.findIndex((x) => x.id === activeId);
      if (e.key === "Escape") {
        setPresent(false);
        if (document.fullscreenElement) document.exitFullscreen?.();
      } else if (typing) {
        return;
      } else if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault();
        go(nav[Math.min(nav.length - 1, idx + 1)].id);
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        go(nav[Math.max(0, idx - 1)].id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [present, activeId, nav]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onFs = () => {
      if (!document.fullscreenElement && present) setPresent(false);
    };
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, [present]);

  if (error) return <Splash text={`Error: ${error.message}`} error />;
  if (!data) return <Splash text={`กำลังโหลดข้อมูล ${co.name}…`} />;

  const records = data.records;
  const Active = active.c;
  const page = <Active key={active.id} records={records} {...(active.props || {})} />;

  const enterPresent = async () => {
    if (!nav.some((p) => p.id === activeId)) go(nav[0].id); // dashboards aren't slides
    setPresent(true);
    try {
      await document.documentElement.requestFullscreen?.();
    } catch {
      /* ignore */
    }
  };

  if (present) {
    return (
      <PresentView nav={nav} activeId={activeId} go={go} onExit={() => {
        setPresent(false);
        if (document.fullscreenElement) document.exitFullscreen?.();
      }}>
        {page}
      </PresentView>
    );
  }

  return (
    <>
      <DashboardBar />
      <div style={{ display: "flex", minHeight: "100vh" }}>
        <Sidebar
          companies={companies}
          sections={[
            { title: "Monthly Report", subtitle: `${nav.length} หน้า · Team Performance`, items: nav },
            { title: "Dashboard (หลังบ้าน)", subtitle: "Solution / Pending / Timeline", items: DASH, accent: "#3498DB" },
          ]}
          activeId={activeId}
          onPick={go}
        />
        <main style={{ flex: 1, padding: "24px 32px", minWidth: 0, maxWidth: "calc(100vw - 280px)" }}>
          <TopBanner
            isAdmin={isAdmin}
            showLogout={auth.auth && isAdmin}
            onAdminLogin={auth.adminLogin}
            exporting={!!exportState}
            onUpload={onUpload}
            onSettings={() => setSettingsOpen(true)}
            onExportPDF={() => runExport("pdf")}
            onExportPPTX={() => runExport("pptx")}
            onPresent={enterPresent}
            onLogout={auth.logout}
          />
          <FilterBar />
          <div ref={exportTargetRef}>{page}</div>
          <footer style={{ marginTop: 32, padding: "16px 0", fontSize: 11, color: "#9a9aaf", textAlign: "center" }}>
            {co.name} — generated {generatedAt?.replace("T", " ")}
          </footer>
        </main>
      </div>
      {exportState && <ExportOverlay state={exportState} />}
      {settingsOpen && <SettingsPanel open records={data?.records} onClose={() => setSettingsOpen(false)} />}
    </>
  );
}

function Splash({ text, error }) {
  return <div style={{ padding: 40, color: error ? "#c0392b" : "#1f1f2c" }}>{text}</div>;
}

function ExportOverlay({ state }) {
  const pct = state.total > 0 ? Math.round((state.i / state.total) * 100) : 0;
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(15, 12, 35, 0.55)", backdropFilter: "blur(4px)", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "#fff", borderRadius: 14, padding: "24px 32px", minWidth: 360, boxShadow: "0 16px 60px rgba(0,0,0,0.30)", textAlign: "center" }}>
        <div style={{ fontSize: 22, marginBottom: 6 }}>{state.kind === "pdf" ? "📄" : "🎞️"}</div>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#1f1f2c", marginBottom: 4 }}>
          กำลัง Export {state.kind === "pdf" ? "PDF" : "PowerPoint"}
        </div>
        <div style={{ fontSize: 12, color: "#888", marginBottom: 14 }}>
          {state.i} / {state.total} · {state.label}
        </div>
        <div style={{ height: 8, background: "#f0f0f3", borderRadius: 4, overflow: "hidden" }}>
          <div style={{ width: `${pct}%`, height: "100%", background: "linear-gradient(90deg, #A8D75A, #6fb720)", transition: "width 0.3s" }} />
        </div>
        <div style={{ fontSize: 11, color: "#888", marginTop: 8 }}>อย่าปิดหน้าระหว่างกำลังสร้างไฟล์</div>
      </div>
    </div>
  );
}

function PresentView({ nav, activeId, go, onExit, children }) {
  const idx = nav.findIndex((x) => x.id === activeId);
  const prev = nav[Math.max(0, idx - 1)]?.id;
  const next = nav[Math.min(nav.length - 1, idx + 1)]?.id;
  const cur = nav[idx] || nav[0];
  return (
    <div style={{ minHeight: "100vh", background: "#f5f6f8", padding: "20px 28px 24px", position: "relative" }}>
      {children}
      <div
        style={{
          position: "fixed",
          bottom: 18,
          left: "50%",
          transform: "translateX(-50%)",
          background: "rgba(20, 22, 32, 0.92)",
          color: "#fff",
          padding: "8px 14px",
          borderRadius: 999,
          display: "flex",
          alignItems: "center",
          gap: 10,
          fontSize: 13,
          boxShadow: "0 8px 28px rgba(0,0,0,0.30)",
          zIndex: 1000,
          backdropFilter: "blur(6px)",
        }}
      >
        <button onClick={() => go(prev)} disabled={prev === activeId} style={pillBtn} title="หน้าก่อน (← / PgUp)">‹</button>
        <span style={{ minWidth: 90, textAlign: "center", fontWeight: 600 }}>
          หน้า {cur.n} / {nav.length}
        </span>
        <button onClick={() => go(next)} disabled={next === activeId} style={pillBtn} title="หน้าถัดไป (→ / PgDn)">›</button>
        <span style={{ width: 1, height: 18, background: "rgba(255,255,255,0.18)", margin: "0 4px" }} />
        <select
          value={cur.id}
          onChange={(e) => go(e.target.value)}
          style={{ background: "rgba(255,255,255,0.08)", color: "#fff", border: "1px solid rgba(255,255,255,0.18)", borderRadius: 14, padding: "5px 10px", fontSize: 12, cursor: "pointer", maxWidth: 260 }}
        >
          {nav.map((it) => (
            <option key={it.id} value={it.id} style={{ background: "#1a1a2e", color: "#fff" }}>
              {it.n}. {it.t}
            </option>
          ))}
        </select>
        <span style={{ width: 1, height: 18, background: "rgba(255,255,255,0.18)", margin: "0 4px" }} />
        <button onClick={onExit} style={{ ...pillBtn, color: "#FFD180" }} title="ออกจาก Present (ESC)">✕ ออก</button>
      </div>
    </div>
  );
}

const pillBtn = {
  background: "rgba(255,255,255,0.08)",
  color: "#fff",
  border: "1px solid rgba(255,255,255,0.18)",
  borderRadius: 14,
  padding: "4px 10px",
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
  minWidth: 30,
};

function TopBanner({ isAdmin, showLogout, onAdminLogin, exporting, onUpload, onSettings, onExportPDF, onExportPPTX, onPresent, onLogout }) {
  const co = useCompany();
  return (
    <div
      style={{
        background: "linear-gradient(135deg, #d6f0ad 0%, #ffe2a8 100%)",
        border: "1px solid #e6e6ea",
        borderRadius: 12,
        padding: "16px 20px",
        marginBottom: 18,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 14,
        flexWrap: "wrap",
      }}
    >
      <div>
        <div style={{ fontSize: 12, color: "#6b6b78", letterSpacing: "0.08em", textTransform: "uppercase" }}>{co.name}</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: "#4d6a1f", marginTop: 2 }}>Monthly Report — Team Performance</div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
        {isAdmin && (
          <>
            <button onClick={onUpload} disabled={exporting} style={ghostBtn(exporting, "#2C7A4D")} title="อัปโหลดไฟล์ Excel (อัปเดตทุกบริษัท)">
              📥 Upload Excel
            </button>
            <button onClick={onSettings} disabled={exporting} style={ghostBtn(exporting, "#6C5CE7")} title="ตั้งเป้าหมายของบริษัทนี้">
              ⚙️ เป้าหมาย
            </button>
          </>
        )}
        <button onClick={onExportPDF} disabled={exporting} style={ghostBtn(exporting, "#C0392B")} title="Export หน้ารายงานทั้งหมดเป็น PDF">
          📄 PDF
        </button>
        <button onClick={onExportPPTX} disabled={exporting} style={ghostBtn(exporting, "#D35400")} title="Export หน้ารายงานทั้งหมดเป็น PowerPoint">
          🎞️ PowerPoint
        </button>
        <button
          onClick={onPresent}
          disabled={exporting}
          style={{
            background: exporting ? "#9aaa80" : "linear-gradient(135deg, #4d6a1f, #6fb720)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 18px",
            fontWeight: 700,
            fontSize: 13,
            cursor: exporting ? "not-allowed" : "pointer",
            boxShadow: "0 4px 12px rgba(77,106,31,0.30)",
          }}
          title="Present (full screen)"
        >
          🎬 Present
        </button>
        {showLogout && (
          <button onClick={onLogout} style={ghostBtn(false, "#777")} title="ออกจากระบบ">
            ออก
          </button>
        )}
        {onAdminLogin && (
          <button onClick={onAdminLogin} style={ghostBtn(false, "#777")} title="เข้าสู่ระบบผู้ดูแล (อัปโหลด Excel / ตั้งเป้า)">
            🔑 Admin
          </button>
        )}
      </div>
    </div>
  );
}

function ghostBtn(disabled, color) {
  return {
    background: "#fff",
    color: disabled ? "#aaa" : color,
    border: `1px solid ${disabled ? "#ddd" : color + "55"}`,
    borderRadius: 8,
    padding: "10px 14px",
    fontWeight: 700,
    fontSize: 13,
    cursor: disabled ? "not-allowed" : "pointer",
  };
}

function Sidebar({ companies, sections, activeId, onPick }) {
  const co = useCompany();
  return (
    <aside
      style={{
        width: 280,
        flexShrink: 0,
        background: "#ffffff",
        borderRight: "1px solid #e6e6ea",
        padding: "16px 12px",
        position: "sticky",
        top: 0,
        height: "100vh",
        overflowY: "auto",
      }}
    >
      <div style={{ padding: "0 12px 14px", borderBottom: "1px solid #ececef", marginBottom: 12 }}>
        <button onClick={() => navigate("/")} style={{ background: "none", border: "none", color: "#3498DB", cursor: "pointer", fontSize: 12, fontWeight: 700, padding: 0 }}>
          ← ทุกบริษัท
        </button>
        <select
          value={co.slug}
          onChange={(e) => navigate(companyUrl(e.target.value))}
          style={{ width: "100%", marginTop: 8, padding: "8px 10px", borderRadius: 8, border: "1px solid #d4d4dc", fontSize: 13, fontWeight: 700, color: "#1f1f2c", background: "#fafafc" }}
        >
          {companies.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.name} ({c.total.toLocaleString()})
            </option>
          ))}
        </select>
      </div>
      {sections.map((sec, sIdx) => {
        const accent = sec.accent || "#A8D75A";
        const accentText = sec.accent || "#4d6a1f";
        return (
          <div key={sec.title} style={{ marginBottom: 16 }}>
            <div style={{ padding: "0 12px 10px", borderBottom: "1px solid #ececef", marginBottom: 8, marginTop: sIdx === 0 ? 0 : 6 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: accentText }}>
                {sIdx === 0 ? "📊 " : "🗄️ "}
                {sec.title}
              </div>
              <div style={{ fontSize: 11, color: "#8b8b96", marginTop: 2 }}>{sec.subtitle}</div>
            </div>
            {sec.items.map((it) => {
              const isActive = activeId === it.id;
              return (
                <button
                  key={it.id}
                  onClick={() => onPick(it.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    width: "100%",
                    padding: "8px 12px",
                    marginBottom: 2,
                    background: isActive ? `${accent}22` : "transparent",
                    color: isActive ? accentText : "#444",
                    border: "none",
                    borderLeft: isActive ? `3px solid ${accent}` : "3px solid transparent",
                    cursor: "pointer",
                    textAlign: "left",
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 400,
                    borderRadius: "0 6px 6px 0",
                    transition: "all 0.15s",
                  }}
                >
                  <span style={{ fontSize: 10, color: "#8b8b96", fontWeight: 700, minWidth: 24 }}>{it.n}</span>
                  <span style={{ flex: 1 }}>{it.t}</span>
                </button>
              );
            })}
          </div>
        );
      })}
    </aside>
  );
}

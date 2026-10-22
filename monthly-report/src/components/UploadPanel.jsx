import React, { useEffect, useRef, useState } from "react";
import { api, invalidate } from "../data.js";

// Same rule as the server: an export date may follow the year.
const FILENAME_RE = /^Data\s+Job\s+done\s+(\d{4})\b.*\.(xlsx|xlsm)$/i;

function fmtSize(n) {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

function fmtDate(s) {
  if (!s) return "—";
  return s.replace("T", " ");
}

const fetchStatus = () => api("/api/status");

export default function UploadPanel({ open, onClose, onDataChanged }) {
  const [status, setStatus] = useState(null);
  const [loadErr, setLoadErr] = useState(null);
  const [busy, setBusy] = useState(null); // string label or null
  const [errorMsg, setErrorMsg] = useState(null);
  const [okMsg, setOkMsg] = useState(null);
  const fileRef = useRef(null);
  // The file input and button are disabled while busy, but drag-and-drop is not;
  // a ref (not state) also blocks a second drop landing before the re-render.
  const busyRef = useRef(false);

  const refresh = async () => {
    setLoadErr(null);
    try {
      setStatus(await fetchStatus());
    } catch (e) {
      setLoadErr(String(e.message || e));
    }
  };

  useEffect(() => {
    if (open) refresh();
  }, [open]);

  if (!open) return null;

  const handleUpload = async (file) => {
    if (busyRef.current) return;
    setErrorMsg(null);
    setOkMsg(null);
    if (!file) return;
    if (!FILENAME_RE.test(file.name)) {
      setErrorMsg(
        `ชื่อไฟล์ต้องขึ้นต้นด้วย "Data Job done <ปี>" และเป็น .xlsx / .xlsm — ที่ได้: ${file.name}`
      );
      return;
    }
    busyRef.current = true;
    setBusy(`กำลังอัพโหลด ${file.name} …`);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const out = await api("/api/upload", { method: "POST", body: fd });
      setStatus(out.status);
      setOkMsg(
        `✓ อัพเดตปี ${out.year} แล้ว · ${out.build.total.toLocaleString()} งาน (${out.build.date_min} → ${out.build.date_max})\n` +
          out.build.companies.map((c) => `   ${c.name}: ${c.total.toLocaleString()}`).join("\n")
      );
      invalidate();
      onDataChanged?.();
    } catch (e) {
      setErrorMsg(String(e.message || e));
    } finally {
      busyRef.current = false;
      setBusy(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleDelete = async (name) => {
    if (busyRef.current) return;
    if (!confirm(`ลบไฟล์ ${name} ออกจาก server?`)) return;
    busyRef.current = true;
    setBusy(`กำลังลบ ${name} …`);
    setErrorMsg(null);
    setOkMsg(null);
    try {
      const out = await api(`/api/files/${encodeURIComponent(name)}`, { method: "DELETE" });
      setStatus(out.status);
      setOkMsg(`✓ ลบ ${name} แล้ว`);
      invalidate();
      onDataChanged?.();
    } catch (e) {
      setErrorMsg(String(e.message || e));
    } finally {
      busyRef.current = false;
      setBusy(null);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,12,35,0.55)",
        backdropFilter: "blur(4px)",
        zIndex: 1500,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#fff",
          borderRadius: 14,
          padding: "22px 26px",
          width: "min(640px, 100%)",
          maxHeight: "85vh",
          overflowY: "auto",
          boxShadow: "0 16px 60px rgba(0,0,0,0.30)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 8,
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 800, color: "#1f1f2c" }}>
            อัพโหลดไฟล์ Excel
          </div>
          <button onClick={onClose} style={closeBtn} title="ปิด">
            ✕
          </button>
        </div>
        <div style={{ fontSize: 12, color: "#888", marginBottom: 16 }}>
          ชื่อไฟล์ขึ้นต้นด้วย <b>Data Job done &lt;ปี&gt;</b> (.xlsx / .xlsm) เช่น <i>Data Job done 2026 10:10:2026.xlsx</i> —
          อัปไฟล์ปีเดิมจะแทนที่ของเดิม (ถ้าไฟล์ใหม่อ่านไม่ได้ ระบบใช้ไฟล์เดิมต่อ) · ทุกบริษัทอัปเดตพร้อมกันจากไฟล์เดียว
        </div>

        {/* Upload row */}
        <div
          style={{
            border: "2px dashed #c9d8a8",
            borderRadius: 10,
            padding: "18px 20px",
            background: "#f7faf0",
            display: "flex",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
          onDragOver={(e) => {
            e.preventDefault();
            e.currentTarget.style.background = "#eef6dc";
          }}
          onDragLeave={(e) => {
            e.currentTarget.style.background = "#f7faf0";
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.currentTarget.style.background = "#f7faf0";
            const file = e.dataTransfer.files?.[0];
            if (file) handleUpload(file);
          }}
        >
          <div style={{ fontSize: 28 }}>📥</div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontWeight: 700, color: "#4d6a1f", fontSize: 14 }}>
              ลากไฟล์มาวาง หรือเลือกไฟล์
            </div>
            <div style={{ fontSize: 11, color: "#7a8569", marginTop: 2 }}>
              .xlsx / .xlsm · 1 ไฟล์ต่อ 1 ปี
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.xlsm"
            onChange={(e) => handleUpload(e.target.files?.[0])}
            style={{ display: "none" }}
            disabled={!!busy}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={!!busy}
            style={primaryBtn(!!busy)}
          >
            เลือกไฟล์
          </button>
        </div>

        {/* Messages */}
        {busy && <Banner color="#856404" bg="#fff8e1">⏳ {busy}</Banner>}
        {errorMsg && <Banner color="#c0392b" bg="#fdecea">⚠️ {errorMsg}</Banner>}
        {okMsg && <Banner color="#1e6b3a" bg="#e6f4ea">{okMsg}</Banner>}

        {/* Server status */}
        <div style={{ marginTop: 18 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 8,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 700, color: "#1f1f2c" }}>
              ไฟล์ที่ server เก็บไว้
            </div>
            <button onClick={refresh} style={ghostBtn}>↻ refresh</button>
          </div>
          {loadErr && (
            <div style={{ fontSize: 12, color: "#c0392b" }}>
              โหลดสถานะไม่สำเร็จ: {loadErr}
            </div>
          )}
          {status && (
            <>
              <table
                style={{
                  width: "100%",
                  fontSize: 12,
                  borderCollapse: "collapse",
                  marginTop: 4,
                }}
              >
                <thead>
                  <tr style={{ color: "#666", textAlign: "left" }}>
                    <th style={th}>ปี</th>
                    <th style={th}>ชื่อไฟล์</th>
                    <th style={th}>ขนาด</th>
                    <th style={th}>แก้ไขล่าสุด</th>
                    <th style={th}></th>
                  </tr>
                </thead>
                <tbody>
                  {status.files.length === 0 && (
                    <tr>
                      <td colSpan={5} style={{ ...td, color: "#999", textAlign: "center" }}>
                        ยังไม่มีไฟล์ — อัพโหลดเพื่อเริ่มต้น
                      </td>
                    </tr>
                  )}
                  {status.files.map((f) => (
                    <tr key={f.name} style={{ borderTop: "1px solid #eee" }}>
                      <td style={td}><b>{f.year ?? "?"}</b></td>
                      <td style={td}>{f.name}</td>
                      <td style={td}>{fmtSize(f.size)}</td>
                      <td style={td}>{fmtDate(f.mtime)}</td>
                      <td style={{ ...td, textAlign: "right" }}>
                        <button
                          onClick={() => handleDelete(f.name)}
                          disabled={!!busy}
                          style={deleteBtn(!!busy)}
                        >
                          ลบ
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {status.data && (
                <div
                  style={{
                    marginTop: 12,
                    fontSize: 11,
                    color: "#666",
                    padding: "8px 10px",
                    background: "#fafafc",
                    borderRadius: 8,
                  }}
                >
                  {status.data.total?.toLocaleString()} งาน · {status.data.date_min} → {status.data.date_max} ·
                  {" "}สร้างเมื่อ {fmtDate(status.data.generated_at)}
                  <div style={{ marginTop: 4 }}>
                    {status.data.companies.map((c) => `${c.name} ${c.total.toLocaleString()}`).join(" · ")}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Banner({ color, bg, children }) {
  return (
    <div
      style={{
        marginTop: 12,
        padding: "10px 12px",
        background: bg,
        color,
        borderRadius: 8,
        fontSize: 12,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
    >
      {children}
    </div>
  );
}

const closeBtn = {
  background: "transparent",
  border: "none",
  fontSize: 18,
  color: "#888",
  cursor: "pointer",
  padding: 4,
};

const primaryBtn = (disabled) => ({
  background: disabled ? "#bbb" : "linear-gradient(135deg, #4d6a1f, #6fb720)",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  padding: "9px 18px",
  fontWeight: 700,
  fontSize: 13,
  cursor: disabled ? "not-allowed" : "pointer",
});

const ghostBtn = {
  background: "#fff",
  border: "1px solid #d4d4dc",
  borderRadius: 6,
  padding: "4px 10px",
  fontSize: 11,
  color: "#555",
  cursor: "pointer",
};

const deleteBtn = (disabled) => ({
  background: "transparent",
  border: "1px solid #f4b6ae",
  color: disabled ? "#aaa" : "#9c2a18",
  borderRadius: 6,
  padding: "3px 10px",
  fontSize: 11,
  cursor: disabled ? "not-allowed" : "pointer",
});

const th = { padding: "6px 8px", fontWeight: 600, fontSize: 11 };
const td = { padding: "6px 8px" };

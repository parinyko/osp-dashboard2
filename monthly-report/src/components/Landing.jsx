import React from "react";
import { navigate, companyUrl } from "../router.js";

export default function Landing({ meta, isAdmin, onUpload, onLogout, showLogout, onAdminLogin, notice }) {
  const companies = meta?.companies || [];
  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12, marginBottom: 26 }}>
        <div>
          <div style={{ fontSize: 13, color: "#6b6b78", letterSpacing: "0.08em", textTransform: "uppercase" }}>OSP · Team Performance</div>
          <div style={{ fontSize: 30, fontWeight: 800, color: "#4d6a1f" }}>Monthly Report — เลือกบริษัท</div>
          {meta?.date_max && (
            <div style={{ fontSize: 12, color: "#8b8b96", marginTop: 4 }}>
              ข้อมูล {meta.date_min} → {meta.date_max} · รวม {meta.total?.toLocaleString()} งาน · อัปเดต {meta.generated_at?.replace("T", " ")}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {isAdmin && (
            <button onClick={onUpload} style={btn("#2C7A4D")}>📥 Upload Excel</button>
          )}
          {showLogout && (
            <button onClick={onLogout} style={btn("#777")}>ออกจากระบบ</button>
          )}
          {onAdminLogin && (
            <button onClick={onAdminLogin} style={btn("#777")}>🔑 Admin</button>
          )}
        </div>
      </div>

      {notice && (
        <div style={{ background: "#fff8e1", color: "#856404", padding: "10px 14px", borderRadius: 8, marginBottom: 16, fontSize: 13 }}>
          {notice}
        </div>
      )}

      {companies.length === 0 ? (
        <div style={{ background: "#fff", border: "1px dashed #d4d4dc", borderRadius: 14, padding: 50, textAlign: "center", color: "#888" }}>
          ยังไม่มีข้อมูล {isAdmin ? "— กด Upload Excel เพื่อเริ่มต้น" : "— รอผู้ดูแลอัปโหลดไฟล์ Excel"}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 18 }}>
          {companies.map((c) => (
            <button
              key={c.slug}
              onClick={() => navigate(companyUrl(c.slug))}
              style={{
                textAlign: "left",
                background: "#fff",
                border: "1px solid #e6e6ea",
                borderRadius: 14,
                padding: "20px 22px",
                cursor: "pointer",
                boxShadow: "0 4px 14px rgba(0,0,0,0.05)",
                borderTop: "4px solid #7CC242",
                fontFamily: "inherit",
              }}
            >
              <div style={{ fontSize: 18, fontWeight: 800, color: "#1f1f2c" }}>{c.name}</div>
              <div style={{ fontSize: 30, fontWeight: 800, color: "#4d6a1f", marginTop: 8 }}>
                {c.total.toLocaleString()} <span style={{ fontSize: 13, color: "#8b8b96", fontWeight: 600 }}>งาน</span>
              </div>
              <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
                {c.zones.length} โซน · {c.zones.map((z) => z.name).join(" · ")}
              </div>
              <div style={{ fontSize: 11, color: "#9a9aaf", marginTop: 4 }}>
                {c.date_min} → {c.date_max}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const btn = (color) => ({
  background: "#fff",
  color,
  border: `1px solid ${color}55`,
  borderRadius: 8,
  padding: "10px 14px",
  fontWeight: 700,
  fontSize: 13,
  cursor: "pointer",
});

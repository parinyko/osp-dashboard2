import React, { useCallback, useEffect, useState } from "react";
import { api, invalidate, onUnauthorized, BASE } from "./data.js";

export function useAuth() {
  const [state, setState] = useState({ loading: true, role: null, auth: true });

  const refresh = useCallback(async () => {
    try {
      const me = await api("/api/me");
      setState({ loading: false, role: me.role, auth: me.auth });
    } catch {
      setState({ loading: false, role: null, auth: true });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Any API call answered 401 (session expired) drops back to the login screen.
  useEffect(() => onUnauthorized(() => setState((s) => ({ ...s, role: null }))), []);

  const login = async (password) => {
    const out = await api("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    invalidate();
    setState((s) => ({ ...s, role: out.role }));
  };

  const logout = async () => {
    await fetch(BASE + "/api/logout", { method: "POST" }).catch(() => {});
    invalidate();
    await refresh();
  };

  return { ...state, login, logout };
}

export function LoginScreen({ onLogin, onCancel }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!pw || busy) return;
    setBusy(true);
    setErr(null);
    try {
      await onLogin(pw);
    } catch (e2) {
      setErr(String(e2.message || e2));
      setBusy(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <form
        onSubmit={submit}
        style={{
          background: "#fff",
          borderRadius: 16,
          padding: "34px 36px",
          width: "min(400px, 100%)",
          boxShadow: "0 16px 50px rgba(0,0,0,0.12)",
          border: "1px solid #ececef",
        }}
      >
        <div style={{ fontSize: 13, color: "#6b6b78", letterSpacing: "0.08em", textTransform: "uppercase" }}>OSP</div>
        <div style={{ fontSize: 24, fontWeight: 800, color: "#4d6a1f", margin: "4px 0 22px" }}>Monthly Report</div>
        <label style={{ fontSize: 12, color: "#666" }}>รหัสผ่าน</label>
        <input
          type="password"
          autoFocus
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          style={{ width: "100%", boxSizing: "border-box", padding: "11px 12px", border: "1px solid #d4d4dc", borderRadius: 8, fontSize: 15, marginTop: 6 }}
        />
        {err && <div style={{ color: "#c0392b", fontSize: 12, marginTop: 10 }}>⚠️ {err}</div>}
        <button
          type="submit"
          disabled={busy || !pw}
          style={{
            width: "100%",
            marginTop: 18,
            padding: "11px 0",
            border: "none",
            borderRadius: 8,
            background: busy || !pw ? "#b9c79c" : "linear-gradient(135deg, #4d6a1f, #6fb720)",
            color: "#fff",
            fontWeight: 700,
            fontSize: 14,
            cursor: busy || !pw ? "not-allowed" : "pointer",
          }}
        >
          {busy ? "กำลังเข้าสู่ระบบ…" : "เข้าสู่ระบบ"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} style={{ width: "100%", marginTop: 10, padding: "9px 0", border: "1px solid #d4d4dc", borderRadius: 8, background: "#fff", color: "#666", cursor: "pointer", fontSize: 13 }}>
            ← กลับไปดูรายงาน
          </button>
        )}
      </form>
    </div>
  );
}

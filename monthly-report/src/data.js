import { useEffect, useReducer } from "react";

// Tiny fetch cache shared by every component: one request per key, results kept
// until invalidate() (after an upload, a settings save, or logout).

const UNAUTHORIZED = "osp:unauthorized";

// "" in dev, "/monthly" in production (vite `base`).
export const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

export async function api(path, opts = {}) {
  const r = await fetch(BASE + path, { cache: "no-store", credentials: "same-origin", ...opts });
  // A 401 from the login call itself is just a wrong password — show its message.
  // Signed out of the OSP dashboard (shared sign-in): go to its login page.
  if (r.status === 401) {
    const j = await r.clone().json().catch(() => null);
    if (j && j.login_url) {
      window.location.href = j.login_url;
      throw new Error("กรุณาเข้าสู่ระบบ");
    }
  }
  if (r.status === 401 && path !== "/api/login") {
    window.dispatchEvent(new Event(UNAUTHORIZED));
    throw new Error("กรุณาเข้าสู่ระบบ");
  }
  if (!r.ok) {
    let msg = `${path} → ${r.status}`;
    try {
      const j = await r.json();
      if (j?.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* not json */
    }
    throw new Error(msg);
  }
  return r.json();
}

export function onUnauthorized(cb) {
  window.addEventListener(UNAUTHORIZED, cb);
  return () => window.removeEventListener(UNAUTHORIZED, cb);
}

const store = new Map(); // key -> { status, value, error }
const subscribers = new Set();
const notify = () => subscribers.forEach((f) => f());

function ensure(key, loader) {
  let e = store.get(key);
  if (e) return e;
  e = { status: "loading" };
  store.set(key, e);
  loader().then(
    (v) => {
      if (store.get(key) !== e) return; // invalidated meanwhile
      e.status = "ok";
      e.value = v;
      notify();
    },
    (err) => {
      if (store.get(key) !== e) return;
      e.status = "error";
      e.error = err;
      notify();
    }
  );
  return e;
}

export function useResource(key, loader) {
  const [, rerender] = useReducer((x) => x + 1, 0);
  useEffect(() => {
    subscribers.add(rerender);
    return () => subscribers.delete(rerender);
  }, []);
  if (!key) return { loading: false, data: null, error: null };
  const e = ensure(key, loader);
  return { loading: e.status === "loading", data: e.value ?? null, error: e.error ?? null };
}

export function invalidate(prefix = "") {
  for (const k of [...store.keys()]) if (k.startsWith(prefix)) store.delete(k);
  notify();
}

export const useCompanies = () => useResource("companies", () => api("/api/companies"));
export const useSettings = () => useResource("settings", () => api("/api/settings"));
export const useCompanyData = (slug) =>
  useResource(slug ? `data:${slug}` : null, () => api(`/api/data/${encodeURIComponent(slug)}`));

import { useEffect, useState } from "react";
import { BASE } from "./data.js";

// Minimal client-side router.
//   /                    company picker
//   /c/<slug>            a company's report (first page)
//   /c/<slug>/<pageId>   a specific page of it

const EVENT = "osp:navigate";

// Paths inside the app are written without the base ("/c/dmp"); the browser URL has it.
const strip = (p) => (BASE && p.startsWith(BASE) ? p.slice(BASE.length) || "/" : p);

export function navigate(path, { replace = false } = {}) {
  const full = BASE + path;
  if (window.location.pathname === full) return;
  window.history[replace ? "replaceState" : "pushState"]({}, "", full);
  window.dispatchEvent(new Event(EVENT));
}

export function usePath() {
  const [path, setPath] = useState(() => strip(window.location.pathname));
  useEffect(() => {
    const onChange = () => setPath(strip(window.location.pathname));
    window.addEventListener("popstate", onChange);
    window.addEventListener(EVENT, onChange);
    return () => {
      window.removeEventListener("popstate", onChange);
      window.removeEventListener(EVENT, onChange);
    };
  }, []);
  return path;
}

export function parseRoute(path) {
  const m = path.match(/^\/c\/([^/]+)(?:\/([^/]+))?\/?$/);
  if (!m) return { kind: "home" };
  const dec = (s) => {
    try {
      return decodeURIComponent(s);
    } catch {
      return s;
    }
  };
  return { kind: "company", slug: dec(m[1]), pageId: m[2] ? dec(m[2]) : null };
}

export const companyUrl = (slug, pageId) =>
  `/c/${encodeURIComponent(slug)}${pageId ? `/${encodeURIComponent(pageId)}` : ""}`;

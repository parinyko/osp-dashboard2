import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 127.0.0.1, not "localhost": on macOS that may resolve to ::1 where another
// project's dev server can be listening on the same port.
const BACKEND = process.env.OSP_BACKEND || "http://127.0.0.1:8795";
// Production lives under /monthly on the dashboard's domain (OSP_BASE_PATH at build time).
const BASE = (process.env.OSP_BASE_PATH || "").replace(/\/$/, "") + "/";

export default defineConfig({
  base: BASE,
  plugins: [react()],
  server: {
    port: 5190,          // fixed + strict: 5173/5180 are used by other projects on this Mac
    strictPort: true,
    host: true,
    proxy: {
      [`${BASE}api`]: { target: BACKEND, changeOrigin: true },
    },
  },
});

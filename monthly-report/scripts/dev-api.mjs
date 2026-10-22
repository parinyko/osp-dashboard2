// Runs the FastAPI backend with auto-reload for `npm run dev:server` / `dev:all`.
// A plain npm script can't name the venv python on every OS: it lives at
// server/.venv/bin/python on macOS/Linux but server\.venv\Scripts\python.exe on Windows.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const python =
  process.platform === "win32"
    ? path.join("server", ".venv", "Scripts", "python.exe")
    : path.join("server", ".venv", "bin", "python");

if (!existsSync(python)) {
  console.error(
    `Missing ${python}. Create it first:\n` +
      "  python3 -m venv server/.venv && server/.venv/bin/pip install -r server/requirements.txt"
  );
  process.exit(1);
}

const child = spawn(python, ["-m", "uvicorn", "server.app:app", "--port", "8795", "--reload"], {
  stdio: "inherit",
});
child.on("exit", (code) => process.exit(code ?? 0));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));

// Dev-only visual annotation harness — the main-process half.
//
// Loaded from src/main/index.js via a dynamic import inside a !app.isPackaged
// guard (and guarded again here), so no packaged build ever evaluates a line
// of it. It injects dev/annotator/overlay.js into the rendered dashboard and
// answers the overlay's one IPC call: capture the page pixel-identical with
// webContents.capturePage() and write the pair into <repo root>/.annotations/.

import { app, ipcMain } from "electron";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const KEEP = 30; // timestamped capture pairs retained after pruning

export function registerAnnotator(win, { baseUrl, projectRoot }) {
  if (app.isPackaged) return;

  const dir = path.join(projectRoot, ".annotations");
  const overlayFile = path.join(here, "overlay.js");
  const log = (...args) => console.log("[meelu:annotator]", ...args);

  const allowedSender = (ev) => {
    const url = ev.senderFrame?.url ?? "";
    return url === baseUrl || url.startsWith(`${baseUrl}/`);
  };

  ipcMain.removeHandler("annotator:capture");
  ipcMain.handle("annotator:capture", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      // The overlay has already hidden its own chrome and waited for the
      // repaint; the user's markup stays in the page and lands in the pixels.
      const image = await win.webContents.capturePage();
      const png = image.toPNG();
      fs.mkdirSync(dir, { recursive: true });
      const stamp = new Date().toISOString().replace(/\.\d{3}Z$/, "Z").replace(/:/g, "-");
      fs.writeFileSync(path.join(dir, `${stamp}.png`), png);
      const md = String(payload?.markdown ?? "").replaceAll("{{IMAGE}}", `${stamp}.png`);
      fs.writeFileSync(path.join(dir, `${stamp}.md`), md);
      fs.writeFileSync(path.join(dir, "latest.png"), png);
      fs.writeFileSync(path.join(dir, "latest.md"), md.replaceAll(`${stamp}.png`, "latest.png"));
      prune(dir);
      log("saved", `${stamp}.md`);
      return { ok: true, mdPath: `.annotations/${stamp}.md`, pngPath: `.annotations/${stamp}.png` };
    } catch (err) {
      return { error: err instanceof Error ? err.message : "capture failed" };
    }
  });

  // Re-inject on every real page load (SPA navigation keeps the overlay
  // alive in between). Read from disk each time so overlay edits apply on a
  // plain reload. Skipped for the waiting page / anything off-origin.
  const inject = () => {
    const url = win.webContents.getURL();
    if (!(url === baseUrl || url.startsWith(`${baseUrl}/`))) return;
    let src;
    try {
      src = fs.readFileSync(overlayFile, "utf8");
    } catch (err) {
      return log("overlay missing:", err.message);
    }
    win.webContents
      .executeJavaScript(`window.__MEELU_ANNOTATOR_DEV = true;\n${src}\ntrue;`, true)
      .then(() => log("overlay ready — Ctrl/Cmd+Shift+A to annotate"))
      .catch((err) => log("inject failed:", err.message));
  };
  win.webContents.on("did-finish-load", inject);
  if (!win.webContents.isLoading()) inject();
}

/** Keep the newest KEEP timestamped pairs; latest.* aliases are never pruned. */
function prune(dir) {
  const stamps = [...new Set(
    fs.readdirSync(dir)
      .filter((f) => /^\d{4}-\d{2}-\d{2}T.+\.(png|md)$/.test(f))
      .map((f) => f.replace(/\.(png|md)$/, "")),
  )].sort().reverse();
  for (const stale of stamps.slice(KEEP)) {
    for (const ext of [".png", ".md"]) {
      fs.rmSync(path.join(dir, stale + ext), { force: true });
    }
  }
}

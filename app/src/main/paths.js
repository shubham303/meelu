import fs from "node:fs";
import path from "node:path";
import { app } from "electron";

export function appRoot() {
  return app.getPath("userData");
}

export function appDir(...segments) {
  const dir = path.join(appRoot(), ...segments);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function appFile(...segments) {
  return path.join(appRoot(), ...segments);
}

export function screenshotDir() {
  return app.getPath("desktop");
}

export function saveDialogDir() {
  return app.getPath("downloads");
}

export function writeSecretFile(file, data) {
  fs.writeFileSync(file, data, { mode: 0o600 });
}

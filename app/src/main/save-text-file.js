import fs from "node:fs";
import path from "node:path";
import { dialog } from "electron";
import { saveDialogDir } from "./paths.js";

export async function saveTextFile({ name, content }) {
  if (typeof content !== "string" || content === "") throw new Error("There is nothing to save.");
  const safeName = String(name || "meelu-export").replace(/[/\\:*?"<>|]/g, "-").slice(0, 120);
  const { canceled, filePath } = await dialog.showSaveDialog({
    defaultPath: path.join(saveDialogDir(), safeName),
  });
  if (canceled || !filePath) return { canceled: true };
  fs.writeFileSync(filePath, content, "utf8");
  return { ok: true, path: filePath };
}

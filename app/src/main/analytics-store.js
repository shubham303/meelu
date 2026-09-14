import fs from "node:fs";
import path from "node:path";
import { dialog, shell } from "electron";
import { appFile, saveDialogDir } from "./paths.js";

const MAX_SOURCE_ROWS = 1_000_000;

function analyticsDir() {
  return appFile("analytics");
}

const ID = /^[A-Za-z0-9_-]{1,64}$/;

function safeId(id) {
  if (typeof id !== "string" || !ID.test(id)) {
    throw new Error("Bad id.");
  }
  return id;
}

function relativeSourcePath(sessionId, sourceId) {
  return `sessions/${safeId(sessionId)}/sources/${safeId(sourceId)}.csv`;
}

function absolute(relativePath) {
  if (typeof relativePath !== "string" || relativePath.trim() === "") {
    throw new Error("Bad path.");
  }
  const parts = relativePath.replace(/\\/g, "/").split("/").filter((p) => p !== "" && p !== ".");
  if (parts.some((p) => p === "..") || path.isAbsolute(relativePath)) {
    throw new Error("Bad path.");
  }
  return path.join(analyticsDir(), ...parts);
}

export function saveSource({ sessionId, sourceId, content }) {
  if (typeof content !== "string" || content.trim() === "") {
    throw new Error("The file is empty.");
  }
  const lines = content.split(/\r?\n/).filter((l) => l.trim() !== "");
  const rowCount = Math.max(0, lines.length - 1);
  if (rowCount > MAX_SOURCE_ROWS) {
    throw new Error(
      `This file has ${rowCount.toLocaleString("en-US")} data rows — the limit is ${MAX_SOURCE_ROWS.toLocaleString("en-US")}. Split it or pre-aggregate first.`,
    );
  }
  if (rowCount === 0) throw new Error("The file has a header but no data rows.");

  const relativePath = relativeSourcePath(sessionId, sourceId);
  const file = absolute(relativePath);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content, "utf8");
  return { relativePath, bytes: Buffer.byteLength(content, "utf8") };
}

function engineState(sessionKey) {
  if (!sessionKey) return "none";
  if (typeof sessionKey !== "string" || !ID.test(sessionKey)) return "missing";
  const db = path.join(analyticsDir(), ".tableint", "sessions", sessionKey, "data.duckdb");
  return fs.existsSync(db) ? "present" : "missing";
}

export function checkSession({ sessionKey, paths }) {
  const missing = resolvePaths({ paths })
    .filter((s) => s.missing)
    .map((s) => s.relativePath);
  const engine = engineState(sessionKey);
  return { engine, missing, ok: engine !== "missing" && missing.length === 0 };
}

export function resolvePaths({ paths }) {
  if (!Array.isArray(paths)) return [];
  return paths.map((relativePath) => {
    try {
      const file = absolute(relativePath);
      return { relativePath, path: file, missing: !fs.existsSync(file) };
    } catch {
      return { relativePath, path: null, missing: true };
    }
  });
}

const PREVIEW_BYTES = 2 * 1024 * 1024;
const PREVIEW_CELL = 400;

function parseRecords(text, maxRecords) {
  const records = [];
  let record = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (quoted) {
      if (c !== '"') {
        field += c;
      } else if (text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else {
        quoted = false;
      }
      continue;
    }
    if (c === '"') {
      quoted = true;
    } else if (c === ",") {
      record.push(field);
      field = "";
    } else if (c === "\n") {
      record.push(field);
      field = "";
      records.push(record);
      record = [];
      if (records.length >= maxRecords) return records;
    } else if (c !== "\r") {
      field += c;
    }
  }
  if (field !== "" || record.length > 0) {
    record.push(field);
    records.push(record);
  }
  return records;
}

function clip(value) {
  return value.length > PREVIEW_CELL ? `${value.slice(0, PREVIEW_CELL)}…` : value;
}

export function readSource({ relativePath, limit = 200 }) {
  const file = absolute(relativePath);
  const stat = fs.statSync(file);
  const length = Math.min(stat.size, PREVIEW_BYTES);
  const buffer = Buffer.alloc(length);
  const fd = fs.openSync(file, "r");
  try {
    fs.readSync(fd, buffer, 0, length, 0);
  } finally {
    fs.closeSync(fd);
  }

  const rowLimit = Math.max(1, Math.min(Number(limit) || 200, 1000));
  const clipped = length < stat.size;
  const records = parseRecords(buffer.toString("utf8"), rowLimit + 2 + (clipped ? 1 : 0));
  if (clipped && records.length > 0) records.pop();

  const [header = [], ...body] = records;
  return {
    name: path.basename(file),
    path: file,
    bytes: stat.size,
    columns: header.map(clip),
    rows: body.slice(0, rowLimit).map((r) => r.map(clip)),
    more: clipped || body.length > rowLimit,
  };
}

export function revealSource({ relativePath }) {
  const file = absolute(relativePath);
  if (!fs.existsSync(file)) throw new Error("That file is not on this machine any more.");
  shell.showItemInFolder(file);
  return { ok: true };
}

export async function exportSource({ relativePath }) {
  const file = absolute(relativePath);
  if (!fs.existsSync(file)) throw new Error("That file is not on this machine any more.");
  const { canceled, filePath } = await dialog.showSaveDialog({
    defaultPath: path.join(saveDialogDir(), path.basename(file)),
  });
  if (canceled || !filePath) return { canceled: true };
  fs.copyFileSync(file, filePath);
  return { ok: true, path: filePath };
}

export async function exportText({ name, content }) {
  if (typeof content !== "string" || content === "") throw new Error("There is nothing to save.");
  const safeName = String(name || "meelu-export").replace(/[/\\:*?"<>|]/g, "-").slice(0, 120);
  const { canceled, filePath } = await dialog.showSaveDialog({
    defaultPath: path.join(saveDialogDir(), safeName),
  });
  if (canceled || !filePath) return { canceled: true };
  fs.writeFileSync(filePath, content, "utf8");
  return { ok: true, path: filePath };
}

export function deleteSource({ relativePath }) {
  const file = absolute(relativePath);
  if (!file.startsWith(path.join(analyticsDir(), "sessions") + path.sep)) {
    return { ok: true, kept: true };
  }
  if (fs.existsSync(file)) fs.unlinkSync(file);
  return { ok: true };
}

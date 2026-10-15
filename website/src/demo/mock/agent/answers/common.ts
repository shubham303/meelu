import type { SitePage } from "@demo/lib/types";
import { ORIGIN, PAGE_BY_PATH, pageId } from "../../data/site";

export type Step =
  | { kind: "tool"; name: string; ms?: number }
  | { kind: "progress"; tool: string; total: number }
  | { kind: "text"; text: string }
  | {
      kind: "write";
      tool: string;
      input: Record<string, unknown>;
      apply: () => void;
      created?: boolean;
      after: string | (() => string);
      declined: string;
    };

export interface Memory {
  action: string;
  turns: number;
  pending: ((ctx: Ctx) => Step[]) | null;
  awaiting: ((ctx: Ctx) => Step[]) | null;
  lastAnswer: string;
  data: Record<string, unknown>;
}

export interface Ctx {
  action: string;
  message: string;
  lower: string;
  siteId: string | null;
  form: Record<string, string | undefined>;
  sessionId: string;
  memory: Memory;
}

export type Script = Step[];

export const tool = (name: string, ms?: number): Step => ({ kind: "tool", name, ms });
export const text = (t: string): Step => ({ kind: "text", text: t });
export const tools = (...names: string[]): Step[] => names.map((n) => tool(n));

export function lines(...parts: string[]): string {
  return parts.join("\n");
}

export function isYes(lower: string): boolean {
  const t = lower.trim().replace(/[.!]+$/, "");
  return (
    /^(y|yes|yep|yeah|yup|sure|ok|okay|go|go ahead|do it|please do|please|agreed|agree|sounds good|looks good|lgtm|ship it|confirm|confirmed|approve|approved|save|save it|save them|save those|add them|track them|correct|perfect|great)\b/.test(t) ||
    /\b(go ahead|save (it|them|those|all)|do it|yes please|that works|looks right)\b/.test(t)
  );
}

export function isNo(lower: string): boolean {
  return /^(no|nope|nah|don't|do not|stop|cancel|not now|skip|leave it)\b/.test(lower.trim());
}

export function quoted(message: string): string | null {
  const m = message.match(/["“]([^"”]{2,120})["”]/);
  return m ? m[1].trim() : null;
}

export function page(path: string): { id: string; url: string; title: string; page: SitePage | undefined } {
  const p = PAGE_BY_PATH.get(path);
  return { id: p?.id ?? pageId(path), url: p?.url ?? `${ORIGIN}${path}`, title: p?.title ?? path, page: p };
}

export function link(path: string): string {
  return `[${path}](${ORIGIN}${path})`;
}

export function cap(s: string): string {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

export function topicFrom(message: string): string {
  const q = quoted(message);
  if (q) return q;
  return message
    .replace(/^(i will name|my topic is|topic:|the topic is|about|it's|it is|page:|the page is)\s*/i, "")
    .replace(/[?.!]+$/, "")
    .trim()
    .slice(0, 80);
}

export function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function chartBars(title: string, rows: Array<[string, number]>, unit = ""): string {
  const max = Math.max(...rows.map(([, v]) => Math.abs(v)), 1);
  const rowH = 26;
  const labelW = 210;
  const barW = 300;
  const h = rows.length * rowH + 40;
  const bars = rows
    .map(([label, v], i) => {
      const w = Math.round((Math.abs(v) / max) * barW);
      const y = 30 + i * rowH;
      const color = v < 0 ? "#c2410c" : "#0f766e";
      const shown = `${v > 0 && unit !== "" ? "+" : ""}${v.toLocaleString("en-US")}${unit}`;
      return `<text x="${labelW - 8}" y="${y + 13}" text-anchor="end" font-size="12" fill="#334155">${label}</text><rect x="${labelW}" y="${y}" width="${w}" height="18" rx="3" fill="${color}"/><text x="${labelW + w + 6}" y="${y + 13}" font-size="12" fill="#334155">${shown}</text>`;
    })
    .join("");
  return `<div style="font-family:system-ui,sans-serif;padding:8px"><svg viewBox="0 0 600 ${h}" width="100%" role="img" aria-label="${title}"><text x="0" y="16" font-size="13" font-weight="600" fill="#0f172a">${title}</text>${bars}</svg></div>`;
}

export function chartLine(title: string, series: Array<{ name: string; color: string; dashed?: boolean; start?: number; points: number[] }>, labels: string[]): string {
  const w = 600;
  const h = 240;
  const pad = { l: 44, r: 12, t: 28, b: 28 };
  const all = series.flatMap((s) => s.points);
  const max = Math.max(...all) * 1.1;
  const min = Math.min(0, ...all);
  const n = Math.max(labels.length, ...series.map((s) => s.points.length + (s.start ?? 0)));
  const x = (i: number) => pad.l + (i / Math.max(1, n - 1)) * (w - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - (v - min) / (max - min || 1)) * (h - pad.t - pad.b);
  const paths = series
    .map((s) => {
      const d = s.points.map((v, i) => `${i === 0 ? "M" : "L"}${x(i + (s.start ?? 0)).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
      return `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2"${s.dashed ? ' stroke-dasharray="5 4"' : ""}/>`;
    })
    .join("");
  const grid = [0, 0.5, 1]
    .map((f) => {
      const v = min + f * (max - min);
      return `<line x1="${pad.l}" x2="${w - pad.r}" y1="${y(v)}" y2="${y(v)}" stroke="#e2e8f0"/><text x="${pad.l - 6}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="#64748b">${Math.round(v).toLocaleString("en-US")}</text>`;
    })
    .join("");
  const ticks = labels
    .map((l, i) => (i % Math.ceil(labels.length / 6) === 0 ? `<text x="${x(i)}" y="${h - 8}" text-anchor="middle" font-size="11" fill="#64748b">${l}</text>` : ""))
    .join("");
  const legend = series
    .map((s, i) => `<rect x="${pad.l + i * 140}" y="8" width="10" height="10" fill="${s.color}"/><text x="${pad.l + 14 + i * 140}" y="17" font-size="11" fill="#334155">${s.name}</text>`)
    .join("");
  return `<div style="font-family:system-ui,sans-serif;padding:8px"><svg viewBox="0 0 ${w} ${h}" width="100%" role="img" aria-label="${title}">${legend}${grid}${paths}${ticks}</svg></div>`;
}

export function fence(lang: string, body: string): string {
  return "```" + lang + "\n" + body + "\n```";
}

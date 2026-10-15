import { ago, DAY, HOUR, NOW } from "./rand";

export class MockHttpError extends Error {
  constructor(
    public status: number,
    message: string,
    public extra: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

let counter = 100;
export function newId(prefix: string): string {
  counter += 1;
  return `${prefix}_${counter.toString(36)}`;
}

export function now(): string {
  return new Date().toISOString();
}

export function paginate<T>(list: T[], q: URLSearchParams, extra: Record<string, unknown> = {}) {
  const page = Math.max(1, Number(q.get("page") ?? 1));
  const size = Math.max(1, Number(q.get("page_size") ?? q.get("pageSize") ?? 50));
  const total = list.length;
  const totalPages = Math.max(1, Math.ceil(total / size));
  return {
    ...extra,
    data: list.slice((page - 1) * size, page * size),
    pagination: { page, page_size: size, total, total_pages: totalPages, has_next: page < totalPages, has_prev: page > 1 },
  };
}

export function ok(data: unknown) {
  return { data };
}

export function num(v: string | null): number | null {
  if (v === null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}


export function slice<T>(rows: T[], q: URLSearchParams): T[] {
  const limit = num(q.get("limit")) ?? 20;
  const offset = num(q.get("offset")) ?? 0;
  return rows.slice(offset, offset + limit);
}

export type Handler = (m: RegExpMatchArray, q: URLSearchParams, body: Record<string, unknown>) => unknown;
export type Route = [string, RegExp, Handler];

export const b = (body: Record<string, unknown>, key: string) => body[key];

export const demoTimes = { ago, DAY, HOUR, NOW };

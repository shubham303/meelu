/**
 * A CSV reader and writer shared by every tool that takes a file upload.
 *
 * Nothing here touches the DOM or Node, so it runs in a browser, a worker or on
 * the server unchanged. Everything is synchronous: even a twenty-thousand-row
 * file parses in a few milliseconds, and a callback API would only add
 * ceremony.
 */

/** Default row cap. Past this the browser tab, not the parser, is the limit. */
export const DEFAULT_MAX_ROWS = 20000;

const DELIMITERS = [",", ";", "\t", "|"] as const;

export interface ParsedCsv {
  headers: string[];
  rows: string[][];
  /** The delimiter that was sniffed, for the "we read this as…" line. */
  delimiter: string;
  /** True when the file had more rows than the cap allowed. */
  truncated: boolean;
  /** Data rows in the file, before the cap and excluding the header. */
  totalRows: number;
}

/**
 * Pick the delimiter by counting candidates outside quoted fields on the first
 * few lines. Sniffing beats asking: exports from Google Sheets, Excel in a
 * European locale and most CRMs all disagree, and nobody wants a dropdown.
 */
function sniffDelimiter(sample: string): string {
  let best = ",";
  let bestScore = -1;

  for (const candidate of DELIMITERS) {
    let inQuotes = false;
    let count = 0;
    let lines = 0;

    for (let i = 0; i < sample.length && lines < 5; i += 1) {
      const char = sample[i];
      if (char === '"') {
        if (inQuotes && sample[i + 1] === '"') i += 1;
        else inQuotes = !inQuotes;
      } else if (!inQuotes && char === candidate) {
        count += 1;
      } else if (!inQuotes && char === "\n") {
        lines += 1;
      }
    }

    if (count > bestScore) {
      bestScore = count;
      best = candidate;
    }
  }

  return best;
}

/**
 * RFC 4180 parser. Handles quoted fields, escaped quotes, newlines inside
 * fields and all three line endings — real exports contain every one of them,
 * and a naive split on commas mangles the first cell that contains a comma.
 */
export function parseCsv(input: string, maxRows = DEFAULT_MAX_ROWS): ParsedCsv {
  // Excel prefixes its CSV exports with a byte-order mark.
  const text = input.replace(/^﻿/, "");
  const delimiter = sniffDelimiter(text.slice(0, 8000));

  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;
  let truncated = false;
  let totalRows = 0;

  const endField = () => {
    row.push(field);
    field = "";
  };

  const endRow = () => {
    endField();
    const empty = row.length === 1 && row[0].trim() === "";
    if (!empty) {
      totalRows += 1;
      if (rows.length <= maxRows) rows.push(row);
      else truncated = true;
    }
    row = [];
  };

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];

    if (inQuotes) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"' && field.length === 0) {
      inQuotes = true;
    } else if (char === delimiter) {
      endField();
    } else if (char === "\r") {
      if (text[i + 1] === "\n") i += 1;
      endRow();
    } else if (char === "\n") {
      endRow();
    } else {
      field += char;
    }
  }

  if (field.length > 0 || row.length > 0) endRow();

  const headers = rows.shift() ?? [];
  if (rows.length > maxRows) {
    rows.length = maxRows;
    truncated = true;
  }

  return {
    headers: headers.map((header) => header.trim()),
    rows,
    delimiter,
    truncated,
    totalRows: Math.max(0, totalRows - 1),
  };
}

export function normalizeHeader(header: string): string {
  return header.toLowerCase().replace(/[\s_-]+/g, " ").trim();
}

/**
 * Find the column whose header best matches a list of hints, preferring an
 * exact match over a substring one. Returns -1 when nothing matches.
 */
export function findColumn(headers: string[], hints: string[]): number {
  const names = headers.map(normalizeHeader);
  for (const hint of hints) {
    const exact = names.indexOf(hint);
    if (exact !== -1) return exact;
  }
  for (let i = 0; i < names.length; i += 1) {
    if (hints.some((hint) => names[i].includes(hint))) return i;
  }
  return -1;
}

/**
 * Read a cell as a number, tolerating the things spreadsheets put in them:
 * thousands separators, currency symbols, percent signs, parenthesised
 * negatives and stray whitespace. Returns null rather than NaN so callers have
 * to decide what an unparseable cell means.
 */
export function toNumber(raw: string | undefined): number | null {
  if (raw === undefined) return null;
  let text = raw.trim();
  if (text === "" || text === "-" || text === "—") return null;

  let negative = false;
  if (/^\(.*\)$/.test(text)) {
    negative = true;
    text = text.slice(1, -1);
  }

  const percent = text.includes("%");
  text = text.replace(/[^\d.,\-+eE]/g, "");

  // A comma is a thousands separator when a dot is also present, and a decimal
  // point otherwise — which is how European exports write 1.234,56.
  if (text.includes(",") && text.includes(".")) {
    text = text.lastIndexOf(",") > text.lastIndexOf(".")
      ? text.replace(/\./g, "").replace(",", ".")
      : text.replace(/,/g, "");
  } else if (text.includes(",")) {
    const parts = text.split(",");
    text = parts.length === 2 && parts[1].length !== 3
      ? text.replace(",", ".")
      : text.replace(/,/g, "");
  }

  const value = Number(text);
  if (!Number.isFinite(value)) return null;
  const signed = negative ? -value : value;
  return percent ? signed / 100 : signed;
}

/** Parse the date formats that turn up in analytics exports, as UTC. */
export function toDate(raw: string | undefined): Date | null {
  if (!raw) return null;
  const text = raw.trim();
  if (text === "") return null;

  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(text);
  if (iso) {
    return new Date(Date.UTC(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3])));
  }

  // GA4 exports dates as YYYYMMDD with no separators.
  const compact = /^(\d{4})(\d{2})(\d{2})$/.exec(text);
  if (compact) {
    return new Date(
      Date.UTC(Number(compact[1]), Number(compact[2]) - 1, Number(compact[3])),
    );
  }

  const slashed = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(text);
  if (slashed) {
    // Ambiguous between US and UK order. A value above 12 in the first position
    // settles it; otherwise assume US, which is what most exports emit.
    const a = Number(slashed[1]);
    const b = Number(slashed[2]);
    const [month, day] = a > 12 ? [b, a] : [a, b];
    return new Date(Date.UTC(Number(slashed[3]), month - 1, day));
  }

  const parsed = new Date(text);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** Build a CSV string. Always comma-delimited and CRLF, which Excel prefers. */
export function toCsv(headers: string[], rows: unknown[][]): string {
  return [headers, ...rows].map((row) => row.map(cell).join(",")).join("\r\n");
}

/** A filename stem from an uploaded file's name, safe on every platform. */
export function fileStem(prefix: string, name: string): string {
  const base = name.replace(/\.[^.]+$/, "").replace(/[^a-z0-9]+/gi, "-").toLowerCase();
  return `${prefix}-${base.replace(/^-+|-+$/g, "") || "data"}`;
}

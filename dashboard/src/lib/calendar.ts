import { instantAt, zonedParts, type CivilDay } from "./zoned";

export { zonedParts, type CivilDay };

export const cellInstant = instantAt;

const DAY_MS = 86_400_000;

export function rollingDays(reference: Date, tz: string): CivilDay[] {
  const p = zonedParts(reference, tz);
  const start = Date.UTC(p.year, p.month - 1, p.day);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start + i * DAY_MS);
    return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1, day: d.getUTCDate() };
  });
}

export function shiftWeeks(days: CivilDay[], weeks: number, tz: string): Date {
  const first = days[0];
  const shifted = new Date(
    Date.UTC(first.year, first.month - 1, first.day) + weeks * 7 * DAY_MS,
  );
  return cellInstant(
    {
      year: shifted.getUTCFullYear(),
      month: shifted.getUTCMonth() + 1,
      day: shifted.getUTCDate(),
    },
    12,
    tz,
  );
}

export function sameDay(a: CivilDay, b: CivilDay): boolean {
  return a.year === b.year && a.month === b.month && a.day === b.day;
}

export function hourLabel(hour: number): string {
  if (hour === 0) return "12 AM";
  if (hour === 12) return "12 PM";
  return hour < 12 ? `${hour} AM` : `${hour - 12} PM`;
}

export function dayLabel(day: CivilDay, tz: string): { weekday: string; date: string } {
  const date = cellInstant(day, 12, tz);
  return {
    weekday: date.toLocaleDateString("en-US", { timeZone: tz, weekday: "short" }),
    date: date.toLocaleDateString("en-US", { timeZone: tz, month: "short", day: "numeric" }),
  };
}

export function rangeLabel(days: CivilDay[], tz: string): string {
  const first = cellInstant(days[0], 12, tz);
  const last = cellInstant(days[days.length - 1], 12, tz);
  const sameMonth =
    days[0].month === days[days.length - 1].month && days[0].year === days[days.length - 1].year;
  const from = first.toLocaleDateString("en-US", {
    timeZone: tz,
    month: "short",
    day: "numeric",
  });
  const to = last.toLocaleDateString("en-US", {
    timeZone: tz,
    ...(sameMonth ? {} : { month: "short" }),
    day: "numeric",
  });
  const year = last.toLocaleDateString("en-US", { timeZone: tz, year: "numeric" });
  return `${from} – ${to}, ${year}`;
}

export function timeLabel(iso: string, tz: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    timeZone: tz,
    hour: "numeric",
    minute: "2-digit",
  });
}

export function dateTimeLabel(iso: string, tz: string): string {
  return new Date(iso).toLocaleString("en-US", {
    timeZone: tz,
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function localTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export interface CivilDay {
  year: number;
  month: number;
  day: number;
}

export interface ZonedParts extends CivilDay {
  hour: number;
  minute: number;
  second: number;
  weekday: number;
}

const WEEKDAY_INDEX: Record<string, number> = {
  Sun: 0,
  Mon: 1,
  Tue: 2,
  Wed: 3,
  Thu: 4,
  Fri: 5,
  Sat: 6,
};

const formatters = new Map<string, Intl.DateTimeFormat>();

function formatter(timeZone: string): Intl.DateTimeFormat {
  let f = formatters.get(timeZone);
  if (!f) {
    f = new Intl.DateTimeFormat("en-US", {
      timeZone,
      hourCycle: "h23",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      weekday: "short",
    });
    formatters.set(timeZone, f);
  }
  return f;
}

export function zonedParts(date: Date, tz: string): ZonedParts {
  const parts = formatter(tz).formatToParts(date);
  const at = (type: string) => parts.find((p) => p.type === type)?.value ?? "0";
  return {
    year: Number(at("year")),
    month: Number(at("month")),
    day: Number(at("day")),
    hour: Number(at("hour")),
    minute: Number(at("minute")),
    second: Number(at("second")),
    weekday: WEEKDAY_INDEX[at("weekday")] ?? 0,
  };
}

function offsetMs(date: Date, tz: string): number {
  const p = zonedParts(date, tz);
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - date.getTime();
}

export function instantAt(day: CivilDay, hour: number, tz: string): Date {
  const naive = Date.UTC(day.year, day.month - 1, day.day, hour);
  const first = offsetMs(new Date(naive), tz);
  const ts = naive - first;
  const second = offsetMs(new Date(ts), tz);
  return new Date(second === first ? ts : naive - second);
}

export function floorToHour(date: Date, tz: string): Date {
  const p = zonedParts(date, tz);
  return instantAt(p, p.hour, tz);
}

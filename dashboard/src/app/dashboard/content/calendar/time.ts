import { zonedParts } from "@/lib/calendar";

export {
  cellInstant,
  dateTimeLabel,
  dayLabel,
  hourLabel,
  localTimezone,
  rangeLabel,
  sameDay,
  timeLabel,
  rollingDays,
  shiftWeeks,
  zonedParts,
  type CivilDay,
} from "@/lib/calendar";

import type { CivilDay } from "@/lib/calendar";

export function slotKey(day: CivilDay, hour: number): string {
  return `${day.year}-${day.month}-${day.day}-${hour}`;
}

export function slotKeyOf(iso: string, tz: string): string {
  const p = zonedParts(new Date(iso), tz);
  return slotKey(p, p.hour);
}

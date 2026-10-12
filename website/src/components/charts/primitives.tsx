"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/**
 * Inline-SVG chart primitives shared by every tool.
 *
 * No charting library. Everything a tool needs — scales, tick marks, axes, a
 * responsive frame — in one place, so nine tools do not each reinvent a bar
 * chart with slightly different padding.
 *
 * Rules these follow, because the tools are read on phones as often as laptops:
 *  - the SVG scales with its container via a ResizeObserver, and text is drawn
 *    at real pixel size rather than being scaled up with a viewBox
 *  - every colour comes from the site tokens, never a hard-coded hex
 *  - every chart is accompanied by a table or <title> elements, so the numbers
 *    survive when the picture does not
 */

export const CHART_PAD = { top: 12, right: 14, bottom: 26, left: 44 };
export const MOBILE_WIDTH = 480;

/** Series colours, in the order a chart should reach for them. */
export const SERIES = [
  "var(--color-accent)",
  "var(--color-good)",
  "var(--color-warn)",
  "var(--color-bad)",
  "#7c3aed",
  "#0891b2",
  "#c026d3",
  "#65a30d",
] as const;

export function seriesColor(index: number): string {
  return SERIES[index % SERIES.length];
}

/** Round tick values a person would actually choose: 1, 2.5, 5, 10 × 10ⁿ. */
export function niceTicks(min: number, max: number, count = 4): number[] {
  const span = max - min;
  if (!Number.isFinite(span) || span <= 0) return [min];
  const raw = span / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const normalised = raw / magnitude;
  const step =
    (normalised >= 5 ? 10 : normalised >= 2.5 ? 5 : normalised >= 1.5 ? 2.5 : 1) * magnitude;
  const ticks: number[] = [];
  for (let value = Math.ceil(min / step) * step; value <= max + step * 1e-9; value += step) {
    ticks.push(Number(value.toPrecision(12)));
  }
  return ticks;
}

/** Compact number formatting for axis labels and dense tables. */
export function compact(value: number, currency = false): string {
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  const unit = currency ? "" : "";
  if (abs >= 1_000_000_000) return `${sign}${unit}${(abs / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${sign}${unit}${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`;
  if (abs >= 1_000) return `${sign}${unit}${(abs / 1_000).toFixed(abs >= 10_000 ? 0 : 1)}k`;
  if (abs >= 10) return `${sign}${unit}${Math.round(abs)}`;
  if (abs === 0) return "0";
  return `${sign}${unit}${abs.toFixed(abs < 1 ? 2 : 1)}`;
}

export function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

/** Track a container's width so the SVG can be drawn at real pixel size. */
export function useChartWidth(fallback = 720): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(fallback);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new ResizeObserver(([entry]) => {
      setWidth(Math.max(280, Math.round(entry.contentRect.width)));
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return [ref, width];
}

export interface Scale {
  (value: number): number;
  domain: [number, number];
  range: [number, number];
  ticks: (count?: number) => number[];
}

export function linearScale(
  domain: [number, number],
  range: [number, number],
): Scale {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;

  const scale = ((value: number) => r0 + ((value - d0) / span) * (r1 - r0)) as Scale;
  scale.domain = domain;
  scale.range = range;
  scale.ticks = (count = 4) => niceTicks(d0, d1, count);
  return scale;
}

/** Pad a domain so the extremes are not glued to the frame. */
export function padDomain(
  min: number,
  max: number,
  fraction = 0.08,
  zeroFloor = false,
): [number, number] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
  if (min === max) return min === 0 ? [0, 1] : [min - Math.abs(min) * 0.1, max + Math.abs(max) * 0.1];
  const pad = (max - min) * fraction;
  const low = zeroFloor ? Math.min(0, min) : min - pad;
  return [zeroFloor && min >= 0 ? 0 : low, max + pad];
}

/**
 * The frame every chart sits in: a sized container, the SVG, gridlines and
 * both axes. Children are drawn in the plot area with the scales already set.
 */
export function ChartFrame({
  height,
  x,
  y,
  xTicks,
  yTicks,
  formatY = (value: number) => compact(value),
  pad = CHART_PAD,
  width,
  children,
  yLabel,
}: {
  height: number;
  width: number;
  x?: Scale;
  y: Scale;
  xTicks?: Array<{ value: number; label: string }>;
  yTicks?: number[];
  formatY?: (value: number) => string;
  pad?: typeof CHART_PAD;
  children: React.ReactNode;
  yLabel?: string;
}) {
  const ticksY = yTicks ?? y.ticks(height < 200 ? 3 : 4);
  const plotLeft = pad.left;
  const plotRight = width - pad.right;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      className="block overflow-visible"
    >
      {ticksY.map((tick) => {
        const py = y(tick);
        if (!Number.isFinite(py)) return null;
        return (
          <g key={`gy-${tick}`}>
            <line
              x1={plotLeft}
              x2={plotRight}
              y1={py}
              y2={py}
              stroke="var(--color-edge)"
              strokeWidth={1}
            />
            <text
              x={plotLeft - 6}
              y={py}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-[var(--color-faint)] font-mono text-[10px]"
            >
              {formatY(tick)}
            </text>
          </g>
        );
      })}

      {xTicks?.map((tick) => (
        <text
          key={`gx-${tick.value}-${tick.label}`}
          x={x ? x(tick.value) : tick.value}
          y={height - pad.bottom + 14}
          textAnchor="middle"
          className="fill-[var(--color-faint)] font-mono text-[10px]"
        >
          {tick.label}
        </text>
      ))}

      {yLabel ? (
        <text
          x={plotLeft - 6}
          y={pad.top - 4}
          textAnchor="end"
          className="fill-[var(--color-faint)] font-mono text-[9px]"
        >
          {yLabel}
        </text>
      ) : null}

      {children}
    </svg>
  );
}

/** A responsive wrapper: measures, then renders the chart at that width. */
export function Responsive({
  height,
  children,
  className = "",
}: {
  height: number;
  children: (width: number) => React.ReactNode;
  className?: string;
}) {
  const [ref, width] = useChartWidth();
  return (
    <div ref={ref} className={`w-full ${className}`} style={{ minHeight: height }}>
      {children(width)}
    </div>
  );
}

/** Build an SVG path from points, skipping nulls so gaps stay gaps. */
export function linePath(
  points: Array<{ x: number; y: number | null }>,
): string {
  let path = "";
  let pen = false;
  for (const point of points) {
    if (point.y === null || !Number.isFinite(point.y)) {
      pen = false;
      continue;
    }
    path += `${pen ? "L" : "M"}${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
    pen = true;
  }
  return path;
}

/** A shaded band between two series, for prediction and confidence intervals. */
export function bandPath(
  points: Array<{ x: number; lower: number | null; upper: number | null }>,
): string {
  const valid = points.filter(
    (point) => point.lower !== null && point.upper !== null,
  ) as Array<{ x: number; lower: number; upper: number }>;
  if (valid.length === 0) return "";

  const top = valid.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)} ${p.upper.toFixed(2)}`);
  const bottom = [...valid]
    .reverse()
    .map((p) => `L${p.x.toFixed(2)} ${p.lower.toFixed(2)}`);
  return `${top.join("")}${bottom.join("")}Z`;
}

export function Legend({
  items,
}: {
  items: Array<{ label: string; color?: string; swatch?: React.ReactNode }>;
}) {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5 text-xs text-sub">
          {item.swatch ?? (
            <span
              className="size-2.5 shrink-0 rounded-sm"
              style={{ background: item.color ?? "var(--color-accent)" }}
            />
          )}
          {item.label}
        </li>
      ))}
    </ul>
  );
}

/**
 * A heatmap cell colour on a single-hue ramp. `t` runs 0..1; anything outside
 * is clamped. Used by the cohort triangle and any matrix view.
 */
export function rampColor(t: number, hue: "accent" | "good" | "bad" = "accent"): string {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(t) ? t : 0));
  const base =
    hue === "good" ? [21, 128, 61] : hue === "bad" ? [220, 38, 38] : [37, 99, 235];
  // Interpolate towards the panel colour rather than white, so cells sit on the
  // paper background without glowing.
  const paper = [248, 245, 235];
  const mix = base.map((channel, i) => Math.round(paper[i] + (channel - paper[i]) * clamped));
  return `rgb(${mix[0]} ${mix[1]} ${mix[2]})`;
}

/** Readable text colour for a cell filled with rampColor at intensity `t`. */
export function rampText(t: number): string {
  return t > 0.55 ? "#ffffff" : "var(--color-ink)";
}

/** A simple horizontal bar row, used for ranked lists everywhere. */
export function BarRow({
  label,
  value,
  max,
  display,
  color = "var(--color-accent)",
  labelWidth = "w-40",
}: {
  label: string;
  value: number;
  max: number;
  display?: string;
  color?: string;
  labelWidth?: string;
}) {
  const width = max === 0 ? 0 : Math.abs(value / max) * 100;
  return (
    <li className="flex items-center gap-2">
      <span className={`${labelWidth} shrink-0 truncate text-sm text-ink/90`} title={label}>
        {label}
      </span>
      <span className="h-2 flex-1 overflow-hidden rounded-full bg-panel2">
        <span
          className="block h-full rounded-full"
          style={{ width: `${width}%`, background: color }}
        />
      </span>
      <span className="w-16 shrink-0 text-right font-mono text-xs text-sub">
        {display ?? compact(value)}
      </span>
    </li>
  );
}

/** Empty-state box, so every tool fails the same way. */
export function ChartEmpty({ message }: { message: string }) {
  return (
    <div className="flex min-h-[120px] items-center justify-center rounded-xl border border-dashed border-edge2 bg-panel p-6 text-center text-sm text-sub">
      {message}
    </div>
  );
}

/** Hook up to a plot area's coordinates for a shared crosshair/tooltip. */
export function useHoverIndex(count: number) {
  const [index, setIndex] = useState<number | null>(null);

  const handlers = useMemo(
    () => ({
      onMouseLeave: () => setIndex(null),
      pick: (fraction: number) => {
        if (count === 0) return;
        const next = Math.round(fraction * (count - 1));
        setIndex(Math.max(0, Math.min(count - 1, next)));
      },
    }),
    [count],
  );

  return { index, setIndex, ...handlers };
}

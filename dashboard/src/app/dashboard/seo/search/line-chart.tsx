"use client";

import { useState } from "react";

export interface ChartSeries {
  name: string;
  color: string;
  values: (number | null)[];
}

const W = 920;
const H = 260;
const PAD = { l: 48, r: 16, t: 12, b: 26 };

function niceTicks(max: number): { top: number; ticks: number[] } {
  const raw = max / 4;
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 2.5, 5, 10].map((s) => s * mag).find((s) => s >= raw) ?? mag * 10;
  const top = Math.ceil(max / step) * step || 1;
  const ticks: number[] = [];
  for (let v = 0; v <= top + 1e-9; v += step) ticks.push(v);
  return { top, ticks };
}

function dayLabel(day: string): string {
  return new Date(day + "T00:00:00Z").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function LineChart({
  labels,
  series,
  format,
  invert = false,
}: {
  labels: string[];
  series: ChartSeries[];
  format: (v: number) => string;
  invert?: boolean;
}) {
  const [hover, setHover] = useState<number | null>(null);

  const n = labels.length;
  const max = Math.max(1e-9, ...series.flatMap((s) => s.values.filter((v): v is number => v !== null)));
  const { top, ticks } = niceTicks(max * 1.05);
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const x = (i: number) => PAD.l + (n > 1 ? (i / (n - 1)) * iw : iw / 2);
  const y = (v: number) => {
    const f = v / top;
    return invert ? PAD.t + f * ih : PAD.t + (1 - f) * ih;
  };

  const paths = series.map((s) => {
    let d = "";
    let pen = false;
    s.values.forEach((v, i) => {
      if (v === null) {
        pen = false;
        return;
      }
      d += `${pen ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`;
      pen = true;
    });
    return d;
  });

  const lastIdx = (s: ChartSeries) => {
    for (let i = s.values.length - 1; i >= 0; i--) if (s.values[i] !== null) return i;
    return -1;
  };

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    if (px < PAD.l - 6 || px > W - PAD.r + 6) return setHover(null);
    setHover(Math.max(0, Math.min(n - 1, Math.round(((px - PAD.l) / iw) * (n - 1)))));
  };

  const tickEvery = Math.max(1, Math.round(n / 6));
  const flipTooltip = hover !== null && x(hover) > W * 0.62;

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label="Daily metric chart"
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
      >
        {ticks.map((tv) => (
          <g key={tv}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(tv)} y2={y(tv)} className="stroke-edge" strokeWidth={1} />
            <text x={PAD.l - 8} y={y(tv) + 4} textAnchor="end" className="fill-faint text-[11px]">
              {format(tv)}
            </text>
          </g>
        ))}
        <line x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} className="stroke-edge2" strokeWidth={1} />
        {labels.map((day, i) =>
          i % tickEvery === 0 ? (
            <text key={day} x={x(i)} y={H - 8} textAnchor="middle" className="fill-faint text-[11px]">
              {dayLabel(day)}
            </text>
          ) : null,
        )}
        {series.length === 1 && paths[0] && (
          <path
            d={`${paths[0]}L${x(lastIdx(series[0])).toFixed(1)} ${invert ? PAD.t : H - PAD.b}L${x(0).toFixed(1)} ${invert ? PAD.t : H - PAD.b}Z`}
            fill={series[0].color}
            opacity={0.1}
          />
        )}
        {series.map((s, k) => (
          <path
            key={s.name}
            d={paths[k]}
            fill="none"
            stroke={s.color}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}
        {series.map((s) => {
          const li = lastIdx(s);
          if (li < 0) return null;
          const v = s.values[li] as number;
          return (
            <g key={s.name}>
              <circle cx={x(li)} cy={y(v)} r={5.5} className="fill-panel" />
              <circle cx={x(li)} cy={y(v)} r={4} fill={s.color} />
            </g>
          );
        })}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={H - PAD.b} className="stroke-edge2" strokeWidth={1} />
            {series.map((s) => {
              const v = s.values[hover];
              if (v === null) return null;
              return (
                <circle key={s.name} cx={x(hover)} cy={y(v)} r={5} fill={s.color} className="stroke-panel" strokeWidth={2} />
              );
            })}
          </g>
        )}
      </svg>
      {hover !== null && (
        <div
          className="pointer-events-none absolute top-6 z-10 min-w-[150px] max-w-[300px] rounded-lg border border-edge bg-panel p-2.5 shadow-lg"
          style={{
            left: `${((x(hover) / W) * 100).toFixed(2)}%`,
            transform: flipTooltip ? "translateX(calc(-100% - 14px))" : "translateX(14px)",
          }}
        >
          <p className="mb-1 text-[11px] text-faint">{dayLabel(labels[hover])}</p>
          {series.map((s) => (
            <div key={s.name} className="mt-0.5 flex items-center gap-2 text-xs">
              <span className="h-0 w-3.5 shrink-0 rounded border-t-[3px]" style={{ borderColor: s.color }} />
              <span className="font-semibold tabular-nums text-ink">
                {s.values[hover] === null ? "—" : format(s.values[hover] as number)}
              </span>
              <span className="truncate text-sub">{s.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

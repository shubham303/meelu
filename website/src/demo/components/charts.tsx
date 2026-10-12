"use client";

const ACCENT = "var(--color-accent)";
const GOOD = "var(--color-good)";
const BAD = "var(--color-bad)";
const EDGE = "var(--color-edge2)";

export function Sparkline({
  data,
  width = 96,
  height = 28,
  stroke,
}: {
  data: number[];
  width?: number;
  height?: number;
  stroke?: string;
}) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 2;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (width - pad * 2);
    const y = height - pad - ((v - min) / range) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const rising = data[data.length - 1] >= data[0];
  const color = stroke ?? (rising ? GOOD : BAD);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export function Bars({
  data,
  labels,
  height = 120,
  color = ACCENT,
}: {
  data: number[];
  labels?: string[];
  height?: number;
  color?: string;
}) {
  if (!data?.length) return null;
  const max = Math.max(...data) || 1;
  return (
    <div className="flex items-end gap-2" style={{ height }}>
      {data.map((v, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1 min-w-0">
          <div
            className="w-full rounded-t-sm"
            style={{ height: `${Math.max(4, (v / max) * (height - 20))}px`, background: color, opacity: 0.5 + 0.5 * (v / max) }}
          />
          {labels?.[i] && <span className="text-[10px] text-faint truncate">{labels[i]}</span>}
        </div>
      ))}
    </div>
  );
}

export function Donut({
  value,
  max = 100,
  size = 64,
  label,
}: {
  value: number;
  max?: number;
  size?: number;
  label?: string;
}) {
  const r = size / 2 - 5;
  const c = 2 * Math.PI * r;
  const frac = Math.min(1, Math.max(0, value / (max || 1)));
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={EDGE} strokeWidth="5" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={ACCENT}
          strokeWidth="5"
          strokeDasharray={`${c * frac} ${c}`}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-xs font-medium text-ink">{label ?? `${Math.round(frac * 100)}%`}</span>
    </div>
  );
}

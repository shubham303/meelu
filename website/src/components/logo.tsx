import { cn } from "@/lib/utils";

/**
 * The Meelu mark: a solid disk overlapping an open ring. Below ~32px the ring
 * is drawn thicker so it survives at favicon-ish sizes — that is the
 * `meelu-mark-small` variant from the brand kit. Each viewBox is cropped to the
 * artwork so `size` is the mark's true rendered height, with no dead padding.
 */
const marks = {
  regular: {
    viewBox: "5 11 38 26",
    ratio: 38 / 26,
    disk: { cx: 30, r: 13 },
    ring: { cx: 18, r: 11, width: 4 },
  },
  small: {
    viewBox: "3.25 9.5 41.25 29",
    ratio: 41.25 / 29,
    disk: { cx: 30, r: 14.5 },
    ring: { cx: 17, r: 11, width: 5.5 },
  },
} as const;

const tones = {
  light: { disk: "var(--color-accent)", ring: "var(--color-ink)", text: "text-ink" },
  dark: { disk: "#6b9bff", ring: "var(--color-bg)", text: "text-bg" },
} as const;

export function LogoMark({
  size = 22,
  tone = "light",
  className,
}: {
  size?: number;
  tone?: keyof typeof tones;
  className?: string;
}) {
  const mark = size < 32 ? marks.small : marks.regular;
  const { disk, ring } = tones[tone];

  return (
    <svg
      width={Math.round(size * mark.ratio)}
      height={size}
      viewBox={mark.viewBox}
      fill="none"
      className={className}
      aria-hidden
    >
      <circle cx={mark.disk.cx} cy="24" r={mark.disk.r} fill={disk} />
      <circle
        cx={mark.ring.cx}
        cy="24"
        r={mark.ring.r}
        fill="none"
        stroke={ring}
        strokeWidth={mark.ring.width}
      />
    </svg>
  );
}

export function Logo({
  size = 22,
  withWordmark = true,
  tone = "light",
  className,
}: {
  size?: number;
  withWordmark?: boolean;
  tone?: keyof typeof tones;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <LogoMark size={size} tone={tone} />
      {withWordmark && (
        <span
          className={cn(
            "font-[family-name:var(--font-fraunces)] text-lg font-light tracking-tight",
            tones[tone].text,
          )}
        >
          meelu
        </span>
      )}
    </span>
  );
}

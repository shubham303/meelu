export interface ScreenshotMarker {
  x: number;
  y: number;
  label: string;
}

export function Screenshot({
  src,
  alt,
  width,
  height,
  caption,
  markers = [],
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  caption?: string;
  markers?: ScreenshotMarker[];
}) {
  return (
    <figure className="not-prose my-6">
      <div className="relative overflow-hidden rounded-xl border border-fd-border bg-fd-card shadow-sm">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={alt} width={width} height={height} loading="lazy" className="block h-auto w-full" />
        {markers.map((marker, index) => (
          <span
            key={marker.label}
            aria-hidden
            className="absolute flex size-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-fd-primary text-xs font-semibold text-fd-primary-foreground shadow ring-2 ring-white"
            style={{ left: `${marker.x}%`, top: `${marker.y}%` }}
          >
            {index + 1}
          </span>
        ))}
      </div>
      {markers.length > 0 && (
        <ol className="mt-3 grid gap-x-6 gap-y-1.5 text-sm text-fd-muted-foreground sm:grid-cols-2">
          {markers.map((marker, index) => (
            <li key={marker.label} className="flex gap-2">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-fd-primary text-[11px] font-semibold text-fd-primary-foreground">
                {index + 1}
              </span>
              <span>{marker.label}</span>
            </li>
          ))}
        </ol>
      )}
      {caption && <figcaption className="mt-2 text-center text-sm text-fd-muted-foreground">{caption}</figcaption>}
    </figure>
  );
}

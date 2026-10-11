"use client";

import { useRef, useState } from "react";

export function ChartFrame({ html, title = "Chart" }: { html: string; title?: string }) {
  const ref = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(320);

  const measure = () => {
    const doc = ref.current?.contentDocument;
    const h = doc?.documentElement?.scrollHeight ?? 0;
    if (h > 0) setHeight(h);
  };

  return (
    <iframe
      ref={ref}
      title={title}
      sandbox="allow-same-origin"
      srcDoc={html}
      style={{ height }}
      className="block w-full bg-white"
      onLoad={() => {
        measure();
        setTimeout(measure, 150);
      }}
    />
  );
}

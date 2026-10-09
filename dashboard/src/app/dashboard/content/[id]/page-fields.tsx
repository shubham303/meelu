"use client";

import { useLayoutEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { PieceForm } from "./use-autosave";

const TITLE_MAX = 60;
const META_MIN = 70;
const META_MAX = 160;

function Counter({ length, min = 1, max }: { length: number; min?: number; max: number }) {
  const off = length > max || length < min;
  return (
    <span className={cn("shrink-0 pt-1 text-[11px] tabular-nums", off ? "text-warn" : "text-faint")}>
      {length}/{max}
    </span>
  );
}

function AutoTextarea({
  value,
  onChange,
  placeholder,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  className: string;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  return (
    <textarea
      ref={ref}
      value={value}
      rows={1}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={cn(
        "w-full resize-none overflow-hidden bg-transparent placeholder:text-faint focus:outline-none",
        className,
      )}
    />
  );
}

export function PageFields({
  form,
  onChange,
  meta,
}: {
  form: PieceForm;
  onChange: (patch: Partial<PieceForm>) => void;
  meta: React.ReactNode;
}) {
  return (
    <div className="mb-9">
      <div className="flex items-start gap-3">
        <AutoTextarea
          value={form.title}
          onChange={(title) => onChange({ title })}
          placeholder="Title"
          className="text-sm font-medium text-sub"
        />
        <Counter length={form.title.length} max={TITLE_MAX} />
      </div>

      <AutoTextarea
        value={form.h1}
        onChange={(h1) => onChange({ h1 })}
        placeholder="Headline (H1)"
        className="mt-2 font-display text-[40px] leading-[1.15] text-ink"
      />

      <div className="mt-3 flex items-start gap-3">
        <AutoTextarea
          value={form.metaDescription}
          onChange={(metaDescription) => onChange({ metaDescription })}
          placeholder="Meta description"
          className="text-[15px] italic leading-relaxed text-sub"
        />
        <Counter length={form.metaDescription.length} min={META_MIN} max={META_MAX} />
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-[13px] text-faint">{meta}</div>
    </div>
  );
}

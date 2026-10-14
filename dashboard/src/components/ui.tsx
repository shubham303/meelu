"use client";

import {
  useEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { createPortal } from "react-dom";
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Maximize2,
  Minimize2,
  X,
  Loader2,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { cn } from "@/lib/utils";
import { Sparkline } from "./charts";

type ButtonVariant = "primary" | "outline" | "ghost" | "danger";

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md";
}) {
  const base =
    "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-lg font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none cursor-pointer";
  const sizes = { sm: "text-xs px-2.5 py-1.5", md: "text-sm px-3.5 py-2" };
  const variants: Record<ButtonVariant, string> = {
    primary: "bg-accent text-white hover:bg-accent-hi",
    outline: "border border-edge2 text-ink hover:bg-panel2",
    ghost: "text-sub hover:text-ink hover:bg-panel2",
    danger: "bg-bad/10 text-bad border border-bad/30 hover:bg-bad/20",
  };
  return (
    <button className={cn(base, sizes[size], variants[variant], className)} {...rest}>
      {children}
    </button>
  );
}

export function IconButton({
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg p-1.5 text-sub hover:text-ink hover:bg-panel2 transition-colors cursor-pointer",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Card({
  className,
  children,
  onClick,
}: {
  className?: string;
  children: ReactNode;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "bg-panel border border-edge rounded-2xl p-5",
        onClick && "cursor-pointer hover:border-edge2 transition-colors",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
      <div>
        <h1 className="font-display text-2xl text-ink">{title}</h1>
        {description && <p className="text-sm text-sub mt-1 max-w-2xl">{description}</p>}
      </div>
      {actions && <div className="flex items-start gap-2">{actions}</div>}
    </div>
  );
}

export function StatCard({
  label,
  value,
  change,
  spark,
  hint,
}: {
  label: string;
  value: string | number;
  change?: number;
  spark?: number[];
  hint?: string;
}) {
  return (
    <Card className="stagger-item">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-sub uppercase tracking-wide">{label}</p>
          <p className="font-display text-2xl text-ink mt-1.5">{value}</p>
          {change !== undefined && (
            <p className={cn("text-xs mt-1", change >= 0 ? "text-good" : "text-bad")}>
              {change >= 0 ? "▲" : "▼"} {Math.abs(change)}%
            </p>
          )}
          {hint && <p className="text-xs text-faint mt-1">{hint}</p>}
        </div>
        {spark && spark.length > 1 && <Sparkline data={spark} />}
      </div>
    </Card>
  );
}

export type BadgeTone = "neutral" | "accent" | "good" | "warn" | "bad";

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}) {
  const tones: Record<BadgeTone, string> = {
    neutral: "bg-panel2 text-sub border-edge2",
    accent: "bg-accent-soft text-accent border-accent/30",
    good: "bg-good/10 text-good border-good/30",
    warn: "bg-warn/10 text-warn border-warn/30",
    bad: "bg-bad/10 text-bad border-bad/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const inputBase =
  "rounded-lg bg-panel2 border border-edge2 px-3 py-2 text-sm text-ink placeholder:text-faint focus:outline-none focus:border-accent transition-colors";

function fullWidthUnlessGiven(className?: string) {
  return /(^|\s)w-/.test(className ?? "") ? "" : "w-full";
}

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(inputBase, fullWidthUnlessGiven(className), className)} {...rest} />;
}

export function Textarea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(inputBase, fullWidthUnlessGiven(className), "min-h-24", className)}
      {...rest}
    />
  );
}

export function Select({
  className,
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(inputBase, fullWidthUnlessGiven(className), "cursor-pointer", className)}
      {...rest}
    >
      {children}
    </select>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-sub mb-1.5">{label}</span>
      {children}
      {hint && <span className="block text-xs text-faint mt-1">{hint}</span>}
    </label>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  wide,
  elevated,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
  elevated?: boolean;
}) {
  const [mounted, setMounted] = useState(false);
  const [shown, setShown] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  useEffect(() => setMounted(true), []);
  useEffect(() => {
    if (open) setShown(true);
  }, [open]);

  useGSAP(
    () => {
      if (!shown || !panelRef.current) return;
      if (open) {
        gsap.fromTo(
          panelRef.current,
          { xPercent: 100 },
          { xPercent: 0, duration: 0.4, ease: "power3.out" },
        );
        gsap.fromTo(backdropRef.current, { opacity: 0 }, { opacity: 1, duration: 0.25 });
      } else {
        gsap.to(panelRef.current, { xPercent: 100, duration: 0.3, ease: "power3.in" });
        gsap.to(backdropRef.current, {
          opacity: 0,
          duration: 0.25,
          onComplete: () => setShown(false),
        });
      }
    },
    { dependencies: [open, shown] },
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!mounted || !shown) return null;
  return createPortal(
    <div className={cn("fixed inset-0", elevated ? "z-[70]" : "z-50")}>
      <div
        ref={backdropRef}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        className={cn(
          "absolute right-0 top-0 h-full w-full bg-panel border-l border-edge2 flex flex-col will-change-transform",
          wide ? "max-w-2xl" : "max-w-lg",
        )}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-edge">
          <h2 className="font-display text-lg text-ink">{title}</h2>
          <IconButton onClick={onClose} aria-label="Close">
            <X size={16} />
          </IconButton>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

const DRAWER_MIN = 380;

export function Drawer({
  open,
  onClose,
  title,
  children,
  actions,
  fullscreenToggle,
}: {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
  fullscreenToggle?: boolean;
}) {
  const [mounted, setMounted] = useState(false);
  const [shown, setShown] = useState(false);
  const [width, setWidth] = useState(560);
  const [maximized, setMaximized] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ startX: number; startWidth: number; overshoot: number } | null>(null);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (open) {
      const max = Math.floor(window.innerWidth * 0.85);
      const min = Math.min(DRAWER_MIN, max);
      setWidth(Math.min(Math.max(Math.floor(window.innerWidth * 0.5), min), 720));
      setShown(true);
    }
  }, [open]);

  useGSAP(
    () => {
      if (!shown || !panelRef.current) return;
      if (open) {
        gsap.fromTo(
          panelRef.current,
          { xPercent: 100, x: 0 },
          { xPercent: 0, duration: 0.45, ease: "power3.out" },
        );
        gsap.fromTo(backdropRef.current, { opacity: 0 }, { opacity: 1, duration: 0.3 });
      } else {
        gsap.to(panelRef.current, { xPercent: 100, duration: 0.35, ease: "power3.in" });
        gsap.to(backdropRef.current, {
          opacity: 0,
          duration: 0.3,
          onComplete: () => setShown(false),
        });
      }
    },
    { dependencies: [open, shown] },
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  function onHandleDown(e: React.PointerEvent<HTMLDivElement>) {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { startX: e.clientX, startWidth: width, overshoot: 0 };
  }

  function onHandleMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    const max = Math.floor(window.innerWidth * 0.85);
    const min = Math.min(DRAWER_MIN, max);
    const desired = drag.current.startWidth + (drag.current.startX - e.clientX);
    setWidth(Math.min(Math.max(desired, min), max));
    const overshoot = Math.max(0, min - desired);
    drag.current.overshoot = overshoot;
    if (panelRef.current) gsap.set(panelRef.current, { x: overshoot });
  }

  function onHandleUp() {
    if (!drag.current) return;
    const { overshoot } = drag.current;
    drag.current = null;
    if (overshoot > 90) onClose();
    else if (panelRef.current) {
      gsap.to(panelRef.current, { x: 0, duration: 0.25, ease: "power3.out" });
    }
  }

  if (!mounted || !shown) return null;
  return createPortal(
    <div className="fixed inset-0 z-50">
      <div
        ref={backdropRef}
        className="absolute inset-0 bg-black/50 backdrop-blur-[2px]"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        style={maximized ? { width: "100vw" } : { width }}
        className="absolute right-0 top-0 h-full bg-panel border-l border-edge2 flex flex-col will-change-transform select-none"
      >
        {!maximized && (
          <div
            onPointerDown={onHandleDown}
            onPointerMove={onHandleMove}
            onPointerUp={onHandleUp}
            className="absolute left-0 top-0 z-10 h-full w-4 -translate-x-1/2 cursor-col-resize group flex items-center justify-center touch-none"
            aria-hidden
          >
            <div className="h-16 w-1 rounded-full bg-edge2 group-hover:bg-accent transition-colors" />
          </div>
        )}
        <div className="flex items-start justify-between gap-3 px-6 py-5 border-b border-edge">
          <div className="min-w-0">{title}</div>
          <div className="flex items-center gap-1 shrink-0">
            {actions}
            {fullscreenToggle && (
              <IconButton
                onClick={() => setMaximized((v) => !v)}
                aria-label={maximized ? "Restore" : "Maximize"}
                title={maximized ? "Restore" : "Maximize"}
              >
                {maximized ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
              </IconButton>
            )}
            <IconButton onClick={onClose} aria-label="Close">
              <X size={16} />
            </IconButton>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5 select-text">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

export function ConfirmDelete({
  open,
  onClose,
  onConfirm,
  what,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  what: string;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <Modal open={open} onClose={onClose} title={`Delete ${what}?`}>
      <p className="text-sm text-sub mb-5">This can&apos;t be undone.</p>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="danger"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onConfirm();
              onClose();
            } finally {
              setBusy(false);
            }
          }}
        >
          <Trash2 size={14} /> Delete
        </Button>
      </div>
    </Modal>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ key: string; label: string; count?: number }>;
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="flex items-center gap-1 border-b border-edge mb-5">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={cn(
            "px-3 py-2 text-sm -mb-px border-b-2 transition-colors cursor-pointer",
            active === t.key
              ? "border-accent text-ink"
              : "border-transparent text-sub hover:text-ink",
          )}
        >
          {t.label}
          {t.count !== undefined && (
            <span className="ml-1.5 text-xs text-faint">{t.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}

export function Table({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("bg-panel border border-edge rounded-2xl overflow-x-auto", className)}>
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

export type SortState = { col: string; dir: "asc" | "desc" };

export function THead({
  cols,
  sortable,
  sort,
  onSort,
}: {
  cols: string[];
  sortable?: string[];
  sort?: SortState | null;
  onSort?: (col: string) => void;
}) {
  return (
    <thead>
      <tr className="border-b border-edge">
        {cols.map((c, i) => {
          const active = sort?.col === c ? sort : null;
          return (
            <th
              key={i}
              aria-sort={active ? (active.dir === "asc" ? "ascending" : "descending") : undefined}
              className="text-left text-xs font-medium text-sub uppercase tracking-wide px-4 py-3"
            >
              {onSort && sortable?.includes(c) ? (
                <button
                  onClick={() => onSort(c)}
                  className={cn(
                    "group inline-flex cursor-pointer items-center gap-1 transition-colors hover:text-ink",
                    active && "text-ink",
                  )}
                >
                  {c}
                  {active ? (
                    active.dir === "asc" ? (
                      <ChevronUp size={13} />
                    ) : (
                      <ChevronDown size={13} />
                    )
                  ) : (
                    <ChevronsUpDown
                      size={13}
                      className="text-faint opacity-0 transition-opacity group-hover:opacity-100"
                    />
                  )}
                </button>
              ) : (
                c
              )}
            </th>
          );
        })}
      </tr>
    </thead>
  );
}

export function TRow({
  children,
  onClick,
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "border-b border-edge last:border-0",
        onClick && "cursor-pointer hover:bg-panel2 transition-colors",
        className,
      )}
    >
      {children}
    </tr>
  );
}

export function TCell({
  children,
  className,
  colSpan,
}: {
  children?: ReactNode;
  className?: string;
  colSpan?: number;
}) {
  return (
    <td colSpan={colSpan} className={cn("px-4 py-3 text-ink align-top", className)}>
      {children}
    </td>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex justify-center py-16", className)}>
      <Loader2 className="animate-spin text-accent" size={22} />
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  hint,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <Card className="flex flex-col items-center text-center py-14">
      {Icon && (
        <div className="rounded-2xl bg-accent-soft p-3 mb-4">
          <Icon className="text-accent" size={22} />
        </div>
      )}
      <p className="font-display text-lg text-ink">{title}</p>
      {hint && <p className="text-sm text-sub mt-1.5 max-w-sm">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </Card>
  );
}

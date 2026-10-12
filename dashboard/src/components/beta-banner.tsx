import { FlaskConical } from "lucide-react";

export function BetaBanner() {
  return (
    <div role="note" className="border-b border-warn/30 bg-warn/10 px-8 py-1.5 text-xs text-sub">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-2">
        <FlaskConical size={13} className="shrink-0 text-warn" />
        <p className="min-w-0">
          <span className="font-medium text-ink">Beta</span> · Meelu is updated often and you may run into bugs. The app is
          not yet verified by Apple, Microsoft or Google, so security warnings when you install or update it are expected.
        </p>
      </div>
    </div>
  );
}

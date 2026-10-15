import Link from "next/link";
import { ArrowRight, type LucideIcon } from "lucide-react";
import { Card } from "@demo/components/ui";

export function SectionCard({
  href,
  icon: Icon,
  title,
  blurb,
  children,
}: {
  href: string;
  icon: LucideIcon;
  title: string;
  blurb: string;
  children?: React.ReactNode;
}) {
  return (
    <Link href={href} className="group block stagger-item">
      <Card className="flex items-center justify-between gap-3 transition-colors hover:border-edge2">
        <div className="flex min-w-0 items-center gap-2.5">
          <Icon size={16} className="shrink-0 text-accent" />
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink">{title}</p>
            <p className="mt-0.5 truncate text-xs text-sub">{blurb}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {children}
          <ArrowRight size={14} className="text-faint transition-colors group-hover:text-accent" />
        </div>
      </Card>
    </Link>
  );
}

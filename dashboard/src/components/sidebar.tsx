"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Cable,
  Globe,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useIsApp } from "@/lib/use-app-mode";
import { GLOBAL } from "@/lib/current-site";
import { useCurrentSite } from "@/lib/use-api";
import { signOut, useSession } from "@/lib/session";
import { Logo } from "./logo";
import { SessionUsage } from "./session-usage";
import { SiteSwitcher } from "./site-switcher";
import { APP_DESKS, GLOBAL_HOME, WEBSITE_DESKS, type Desk } from "./desks";

const COLLAPSED_KEY = "meelu.sidebar.collapsed";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = useSession();
  const selection = useCurrentSite();
  const global = selection === GLOBAL;
  const isApp = useIsApp();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCollapsed(readCollapsed());
  }, []);

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    try {
      localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0");
    } catch {}
  };

  const website = global ? [] : WEBSITE_DESKS;
  const appGroup = APP_DESKS;

  useEffect(() => {
    if (!global) return;
    const onDesk = WEBSITE_DESKS.some((d) =>
      d.exact ? pathname === d.href : pathname.startsWith(d.href),
    );
    if (onDesk) router.replace(GLOBAL_HOME);
  }, [global, pathname, router]);

  const isActive = (item: Desk) =>
    item.exact ? pathname === item.href : pathname.startsWith(item.href);

  const linkClass = (active: boolean) =>
    cn(
      "flex items-center gap-2.5 rounded-lg py-2 text-sm transition-colors",
      collapsed ? "justify-center px-0" : "px-3",
      active ? "bg-accent-soft text-accent" : "text-sub hover:text-ink hover:bg-panel2",
    );

  const navLink = (item: Desk) => {
    const Icon: LucideIcon = item.icon;
    return (
      <Link key={item.href} href={item.href} title={collapsed ? item.label : undefined} className={linkClass(isActive(item))}>
        <Icon size={16} className="shrink-0" />
        {!collapsed && item.label}
      </Link>
    );
  };

  return (
    <aside
      className={cn(
        "shrink-0 border-r border-edge bg-panel/50 flex flex-col min-h-screen sticky top-0 max-h-screen transition-[width] duration-200",
        collapsed ? "w-14" : "w-60",
      )}
    >
      <div className={cn("border-b border-edge", collapsed ? "flex flex-col items-center gap-2 px-2 py-3" : "px-5 py-5")}>
        {collapsed ? (
          <Link href="/dashboard" title="Meelu" className="flex h-8 w-8 items-center justify-center">
            <Logo withWordmark={false} />
          </Link>
        ) : (
          <div className="flex items-start justify-between">
            <div>
              <Link href="/dashboard">
                <Logo />
              </Link>
              <p className="text-[11px] text-faint mt-1">Your AI coworker</p>
            </div>
            <button
              type="button"
              onClick={toggleCollapsed}
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
              className="rounded-lg p-1.5 text-faint hover:text-ink hover:bg-panel2 transition-colors cursor-pointer"
            >
              <PanelLeftClose size={16} />
            </button>
          </div>
        )}
        {collapsed && (
          <button
            type="button"
            onClick={toggleCollapsed}
            title="Expand sidebar"
            aria-label="Expand sidebar"
            className="rounded-lg p-1.5 text-faint hover:text-ink hover:bg-panel2 transition-colors cursor-pointer"
          >
            <PanelLeftOpen size={16} />
          </button>
        )}
      </div>

      {collapsed ? (
        <div className="flex justify-center border-b border-edge py-2">
          <button
            type="button"
            onClick={toggleCollapsed}
            title={global ? "Global" : "Switch website"}
            aria-label="Switch website"
            className="rounded-lg p-2 text-sub hover:text-ink hover:bg-panel2 transition-colors cursor-pointer"
          >
            <Globe size={16} className={cn(!global && "text-accent")} />
          </button>
        </div>
      ) : (
        <div className="pt-3 border-b border-edge">
          <SiteSwitcher />
        </div>
      )}

      <nav className={cn("flex-1 overflow-y-auto space-y-0.5", collapsed ? "p-2" : "p-3")}>
        {website.length > 0 && (
          <>
            {!collapsed && <GroupLabel>Website</GroupLabel>}
            {website.map(navLink)}
          </>
        )}

        <div className={cn(website.length > 0 && (collapsed ? "mt-3 border-t border-edge pt-3" : "pt-4"))}>
          {!collapsed && <GroupLabel>App</GroupLabel>}
          {appGroup.map(navLink)}
        </div>
      </nav>

      <div className={cn("border-t border-edge space-y-0.5", collapsed ? "p-2" : "p-3")}>
        {isApp && (
          <Link
            href="/dashboard/connections"
            title={collapsed ? "Connections" : undefined}
            className={linkClass(pathname.startsWith("/dashboard/connections"))}
          >
            <Cable size={16} className="shrink-0" />
            {!collapsed && "Connections"}
          </Link>
        )}
        <button
          onClick={async () => {
            await signOut();
            router.push("/login");
          }}
          title={collapsed ? "Sign out" : undefined}
          className={cn("w-full cursor-pointer", linkClass(false))}
        >
          <LogOut size={16} className="shrink-0" />
          {!collapsed && "Sign out"}
        </button>
        <SessionUsage compact={collapsed} />
        {session?.user && !collapsed && (
          <p className="px-3 pt-2 text-[11px] text-faint truncate">{session.user.email}</p>
        )}
      </div>
    </aside>
  );
}

function GroupLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-3 pb-1.5 text-[10px] font-medium uppercase tracking-wider text-faint">
      {children}
    </p>
  );
}

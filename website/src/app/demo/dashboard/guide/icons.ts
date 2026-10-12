import {
  BookOpen,
  CalendarDays,
  Lightbulb,
  ListChecks,
  Search,
  Send,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { AgentGuideIcon } from "@demo/lib/agents";

export const GUIDE_ICONS: Record<AgentGuideIcon, LucideIcon> = {
  send: Send,
  calendar: CalendarDays,
  users: Users,
  search: Search,
  checklist: ListChecks,
  lightbulb: Lightbulb,
  book: BookOpen,
};

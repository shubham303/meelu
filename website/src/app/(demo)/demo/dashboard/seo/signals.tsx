import { Badge, type BadgeTone } from "@demo/components/ui";
import type { ClusterImportance, SearchIntent } from "./types";

const IMPORTANCE_TONE: Record<ClusterImportance, BadgeTone> = {
  hot: "bad",
  warm: "warn",
  cold: "neutral",
};

export const IMPORTANCE_MEANING: Record<ClusterImportance, string> = {
  hot: "ready to act on what you offer",
  warm: "comparing options you could serve",
  cold: "learning about the topic",
};

export const INTENT_MEANING: Record<SearchIntent, string> = {
  informational: "wants to learn something",
  navigational: "wants one specific site or page",
  commercial: "is comparing before choosing",
  transactional: "wants to buy, sign up or book now",
};

export function ImportanceBadge({ importance }: { importance?: ClusterImportance }) {
  if (!importance) return <span className="text-xs text-faint">—</span>;
  return (
    <span title={IMPORTANCE_MEANING[importance]}>
      <Badge tone={IMPORTANCE_TONE[importance]}>{importance}</Badge>
    </span>
  );
}

export function IntentBadge({ intent }: { intent?: SearchIntent }) {
  if (!intent) return <span className="text-xs text-faint">—</span>;
  return (
    <span title={INTENT_MEANING[intent]}>
      <Badge>{intent}</Badge>
    </span>
  );
}

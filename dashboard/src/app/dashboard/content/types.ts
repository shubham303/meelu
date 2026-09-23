import type { BadgeTone } from "@/components/ui";
import type { PieceStatus } from "@/lib/types";

export type { ContentPiece, ContentPieceSlim, PieceStatus } from "@/lib/types";

export type IssueState = "open" | "fixed" | "dismissed";

export interface PieceIssue {
  id: string;
  pieceId: string;
  tool: string;
  code: string;
  title: string;
  detail?: string | null;
  anchorText: string | null;
  suggestion: string | null;
  state: IssueState;
  runId: string;
  createdAt: string;
  updatedAt: string;
}

export const STATUSES: Array<{ key: PieceStatus; label: string }> = [
  { key: "draft", label: "Draft" },
  { key: "blocked", label: "Blocked" },
];

export const STATUS_TONE: Record<PieceStatus, BadgeTone> = {
  draft: "neutral",
  blocked: "bad",
};

export const STATUS_LABEL: Record<PieceStatus, string> = {
  draft: "Draft",
  blocked: "Blocked",
};

export const CHANNEL_LABEL: Record<string, string> = {
  linkedin: "LinkedIn",
  instagram: "Instagram",
  twitter: "X",
  threads: "Threads",
  bluesky: "Bluesky",
  facebook: "Facebook",
  tiktok: "TikTok",
  pinterest: "Pinterest",
  telegram: "Telegram",
  google_business: "Google Business",
  website: "Website",
};

export const CHANNEL_COLOR: Record<string, string> = {
  linkedin: "#0a66c2",
  instagram: "#c13584",
  twitter: "#1f2d3d",
  threads: "#1f2d3d",
  bluesky: "#1185fe",
  facebook: "#1877f2",
  tiktok: "#111111",
  pinterest: "#bd081c",
  telegram: "#229ed9",
  google_business: "#4285f4",
  website: "#15803d",
};

export function channelLabel(key: string): string {
  return CHANNEL_LABEL[key] ?? key;
}

export const TOOL_LABELS: Record<string, string> = {
  readability: "Readability",
  similarity: "Similarity",
  seo: "SEO",
  ai_detector: "AI detector",
  channel_rules: "Channel rules",
};

export function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? tool.replace(/_/g, " ");
}

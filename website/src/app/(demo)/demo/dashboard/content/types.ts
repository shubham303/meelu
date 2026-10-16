export type { ContentPiece, ContentPieceSlim } from "@demo/lib/types";

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

export const TOOL_LABELS: Record<string, string> = {
  readability: "Readability",
  similarity: "Similarity",
  seo: "SEO",
  ai_detector: "AI detector",
  page_rules: "Page rules",
};

export function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? tool.replace(/_/g, " ");
}

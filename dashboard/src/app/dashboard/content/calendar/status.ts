import type { ContentPieceSlim } from "@/lib/types";

export function isOverdue(post: ContentPieceSlim, now: Date): boolean {
  if (!post.scheduledAt) return false;
  if (post.status !== "draft" && post.status !== "blocked") return false;
  return new Date(post.scheduledAt).getTime() < now.getTime();
}

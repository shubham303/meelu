"use client";

import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui";
import type { ContentPiece } from "../types";

export function Rail({ piece, onDelete }: { piece: ContentPiece; onDelete: () => void }) {
  return (
    <aside className="flex w-[300px] shrink-0 flex-col gap-7 overflow-y-auto border-l border-edge bg-panel p-6">
      <section className="flex flex-col gap-3.5">
        <p className="text-[10px] font-medium uppercase tracking-[.08em] text-faint">Piece</p>
        <div>
          <p className="text-xs font-medium text-sub mb-1.5">Where it goes</p>
          <p className="text-sm text-ink">Your website</p>
          <p className="mt-1 text-xs leading-relaxed text-faint">
            Meelu keeps the page and checks it. Copy the markdown out and publish it on your site
            yourself.
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-sub mb-1.5">Written by</p>
          <p className="text-sm text-ink">{piece.createdBy === "agent" ? "The agent" : "You"}</p>
        </div>
        {piece.checks.length > 0 && (
          <div>
            <p className="text-xs font-medium text-sub mb-1.5">Page warnings</p>
            <ul className="space-y-1 text-xs leading-relaxed text-warn">
              {piece.checks.map((c) => (
                <li key={c.code}>· {c.message}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <div className="mt-auto">
        <Button variant="ghost" size="sm" onClick={onDelete} className="text-bad hover:text-bad">
          <Trash2 size={13} /> Delete piece
        </Button>
      </div>
    </aside>
  );
}

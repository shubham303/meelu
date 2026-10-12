"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@demo/lib/use-api";
import type { ContentPiece } from "../types";

export type SaveState = "idle" | "dirty" | "saving" | "saved" | "error";

export interface PieceForm {
  title: string;
  bodyMarkdown: string;
}

export function formFrom(piece: ContentPiece): PieceForm {
  return {
    title: piece.title ?? "",
    bodyMarkdown: piece.bodyMarkdown ?? "",
  };
}

function payload(form: PieceForm) {
  return {
    title: form.title.trim() || "Untitled piece",
    bodyMarkdown: form.bodyMarkdown,
  };
}

export function useAutosave(
  pieceId: string,
  initial: PieceForm | null,
  onSaved?: (piece: ContentPiece) => void,
  delayMs = 800,
) {
  const [form, setFormState] = useState<PieceForm | null>(initial);
  const [state, setState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef<PieceForm | null>(initial);
  const inFlight = useRef<Promise<void> | null>(null);
  const onSavedRef = useRef(onSaved);
  useEffect(() => {
    onSavedRef.current = onSaved;
  }, [onSaved]);

  useEffect(() => {
    if (initial && !latest.current) {
      latest.current = initial;
      setFormState(initial);
    }
  }, [initial]);

  const save = useCallback(async (): Promise<boolean> => {
    const snapshot = latest.current;
    if (!snapshot) return true;
    if (inFlight.current) await inFlight.current;
    setState("saving");
    const job = (async () => {
      try {
        const saved = await api<ContentPiece>(`/api/v1/content/pieces/${pieceId}`, {
          method: "PATCH",
          body: payload(snapshot),
        });
        setSavedAt(new Date(saved.updatedAt));
        setError(null);
        setState(latest.current === snapshot ? "saved" : "dirty");
        onSavedRef.current?.(saved);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not save.");
        setState("error");
        throw e;
      }
    })();
    inFlight.current = job;
    try {
      await job;
      return true;
    } catch {
      return false;
    } finally {
      inFlight.current = null;
    }
  }, [pieceId]);

  const setForm = useCallback(
    (update: Partial<PieceForm> | ((f: PieceForm) => Partial<PieceForm>)) => {
      setFormState((prev) => {
        if (!prev) return prev;
        const patch = typeof update === "function" ? update(prev) : update;
        const next = { ...prev, ...patch };
        latest.current = next;
        return next;
      });
      setState("dirty");
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => void save(), delayMs);
    },
    [delayMs, save],
  );

  const flush = useCallback(async () => {
    const pending = timer.current !== null;
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (pending || state === "dirty" || state === "error") return save();
    if (inFlight.current) await inFlight.current;
    return true;
  }, [save, state]);

  useEffect(
    () => () => {
      if (timer.current) {
        clearTimeout(timer.current);
        void save();
      }
    },
    [save],
  );

  const current = useCallback(() => latest.current, []);

  return { form, setForm, state, error, savedAt, flush, current };
}

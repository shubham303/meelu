import { AI_LABEL, MODEL_DTYPE, MODEL_ID } from "@/lib/ai-detect/constants";
import type { LoadProgress } from "@/lib/ai-detect/types";

/**
 * Two ways to run the same model, both entirely in the browser.
 *
 * The worker is the one we want: inference on a 150M-parameter model freezes the main
 * thread for long enough to be noticed, and a frozen page looks broken. Module workers
 * are not everywhere yet (Firefox only got them in 114), so if the worker will not start
 * we run the model on the main thread instead. Slower and jerkier, but it works, and
 * nothing about where the text goes changes either way — it stays in the tab.
 */

type Progress = (progress: LoadProgress) => void;

export type Engine = {
  load: (onProgress: Progress) => Promise<void>;
  classify: (chunks: string[]) => Promise<number[]>;
  dispose: () => void;
  /** Set once we know which path we took, for the diagnostics line under the result. */
  mode: () => "worker" | "main-thread" | "unknown";
};

type WorkerOut =
  | { type: "progress"; loadedBytes: number; totalBytes: number; percent: number; message: string }
  | { type: "ready" }
  | { type: "scored"; id: number; scores: number[] }
  | { type: "failed"; message: string };

export function createEngine(): Engine {
  let worker: Worker | null = null;
  let mode: "worker" | "main-thread" | "unknown" = "unknown";
  let loaded = false;

  let onProgress: Progress = () => {};
  let resolveLoad: (() => void) | null = null;
  let rejectLoad: ((error: Error) => void) | null = null;

  let nextId = 1;
  const waiting = new Map<
    number,
    { resolve: (scores: number[]) => void; reject: (error: Error) => void }
  >();

  function failEverything(message: string) {
    const error = new Error(message);
    rejectLoad?.(error);
    rejectLoad = null;
    resolveLoad = null;
    for (const entry of waiting.values()) entry.reject(error);
    waiting.clear();
  }

  function startWorker(): Worker | null {
    try {
      const spawned = new Worker(new URL("./detector.worker.ts", import.meta.url), {
        type: "module",
      });
      spawned.addEventListener("message", (event: MessageEvent<WorkerOut>) => {
        const message = event.data;
        if (message.type === "progress") {
          onProgress({
            percent: message.percent,
            loadedBytes: message.loadedBytes,
            totalBytes: message.totalBytes,
            message: message.message,
          });
        } else if (message.type === "ready") {
          loaded = true;
          resolveLoad?.();
          resolveLoad = null;
          rejectLoad = null;
        } else if (message.type === "scored") {
          waiting.get(message.id)?.resolve(message.scores);
          waiting.delete(message.id);
        } else if (message.type === "failed") {
          failEverything(message.message);
        }
      });
      spawned.addEventListener("error", () => {
        failEverything("The detector worker stopped unexpectedly.");
      });
      return spawned;
    } catch {
      return null;
    }
  }

  // --- main-thread fallback -------------------------------------------------
  type Classifier = (
    text: string,
    options: { top_k: null },
  ) => Promise<Array<{ label: string; score: number }>>;
  let inline: Promise<Classifier> | null = null;

  function loadInline(): Promise<Classifier> {
    if (inline) return inline;
    const files = new Map<string, { loaded: number; total: number }>();
    const report = (message: string) => {
      let done = 0;
      let total = 0;
      for (const file of files.values()) {
        done += file.loaded;
        total += file.total;
      }
      onProgress({
        percent: total > 0 ? Math.min(100, (done / total) * 100) : 0,
        loadedBytes: done,
        totalBytes: total,
        message,
      });
    };

    inline = (async () => {
      const { pipeline } = await import("@huggingface/transformers");
      const pipe = await pipeline("text-classification", MODEL_ID, {
        dtype: MODEL_DTYPE,
        progress_callback: ((event: {
          status: string;
          file?: string;
          name?: string;
          loaded?: number;
          total?: number;
        }) => {
          const key = event.file ?? event.name ?? "model";
          if (event.status === "progress" && event.total) {
            files.set(key, { loaded: event.loaded ?? 0, total: event.total });
            report("Downloading the model");
          } else if (event.status === "done") {
            const known = files.get(key);
            if (known) files.set(key, { loaded: known.total, total: known.total });
            report("Downloading the model");
          } else if (event.status === "initiate") {
            report("Fetching model files");
          }
        }) as never,
      });
      return pipe as unknown as Classifier;
    })();
    inline.catch(() => {
      inline = null;
    });
    return inline;
  }

  return {
    mode: () => mode,

    load(progress) {
      onProgress = progress;
      if (loaded) return Promise.resolve();

      if (mode === "unknown") {
        worker = startWorker();
        mode = worker ? "worker" : "main-thread";
      }

      if (mode === "worker" && worker) {
        const active = worker;
        return new Promise<void>((resolve, reject) => {
          resolveLoad = resolve;
          rejectLoad = reject;
          active.postMessage({ type: "load" });
        });
      }

      return loadInline().then(() => {
        loaded = true;
      });
    },

    async classify(chunks) {
      if (mode === "worker" && worker) {
        const active = worker;
        const id = nextId++;
        return new Promise<number[]>((resolve, reject) => {
          waiting.set(id, { resolve, reject });
          active.postMessage({ type: "classify", id, chunks });
        });
      }

      const pipe = await loadInline();
      const scores: number[] = [];
      for (const chunk of chunks) {
        const output = await pipe(chunk, { top_k: null });
        scores.push(output.find((row) => row.label === AI_LABEL)?.score ?? 0);
        // Give the browser a frame back so the page keeps responding without a worker.
        await new Promise((r) => setTimeout(r, 0));
      }
      return scores;
    },

    dispose() {
      worker?.terminate();
      worker = null;
      loaded = false;
      waiting.clear();
    },
  };
}

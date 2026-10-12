/**
 * Runs the classifier off the main thread.
 *
 * Nothing here talks to a server. transformers.js pulls the model files from the
 * Hugging Face CDN and the ONNX runtime WebAssembly from jsDelivr on first use, stores
 * both in the browser's Cache API, and every run after that is offline. The text the
 * visitor pastes never leaves this worker.
 */
import { AI_LABEL, MODEL_DTYPE, MODEL_ID } from "@/lib/ai-detect/constants";

type Incoming = { type: "load" } | { type: "classify"; id: number; chunks: string[] };

type Outgoing =
  | {
      type: "progress";
      loadedBytes: number;
      totalBytes: number;
      percent: number;
      message: string;
    }
  | { type: "ready" }
  | { type: "scored"; id: number; scores: number[] }
  | { type: "failed"; message: string };

const ctx = self as unknown as {
  postMessage: (message: Outgoing) => void;
  addEventListener: (
    type: "message",
    handler: (event: MessageEvent<Incoming>) => void,
  ) => void;
};

type Classifier = (
  text: string,
  options: { top_k: null },
) => Promise<Array<{ label: string; score: number }>>;

let pending: Promise<Classifier> | null = null;

/** Per-file byte counters, so the bar reflects the whole download rather than one file. */
const files = new Map<string, { loaded: number; total: number }>();

type ProgressEvent = {
  status: string;
  file?: string;
  name?: string;
  loaded?: number;
  total?: number;
};

function report(message: string) {
  let loaded = 0;
  let total = 0;
  for (const entry of files.values()) {
    loaded += entry.loaded;
    total += entry.total;
  }
  ctx.postMessage({
    type: "progress",
    loadedBytes: loaded,
    totalBytes: total,
    percent: total > 0 ? Math.min(100, (loaded / total) * 100) : 0,
    message,
  });
}

function onProgress(event: ProgressEvent) {
  const key = event.file ?? event.name ?? "model";
  if (event.status === "progress" && typeof event.total === "number" && event.total > 0) {
    files.set(key, { loaded: event.loaded ?? 0, total: event.total });
    report("Downloading the model");
    return;
  }
  if (event.status === "done") {
    const known = files.get(key);
    if (known) files.set(key, { loaded: known.total, total: known.total });
    report("Downloading the model");
    return;
  }
  if (event.status === "initiate") {
    report("Fetching model files");
    return;
  }
  if (event.status === "ready") {
    report("Starting the model");
  }
}

async function classifier(): Promise<Classifier> {
  if (!pending) {
    pending = (async () => {
      report("Loading the detector");
      const { pipeline } = await import("@huggingface/transformers");
      const pipe = await pipeline("text-classification", MODEL_ID, {
        dtype: MODEL_DTYPE,
        progress_callback: onProgress as never,
      });
      report("Ready");
      return pipe as unknown as Classifier;
    })();
    pending.catch(() => {
      pending = null;
    });
  }
  return pending;
}

ctx.addEventListener("message", (event) => {
  const message = event.data;

  if (message.type === "load") {
    classifier().then(
      () => ctx.postMessage({ type: "ready" }),
      (error: unknown) =>
        ctx.postMessage({
          type: "failed",
          message: error instanceof Error ? error.message : "The model failed to load.",
        }),
    );
    return;
  }

  if (message.type === "classify") {
    void (async () => {
      try {
        const pipe = await classifier();
        const scores: number[] = [];
        for (const chunk of message.chunks) {
          const output = await pipe(chunk, { top_k: null });
          const ai = output.find((row) => row.label === AI_LABEL)?.score ?? 0;
          scores.push(ai);
        }
        ctx.postMessage({ type: "scored", id: message.id, scores });
      } catch (error: unknown) {
        ctx.postMessage({
          type: "failed",
          message:
            error instanceof Error ? error.message : "The text could not be classified.",
        });
      }
    })();
  }
});

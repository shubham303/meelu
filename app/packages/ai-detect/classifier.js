import { AI_LABEL, MODEL_DTYPE, MODEL_ID } from "./constants.js";

export function createClassifier({ cacheDir, onProgress } = {}) {
  let pending = null;

  const load = () => {
    if (!pending) {
      pending = (async () => {
        const transformers = await import("@huggingface/transformers");
        if (cacheDir) transformers.env.cacheDir = cacheDir;
        return transformers.pipeline("text-classification", MODEL_ID, {
          dtype: MODEL_DTYPE,
          ...(onProgress ? { progress_callback: onProgress } : {}),
        });
      })();
      pending.catch(() => {
        pending = null;
      });
    }
    return pending;
  };

  const scoreChunks = async (texts) => {
    const pipe = await load();
    const scores = [];
    for (const text of texts) {
      const output = await pipe(text, { top_k: null });
      scores.push(output.find((row) => row.label === AI_LABEL)?.score ?? 0);
    }
    return scores;
  };

  return { load, scoreChunks };
}

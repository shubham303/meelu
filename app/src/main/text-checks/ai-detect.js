import { CONFIDENCE_LABEL, VERDICT_BLURB, VERDICT_LABEL, createClassifier, detect, sentenceSpans } from "@meelu/ai-detect";

let classifier = null;

function scorer(modelDir) {
  if (!classifier) classifier = createClassifier({ cacheDir: modelDir });
  return classifier.scoreChunks;
}

function anchorIn(body, text) {
  if (body.includes(text)) return text;
  const sentences = sentenceSpans(text)
    .map((s) => s.text)
    .filter((s) => s.length >= 20 && body.includes(s))
    .sort((a, b) => b.length - a.length);
  return sentences[0] ?? null;
}

function passageIssue(body, chunk, analysis) {
  const pct = Math.round(chunk.ai * 100);
  return {
    code: "ai_passage",
    title: `Passage reads ${pct}% machine-written`,
    detail: `Window ${chunk.index + 1} of ${analysis.chunks.length}, ${chunk.words} words. The classifier is right about four times in five, so read it back: if it is yours, break the rhythm — a shorter sentence, a concrete detail, an opinion.`,
    anchorText: anchorIn(body, chunk.text),
    suggestion: null,
  };
}

function signalIssue(body, signal) {
  const span = signal.spans.find((s) => body.includes(s.text)) ?? null;
  return {
    code: `ai_signal_${signal.id.replace(/-/g, "_")}`,
    title: `${signal.label}: ${signal.value}`,
    detail: `${signal.note} ${signal.trigger}`,
    anchorText: span ? span.text : null,
    suggestion: null,
  };
}

export async function checkAiDetect(text, context = {}, { scoreChunks } = {}) {
  const body = String(text ?? "");
  const result = await detect(body, scoreChunks ?? scorer(context.modelDir));
  if (!result.ok) {
    return { summary: { verdict: "too-short", verdictLabel: VERDICT_LABEL["too-short"], words: result.words }, issues: [] };
  }
  const summary = {
    verdict: result.verdict,
    verdictLabel: VERDICT_LABEL[result.verdict],
    score: result.score,
    median: result.median,
    confidence: result.confidence,
    confidenceLabel: CONFIDENCE_LABEL[result.confidenceBand],
    words: result.words,
    spread: result.spread,
    windows: result.chunks.length,
  };
  const issues = [];
  if (result.verdict === "ai" || result.verdict === "mixed") {
    issues.push({
      code: `ai_${result.verdict}`,
      title: `${VERDICT_LABEL[result.verdict]} — ${result.score}% (${CONFIDENCE_LABEL[result.confidenceBand].toLowerCase()})`,
      detail: VERDICT_BLURB[result.verdict],
      anchorText: null,
      suggestion: null,
    });
  }
  for (const chunk of result.flagged) issues.push(passageIssue(body, chunk, result));
  if (result.verdict !== "human") {
    for (const signal of result.signals) {
      if (signal.leaning === "ai" && signal.spans.length) issues.push(signalIssue(body, signal));
    }
  }
  return { summary, issues };
}

import { FREE_WORD_LIMIT } from "@/lib/limits";

/**
 * The classifier. AICodexLab/answerdotai-ModernBERT-base-ai-detector, converted to
 * ONNX by onnx-community, run in the browser through transformers.js.
 *
 * Picked over onnx-community/e5-small-lora-ai-generated-detector-ONNX (34 MB) after
 * measuring both on 176 hand-labelled 100-word windows: ModernBERT got 81.8% of them
 * right, the smaller model 50% — it scored this site's own hand-written blog posts at
 * 62% AI on average, which is a coin toss dressed up as a number. The 8-bit model is
 * four times the download and the only one of the two worth shipping.
 */
export const MODEL_ID = "onnx-community/answerdotai-ModernBERT-base-ai-detector-ONNX";

/** 8-bit weights. The float32 build is 571 MB, which nobody is downloading in a tab. */
export const MODEL_DTYPE = "q8";

/** Model file + tokenizer + the ONNX runtime WebAssembly, measured over the wire. */
export const DOWNLOAD_MB = 156;

/** Label index 1 is AI-generated, index 0 is human — from the upstream model card, and confirmed by hand. */
export const AI_LABEL = "LABEL_1";

/**
 * What one free check reads. Shared with the other free tools. Every extra
 * word is another pass through the classifier in the visitor's own tab, so
 * this cap is doing more work here than it is anywhere else.
 */
export const MAX_WORDS = FREE_WORD_LIMIT;

/** Below this the classifier is guessing, so we say so instead of printing a number. */
export const MIN_WORDS_TO_JUDGE = 200;

/** Below this there is not enough text to run at all. */
export const MIN_WORDS_TO_RUN = 50;

/**
 * Window size, chosen from measurement rather than from the round number.
 *
 * We ran hand-written prose through the classifier at eight window sizes. At 40 words it
 * called 61.7% of human windows AI; at 100 words, 11.7%; at 170 and above, none of them.
 * Genuinely generated text scored 100% at every size, so a larger window costs nothing on
 * the detection side and buys most of the false-positive rate back. 200 still gives a
 * useful per-section breakdown on anything article-length.
 */
export const TARGET_CHUNK_WORDS = 200;
/** Never score fewer words than this on their own — that is where the noise lives. */
export const MIN_CHUNK_WORDS = 120;
export const MAX_CHUNK_WORDS = 340;
/** Close enough to target that a paragraph end is worth breaking on. */
export const SOFT_BREAK_WORDS = 150;

/** Verdict bands, set from the measured distribution rather than picked to look decisive. */
export const AI_AT = 70;
export const HUMAN_AT = 35;

/** A window at or above this is worth a second read. */
export const FLAG_AT = 70;

/**
 * Confidence is never allowed past this. The model got 81.8% of our test windows right
 * and the published literature puts detectors of this class at 75–85%, so a number
 * above that would be a lie however sure the softmax looks.
 */
export const MAX_CONFIDENCE = 85;
export const MIN_CONFIDENCE = 35;

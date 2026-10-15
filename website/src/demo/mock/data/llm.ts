import type { LlmModel, LlmTier } from "@demo/features/llm-models/models";

export const DEFAULT_MODEL = "anthropic/claude-haiku-5.5";

const FEATURED = ["anthropic/claude-haiku-5.5", "deepseek/deepseek-v4-flash", "openai/gpt-6-luna"];
const WELL_KNOWN = new Set(["anthropic", "openai", "deepseek", "google", "x-ai", "qwen", "moonshotai", "z-ai", "mistralai"]);

const SEEDS: [string, string, number, number, number][] = [
  ["anthropic/claude-haiku-5.5", "Anthropic: Claude Haiku 5.5", 1, 5, 400_000],
  ["deepseek/deepseek-v4-flash", "DeepSeek: DeepSeek V4 Flash", 0.14, 0.42, 256_000],
  ["openai/gpt-6-luna", "OpenAI: GPT-6 Luna", 1.5, 6, 400_000],
  ["anthropic/claude-sonnet-5.5", "Anthropic: Claude Sonnet 5.5", 3, 15, 1_000_000],
  ["anthropic/claude-opus-5.5", "Anthropic: Claude Opus 5.5", 5, 25, 1_000_000],
  ["openai/gpt-6", "OpenAI: GPT-6", 5, 30, 400_000],
  ["openai/gpt-6-mini", "OpenAI: GPT-6 mini", 0.3, 1.8, 400_000],
  ["google/gemini-3.5-pro", "Google: Gemini 3.5 Pro", 2.5, 15, 1_048_576],
  ["google/gemini-3.5-flash", "Google: Gemini 3.5 Flash", 0.3, 2.5, 1_048_576],
  ["google/gemini-3.5-flash-lite", "Google: Gemini 3.5 Flash Lite", 0.1, 0.4, 1_048_576],
  ["deepseek/deepseek-v4.1-flash", "DeepSeek: DeepSeek V4.1 Flash", 0.15, 0.45, 256_000],
  ["deepseek/deepseek-v4", "DeepSeek: DeepSeek V4", 0.55, 2.2, 256_000],
  ["x-ai/grok-5", "xAI: Grok 5", 3, 15, 512_000],
  ["x-ai/grok-5-fast", "xAI: Grok 5 Fast", 0.2, 0.5, 2_000_000],
  ["qwen/qwen4-235b-a22b", "Qwen: Qwen4 235B A22B", 0.13, 0.6, 262_144],
  ["qwen/qwen4-coder", "Qwen: Qwen4 Coder", 0.22, 0.95, 262_144],
  ["moonshotai/kimi-k3", "MoonshotAI: Kimi K3", 0.6, 2.5, 262_144],
  ["z-ai/glm-5", "Z.ai: GLM 5", 0.45, 1.9, 204_800],
  ["mistralai/mistral-large-3", "Mistral: Mistral Large 3", 0.5, 1.5, 262_144],
  ["mistralai/mistral-medium-4", "Mistral: Mistral Medium 4", 0.4, 2, 131_072],
  ["mistralai/devstral-2", "Mistral: Devstral 2", 0.1, 0.3, 262_144],
  ["meta-llama/llama-5-maverick", "Meta: Llama 5 Maverick", 0.15, 0.6, 1_048_576],
  ["meta-llama/llama-5-scout", "Meta: Llama 5 Scout", 0.08, 0.3, 1_048_576],
  ["nvidia/nemotron-ultra-2", "NVIDIA: Nemotron Ultra 2", 0.6, 1.8, 131_072],
  ["cohere/command-a-2", "Cohere: Command A 2", 2.5, 10, 256_000],
  ["amazon/nova-pro-2", "Amazon: Nova Pro 2", 0.8, 3.2, 300_000],
  ["minimax/minimax-m3", "MiniMax: MiniMax M3", 0.3, 1.2, 1_000_000],
  ["inception/mercury-2", "Inception: Mercury 2", 0.25, 1, 128_000],
];

function tierOf(id: string): LlmTier {
  if (FEATURED.includes(id)) return "featured";
  return WELL_KNOWN.has(id.split("/", 1)[0]) ? "well_known" : "other";
}

const TIER_ORDER: Record<LlmTier, number> = { featured: 0, well_known: 1, other: 2 };

export const MODELS: LlmModel[] = SEEDS.map(([id, name, input, output, contextLength]) => ({
  id,
  name,
  provider: id.split("/", 1)[0],
  tier: tierOf(id),
  inputUsdPerMillion: input,
  outputUsdPerMillion: output,
  contextLength,
})).sort((a, b) => {
  const pos = (m: LlmModel) => (m.tier === "featured" ? FEATURED.indexOf(m.id) : 0);
  return (
    TIER_ORDER[a.tier] - TIER_ORDER[b.tier] ||
    pos(a) - pos(b) ||
    a.inputUsdPerMillion + a.outputUsdPerMillion - (b.inputUsdPerMillion + b.outputUsdPerMillion) ||
    a.id.localeCompare(b.id)
  );
});

import { crawlFetch, withOutboundSlot } from "../net.js";
import { pool, USER_AGENT } from "./fetch.js";

export const AI_PROBE_AGENTS = [
  {
    agent: "OAI-SearchBot",
    ua: "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
  },
  {
    agent: "ChatGPT-User",
    ua: "Mozilla/5.0 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)",
  },
  {
    agent: "Claude-SearchBot",
    ua: "Mozilla/5.0 (compatible; Claude-SearchBot/1.0; +https://www.anthropic.com/claude-searchbot)",
  },
  {
    agent: "Claude-User",
    ua: "Mozilla/5.0 (compatible; Claude-User/1.0; +Claude-User@anthropic.com)",
  },
  {
    agent: "PerplexityBot",
    ua: "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
  },
  {
    agent: "Perplexity-User",
    ua: "Mozilla/5.0 (compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)",
  },
  {
    agent: "Applebot",
    ua:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) " +
      "Version/13.1.1 Safari/605.1.15 (Applebot/0.1; +http://www.apple.com/go/applebot)",
  },
  {
    agent: "Amazonbot",
    ua: "Mozilla/5.0 (compatible; Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot)",
  },
];

const REFUSAL = new Set([401, 403, 405, 418, 429, 451]);

const CHALLENGE =
  /(just a moment|checking your browser|enable javascript and cookies|cf[-_]browser[-_]verification|cf[-_]chl|attention required|access denied|request unsuccessful|are you a robot)/i;

const SHRUNK = 0.4;
const MIN_COMPARABLE_BYTES = 1000;

async function read(url, ua) {
  return withOutboundSlot(async () => {
    try {
      const res = await crawlFetch(url, {
        headers: { "user-agent": ua, accept: "text/html" },
        redirect: "follow",
        signal: AbortSignal.timeout(15_000),
      });
      const text = await res.text();
      return { status: res.status, bytes: Buffer.byteLength(text), text };
    } catch {
      return null;
    }
  });
}

function judge(baseline, result) {
  if (!result) return { verdict: "unknown", reason: "could not be reached" };
  if (baseline.status !== 200) return { verdict: "unknown", reason: "nothing to compare against" };

  if (REFUSAL.has(result.status)) {
    return { verdict: "blocked", reason: `was refused with HTTP ${result.status}` };
  }
  if (result.status >= 400) {
    return {
      verdict: "blocked",
      reason: `got HTTP ${result.status} from a page that answers 200 for an ordinary crawler`,
    };
  }
  if (CHALLENGE.test(result.text.slice(0, 4000))) {
    return { verdict: "blocked", reason: "was served a bot challenge instead of the home page" };
  }
  if (baseline.bytes >= MIN_COMPARABLE_BYTES && result.bytes < baseline.bytes * SHRUNK) {
    const share = Math.round((result.bytes / baseline.bytes) * 100);
    return {
      verdict: "blocked",
      reason: `was served a page ${share}% the size of the one an ordinary crawler gets`,
    };
  }
  return { verdict: "allowed", reason: "" };
}

export async function probeCrawlerAccess(origin) {
  const url = new URL("/", origin).toString();
  const checkedAt = new Date().toISOString();
  const baseline = (await read(url, USER_AGENT)) ?? { status: null, bytes: null, text: "" };

  const results = await pool(AI_PROBE_AGENTS, 4, ({ ua }) => read(url, ua));

  const agents = AI_PROBE_AGENTS.map(({ agent }, i) => {
    const result = results[i];
    const { verdict: state, reason } = judge(baseline, result);
    return {
      agent,
      status: result?.status ?? null,
      bytes: result?.bytes ?? null,
      verdict: state,
      ...(reason ? { reason } : {}),
    };
  });

  return {
    checkedAt,
    url,
    baseline: { status: baseline.status, bytes: baseline.bytes },
    agents,
  };
}

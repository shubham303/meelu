const CANDIDATES = [
  "http://localhost:8080",
  "http://127.0.0.1:60199",
  "http://localhost:11434",
];

async function probe(baseUrl: string) {
  try {
    const res = await fetch(`${baseUrl}/props`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return null;
    const props = (await res.json()) as {
      default_generation_settings?: { n_ctx?: number };
      model_path?: string;
    };
    return {
      context: props.default_generation_settings?.n_ctx ?? null,
      model: props.model_path ?? null,
    };
  } catch {
    return null;
  }
}

async function chat(baseUrl: string) {
  const res = await fetch(`${baseUrl}/v1/chat/completions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      messages: [{ role: "user", content: "Reply with exactly one word: pong" }],
      max_tokens: 512,
    }),
    signal: AbortSignal.timeout(30000),
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  const json = (await res.json()) as {
    model?: string;
    choices?: { message?: { content?: string; reasoning_content?: string } }[];
  };
  const msg = json.choices?.[0]?.message;
  return { model: json.model, reply: msg?.content, thought: msg?.reasoning_content?.slice(0, 80) };
}

for (const baseUrl of CANDIDATES) {
  const props = await probe(baseUrl);
  if (!props) {
    console.log(`${baseUrl} — no llama.cpp /props endpoint`);
    continue;
  }
  console.log(`${baseUrl} — llama.cpp server, context=${props.context}, model=${props.model}`);
  try {
    const { model, reply, thought } = await chat(baseUrl);
    console.log(`  chat OK: model=${model}, reply=${JSON.stringify(reply)}, thought=${JSON.stringify(thought)}...`);
  } catch (err) {
    console.log(`  chat FAILED: ${(err as Error).message}`);
  }
}

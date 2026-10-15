import { channel, sleep, uid } from "./channel";
import { chargeTurn } from "./hooks";
import { scopeDef, scopeResponse } from "./scope";
import { answer, type Memory, type Step } from "./answers";

export interface TurnEvent {
  turnId: string;
  event: string;
  data: Record<string, unknown>;
}

export interface TurnPayload {
  action: string;
  siteId: string | null;
  message: string;
  sessionId?: string;
  form?: Record<string, string | undefined>;
  params?: Record<string, string>;
  files?: Array<{ name: string; type: string; data: string }>;
  history?: { role: "user" | "assistant"; text: string }[];
  model?: string;
}

export type Decision = "allow" | "always" | "full" | "deny";

export const turnChannel = channel<TurnEvent>();

const sessions = new Map<string, Memory>();
const aborted = new Set<string>();
const pendingPermissions = new Map<string, { resolve: (d: "allow" | "deny") => void; tool: string; turnId: string }>();
const grants = { full: false, always: new Set<string>() };

export const usage = {
  tokens: 0,
  inputTokens: 0,
  outputTokens: 0,
  costUsd: 0,
  turns: 0,
  startedAt: Date.now(),
};

class Aborted extends Error {}

function emitter(turnId: string) {
  return (event: string, data: Record<string, unknown>) => {
    if (aborted.has(turnId)) throw new Aborted();
    turnChannel.emit({ turnId, event, data });
  };
}

function askPermission(turnId: string, tool: string, input: Record<string, unknown>): Promise<"allow" | "deny"> {
  if (grants.full || grants.always.has(tool)) return Promise.resolve("allow");
  return new Promise((resolve) => {
    const requestId = uid("perm");
    pendingPermissions.set(requestId, { resolve, tool, turnId });
    turnChannel.emit({ turnId, event: "permission", data: { requestId, tool, input } });
  });
}

export function respondPermission(requestId: string, decision: Decision) {
  const pending = pendingPermissions.get(requestId);
  if (!pending) return { ok: false };
  pendingPermissions.delete(requestId);
  if (decision === "always") grants.always.add(pending.tool);
  if (decision === "full") grants.full = true;
  pending.resolve(decision === "deny" ? "deny" : "allow");
  return { ok: true };
}

async function streamText(turnId: string, emit: ReturnType<typeof emitter>, body: string, state: { sent: boolean }) {
  if (!body) return;
  if (state.sent) emit("text", { text: "\n\n" });
  state.sent = true;
  const parts = body.split(/(?<=\s)/);
  const step = body.length > 1200 ? 6 : 3;
  for (let i = 0; i < parts.length; i += step) {
    emit("text", { text: parts.slice(i, i + step).join("") });
    await sleep(14 + Math.random() * 22);
    if (aborted.has(turnId)) throw new Aborted();
  }
}

async function run(turnId: string, payload: TurnPayload, memory: Memory, sessionId: string) {
  const emit = emitter(turnId);
  const def = scopeDef(payload.action);
  const scope = scopeResponse(payload.action);
  await sleep(220);
  emit("session", { sessionId });
  emit("scope", { action: payload.action, readOnly: scope.writes.length === 0, writes: scope.writes, reviewTools: scope.localTools });

  const steps: Step[] = answer({
    action: payload.action,
    message: payload.message,
    lower: payload.message.toLowerCase(),
    siteId: payload.siteId,
    form: payload.form ?? {},
    sessionId,
    memory,
  });

  const state = { sent: false };
  let written = "";
  for (const s of steps) {
    if (s.kind === "tool") {
      await sleep(s.ms ?? 450 + Math.random() * 500);
      emit("tool", { name: s.name });
    } else if (s.kind === "progress") {
      await sleep(300);
      emit("tool", { name: s.tool });
      for (let done = 1; done <= s.total; done++) {
        await sleep(380 + Math.random() * 300);
        emit("progress", { tool: s.tool, done, total: s.total });
      }
    } else if (s.kind === "text") {
      await sleep(350);
      await streamText(turnId, emit, s.text, state);
      written += (written ? "\n\n" : "") + s.text;
    } else {
      await sleep(400);
      emit("tool", { name: s.tool });
      const decision = await askPermission(turnId, s.tool, s.input);
      if (aborted.has(turnId)) throw new Aborted();
      if (decision === "deny") {
        await streamText(turnId, emit, s.declined, state);
        written += (written ? "\n\n" : "") + s.declined;
        break;
      }
      await sleep(500);
      s.apply();
      if (def?.writes.includes(s.tool)) emit("wrote", { tool: s.tool });
      if (s.created) emit("created", {});
      const after = typeof s.after === "function" ? s.after() : s.after;
      if (after) {
        await streamText(turnId, emit, after, state);
        written += (written ? "\n\n" : "") + after;
      }
    }
  }
  if (written) memory.lastAnswer = written;

  const outputTokens = Math.round(written.length / 3.6) + 120;
  const inputTokens = 5_800 + steps.length * 1_400 + memory.turns * 2_100;
  const costUsd = Math.round((inputTokens * 3 + outputTokens * 15) / 1_000) / 1_000;
  memory.turns += 1;
  usage.turns += 1;
  usage.inputTokens += inputTokens;
  usage.outputTokens += outputTokens;
  usage.tokens = usage.inputTokens + usage.outputTokens;
  usage.costUsd = Math.round((usage.costUsd + costUsd) * 1000) / 1000;
  chargeTurn(costUsd);
  emit("done", { ok: true, costUsd, tokens: inputTokens + outputTokens, inputTokens, outputTokens, error: null });
}

export function runTurn(payload: TurnPayload): { turnId?: string; error?: string } {
  if (!payload?.message?.trim()) return { error: "Missing message." };
  const def = scopeDef(payload.action);
  if (!def) return { error: `Unknown agent action "${payload.action}".` };
  if (!payload.siteId && !def.global) return { error: "This action needs a website — pick one first." };
  if (payload.files?.length && def.attachments === false) {
    return { error: "This desk works only on the data in Meelu's database; it does not take attached files." };
  }
  const turnId = uid("turn");
  const sessionId = payload.sessionId && sessions.has(payload.sessionId) ? payload.sessionId : (payload.sessionId ?? uid("sess"));
  let memory = sessions.get(sessionId);
  if (!memory) {
    memory = { action: payload.action, turns: 0, pending: null, awaiting: null, lastAnswer: "", data: {} };
    const lastAssistant = [...(payload.history ?? [])].reverse().find((h) => h.role === "assistant");
    if (lastAssistant) memory.lastAnswer = lastAssistant.text;
    sessions.set(sessionId, memory);
  }
  const live = memory;
  void run(turnId, payload, live, sessionId).catch((e: unknown) => {
    if (e instanceof Aborted) return;
    turnChannel.emit({
      turnId,
      event: "done",
      data: { ok: false, costUsd: 0, tokens: 0, error: e instanceof Error ? e.message : "The agent run failed." },
    });
  });
  return { turnId };
}

export function abortTurn(turnId: string) {
  if (aborted.has(turnId)) return;
  aborted.add(turnId);
  for (const [id, p] of pendingPermissions) {
    if (p.turnId !== turnId) continue;
    pendingPermissions.delete(id);
    p.resolve("deny");
  }
  turnChannel.emit({ turnId, event: "done", data: { ok: false, costUsd: 0, tokens: 0, error: "Stopped." } });
}

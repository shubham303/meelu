import type { UserProfile } from "@demo/lib/types";
import { call } from "../hooks";
import { lines, text, tool, type Ctx, type Script, type Step } from "./common";

function saveStep(fields: Partial<UserProfile>, after: string): Step {
  return {
    kind: "write",
    tool: "save_profile",
    input: { fields: Object.keys(fields) },
    created: true,
    apply: () => {
      call("PUT", "/api/v1/profile", fields);
    },
    after,
    declined: "Nothing saved. Your profile is as it was.",
  };
}

function current(): UserProfile | null {
  return call<UserProfile>("GET", "/api/v1/profile");
}

function readBack(): Script {
  const p = current();
  const row = (label: string, v: string | undefined) => `- **${label}:** ${v && v.trim() ? v : "*empty*"}`;
  const empty = p
    ? (["role", "company", "timezone", "bio", "writingVoice", "signature", "linkedinUrl", "xUrl", "websiteUrl"] as const).filter((k) => !p[k]?.trim())
    : [];
  return [
    tool("run_sql"),
    text(
      lines(
        "Your profile as it is stored:",
        "",
        row("Name", p?.fullName),
        row("Role", p?.role),
        row("Company", p?.company),
        row("Time zone", p?.timezone),
        row("Bio", p?.bio),
        row("Voice", p?.writingVoice),
        row("LinkedIn", p?.linkedinUrl),
        row("X", p?.xUrl),
        row("Website", p?.websiteUrl),
        "",
        "**Sign-off**",
        "```",
        p?.signature?.trim() || "(empty)",
        "```",
        "",
        empty.length === 0 ? "Every field is filled. I have changed nothing." : `Still empty: ${empty.join(", ")}. I have changed nothing.`,
      ),
    ),
  ];
}

function signOff(ctx: Ctx): Script {
  ctx.memory.awaiting = (c) => {
    const block = c.message.trim();
    c.memory.pending = () => [saveStep({ signature: block }, "Saved your sign-off. Everything written as you now ends with it; your other fields are untouched.")];
    return [text(lines("Here is the block as it will appear:", "", "```", block, "```", "", "Say **yes** to save it exactly like that."))];
  };
  return [tool("run_sql"), text("Send me the exact lines you want at the end of anything written as you — name, role, whatever follows. Put each on its own line.")];
}

function voice(ctx: Ctx): Script {
  ctx.memory.awaiting = (c) => {
    const said = c.message.trim().replace(/\s+/g, " ");
    const description = `Plain and direct, first person. ${said.length > 20 ? `In their words: ${said.slice(0, 220)}${said.length > 220 ? "…" : ""}` : ""} Short sentences, specific numbers over adjectives, no hype, no exclamation marks.`.replace(/\s+/g, " ").trim();
    c.memory.pending = () => [saveStep({ writingVoice: description }, "Saved your voice. Drafts on the Content desk and replies on Social Listening use it from now on.")];
    return [text(lines("Here is how I would describe it:", "", `> ${description}`, "", "Would you recognise that as you? Say **yes** to save it, or tell me what to change."))];
  };
  return [text("Two questions. What do you sound like at your best — tone, sentence length, words you like? And what do you never want to sound like?")];
}

const INTERVIEW = [
  "Let's start with you: what is your name and your role at the business?",
  "What does the business do, in one or two sentences, and who is it for?",
  "Who do you write for — who reads what Meelu drafts as you?",
];

function setup(ctx: Ctx): Script {
  const p = current();
  const answers: string[] = [];
  const ask = (i: number): ((c: Ctx) => Script) => (c) => {
    answers.push(c.message.trim());
    if (i + 1 < INTERVIEW.length) {
      c.memory.awaiting = ask(i + 1);
      return [text(INTERVIEW[i + 1])];
    }
    const [who, what, readers] = answers;
    const bio = `${who}. ${what}.`.replace(/\s+/g, " ").replace(/([.!?])\./g, "$1");
    c.memory.pending = () => [saveStep({ bio, writingVoice: p?.writingVoice || `Writes for ${readers}. Plain, specific, first person.` }, "Saved your profile in one go. Read it back any time from this panel, or edit it on the Settings screen.")];
    return [
      text(
        lines(
          "Here is what I would save:",
          "",
          `- **Bio:** ${bio}`,
          `- **Readers:** ${readers}`,
          p?.writingVoice ? "- **Voice:** unchanged — you already have one." : "",
          "",
          "Say **yes** to save it all, or correct anything first.",
        ),
      ),
    ];
  };
  ctx.memory.awaiting = ask(0);
  return [
    tool("run_sql"),
    text(
      lines(
        p?.fullName ? `I can see a profile already — ${p.fullName}${p.role ? `, ${p.role}` : ""}. I will only fill in or replace what you confirm.` : "Your profile is empty, so we start from scratch.",
        "",
        INTERVIEW[0],
      ),
    ),
  ];
}

export function profileAnswer(ctx: Ctx): Script {
  const l = ctx.lower;
  if (l.includes("read back the profile")) return readBack();
  if (l.includes("set the sign-off")) return signOff(ctx);
  if (l.includes("describe my writing voice")) return voice(ctx);
  if (l.includes("set up my profile")) return setup(ctx);
  return [
    tool("run_sql"),
    text("I can read back your profile, set your sign-off, describe how you sound, or walk through the whole profile one question at a time. Which would you like?"),
  ];
}

import { MockHttpError } from "../core";

const NOTES = ["save_note", "update_note", "delete_note"];

export interface DeskOffer {
  name: string;
  blurb: string;
  brief: string;
}

export interface AgentScopeResponse {
  action: string;
  writes: string[];
  desk: string;
  createToolName: string | string[] | null;
  global: boolean;
  allowAttachments: boolean;
  limits: Record<string, number>;
  providers: string[];
  localTools: string[];
  silentWrites: string[];
  desks: DeskOffer[];
  systemPrompt: string;
}

interface ScopeDef {
  desk: string;
  writes: string[];
  create?: string;
  global?: boolean;
  attachments?: boolean;
  limits?: Record<string, number>;
  providers?: string[];
  localTools?: string[];
  silent?: string[];
  prompt: string;
}

const STRUCTURE_WRITES = [
  "start_structure_job",
  "reconcile_structure_suggestions",
  "propose_hierarchy_links",
  "propose_unlinked_mentions",
  "propose_links_from_table",
  "propose_link_removals",
  "screen_link_suggestions",
  "rank_link_suggestions",
  "propose_pillar_pages",
  "screen_pillar_suggestions",
  "rank_pillar_suggestions",
  "finish_structure_job",
  "delete_structure_suggestion",
];

const STANDARD = { maxTurns: 60, maxBudgetUsd: 3 };

export const SCOPES: Record<string, ScopeDef> = {
  plan: {
    desk: "workspace",
    writes: [],
    limits: {},
    prompt: "You plan work across this website's desks. You read; you never write.",
  },
  "ask-site": {
    desk: "site",
    writes: ["save_site_market", "create_site_issue", "reject_issue", "restore_issue", ...STRUCTURE_WRITES, ...NOTES],
    localTools: ["review_link_suggestions", "review_pillar_suggestions"],
    prompt: "You answer questions about the website record, its crawl and its structure, and run structure strategies that end in suggestions the owner reviews.",
  },
  "ask-seo": {
    desk: "seo",
    writes: [
      "add_to_seo_list",
      "remove_from_seo_list",
      "track_keyword_rankings",
      "track_keyword_volumes",
      "save_site_market",
      "create_keyword_clusters",
      "compute_metrics_for_cluster",
      ...NOTES,
    ],
    limits: { maxTurns: 40, maxBudgetUsd: 2 },
    providers: ["seo-data"],
    prompt: "You read measured search and traffic data and the saved SEO lists, and suggest what to target. Every number you quote is measured.",
  },
  "ask-pages": {
    desk: "pages",
    writes: ["set_page_type", ...NOTES],
    silent: ["set_page_type"],
    prompt: "You search and read the crawled pages of this website and answer from what they say.",
  },
  "issue-review": {
    desk: "technical-seo",
    writes: ["reject_issue", "restore_issue", ...NOTES],
    limits: { maxTurns: 80, maxBudgetUsd: 5 },
    prompt: "You review the technical audit with the owner: what each finding costs, which pages it touches, which are cosmetic.",
  },
  "content-draft": {
    desk: "content",
    writes: ["content_update_piece", ...NOTES],
    prompt: "You edit one web page with the owner. Changes land as marked proposals they keep or discard.",
  },
  "content-piece": {
    desk: "content",
    writes: ["content_create_piece", ...NOTES],
    create: "mcp__meelu__content_create_piece",
    prompt: "You plan and write one web page for this website, grounded in its search data and crawled pages, and save it as a draft once the owner agrees.",
  },
  "ask-content": {
    desk: "content",
    writes: ["content_create_piece", "content_update_piece", ...NOTES],
    prompt: "You answer questions about the pieces on the Content desk.",
  },
  "profile-setup": {
    desk: "profile",
    writes: ["save_profile", "clear_profile_fields"],
    create: "mcp__meelu__save_profile",
    global: true,
    limits: {},
    prompt: "You set up the owner's profile: who they are and how they sound. Save only what they confirm.",
  },
  "ask-analytics": {
    desk: "analytics",
    writes: ["analytics_save_report", "analytics_update_report", ...NOTES],
    attachments: false,
    prompt: "You analyse this website's Search Console, Analytics and page data with the deterministic analytics tools, and save reports when asked.",
  },
  "social-listening-setup": {
    desk: "social-listening",
    writes: ["social_listening_save_queries", ...NOTES],
    limits: { maxTurns: 30, maxBudgetUsd: 1.5 },
    prompt: "You help the owner write the lines Meelu listens for.",
  },
  "ask-social-listening": {
    desk: "social-listening",
    writes: ["social_listening_update_post", "social_listening_save_queries", ...NOTES],
    prompt: "You help the owner decide which social posts deserve a reply and suggest angles. They write and send the reply themselves.",
  },
  "compose-reply": {
    desk: "social-listening",
    writes: [...NOTES],
    limits: { maxTurns: 8, maxBudgetUsd: 0.3 },
    prompt: "You draft one reply to one social post, in the owner's voice, for them to edit and send.",
  },
};

const DESK_BLURBS: Record<string, string> = {
  profile: "The business profile record — who the user is, what they sell, voice and positioning; save or clear its fields.",
  site: "The website record and site-wide technical issues — record one the audit missed, reject or restore one.",
  seo: "Search Console, Analytics and the saved SEO lists — find and curate competitors and backlink opportunities.",
  pages: "The crawled page corpus — search pages by text or crawl facts.",
  "technical-seo": "The technical audit — open issues, turn-downs, reject or restore findings.",
  content: "Web pages written for the site — create and revise pieces with their title, H1, meta description, slug and target keyword.",
  "social-listening": "Social posts where a reply from the site belongs, found from the lines of text the user listens for — set reply angles and statuses, grow the list of lines.",
  analytics: "Analysis over this website's Search Console, Analytics and page data in the database — profiling, clustering, forecasting, period comparison, metric drivers; save reports.",
};

function deskWrites(desk: string): string[] {
  const all = Object.values(SCOPES)
    .filter((s) => s.desk === desk)
    .flatMap((s) => s.writes);
  return [...new Set(all)];
}

export function scopeDef(action: string): ScopeDef | null {
  return SCOPES[action] ?? null;
}

export function scopeResponse(action: string, desks: string = ""): AgentScopeResponse {
  const def = SCOPES[action];
  if (!def) {
    throw new MockHttpError(404, `Unknown agent action "${action}". Known: ${Object.keys(SCOPES).join(", ")}.`);
  }
  const extra = desks
    .split(",")
    .map((d) => d.trim())
    .filter((d) => d && d !== def.desk);
  for (const name of extra) {
    if (!DESK_BLURBS[name]) {
      throw new MockHttpError(400, `Unknown desk '${name}'. Loadable: ${Object.keys(DESK_BLURBS).sort().join(", ")}.`);
    }
  }
  const loaded = new Set([def.desk, ...extra]);
  const writes = [...new Set([...def.writes, ...extra.flatMap(deskWrites)])];
  return {
    action,
    writes,
    desk: def.desk,
    createToolName: def.create ?? null,
    global: def.global === true,
    allowAttachments: def.attachments !== false,
    limits: def.limits ?? STANDARD,
    providers: def.providers ?? [],
    localTools: def.localTools ?? [],
    silentWrites: def.silent ?? [],
    desks: Object.entries(DESK_BLURBS)
      .filter(([name]) => !loaded.has(name))
      .sort(([a], [c]) => a.localeCompare(c))
      .map(([name, blurb]) => ({
        name,
        blurb,
        brief: `The ${name} desk is loaded. Its tools are in your tool list now. Writes it adds: ${deskWrites(name).map((w) => `\`${w}\``).join(", ") || "none"}.`,
      })),
    systemPrompt: def.prompt,
  };
}

const URL_RE = /https?:\/\/[^\s)\]>]+/gi;
const HASHTAG_RE = /(?<![\w&])#[A-Za-z][\w]*/g;
const EMOJI_RE = /\p{Extended_Pictographic}(?:️|‍\p{Extended_Pictographic})*/gu;
const PHONE_RE = /(?:\+?\d[\d\s().-]{7,}\d)/g;
const MARKDOWN_RE = /(\*\*[^*\n]+\*\*|__[^_\n]+__|(?<!\w)\*[^*\n]+\*(?!\w)|(?<!\w)_[^_\n]+_(?!\w)|^\s{0,3}#{1,6}\s+\S|\[[^\]]+\]\([^)]+\)|`[^`\n]+`)/m;

const LLM_TELLS = [
  "delve",
  "leverage",
  "in today's landscape",
  "in today's fast-paced",
  "game-changer",
  "game changer",
  "unlock",
  "supercharge",
  "dive into",
  "elevate your",
  "it's not just",
  "it is not just",
  "in the ever-evolving",
  "seamlessly",
  "a testament to",
];

const ENGAGEMENT_BAIT = [
  "agree?",
  "who else",
  "save this for later",
  "follow for follow",
  "follow-for-follow",
  "like if you agree",
  "tag a friend",
  "tag someone",
  "comment yes",
  "comment below",
  "double tap if",
  "double-tap if",
  "drop a",
  "share if",
  "thoughts? 👇",
  "thoughts?👇",
];

const THREAD_BAIT = ["a thread", "🧵", "bookmark this", "read to the end", "1/"];

const ANNOUNCEMENT_OPENERS = ["just shipped", "excited to announce", "thrilled to announce", "proud to announce"];

const RHETORICAL_OPENERS = ["ever wondered", "have you ever", "what if i told you", "did you know"];

const SUPERLATIVES = ["best", "amazing", "incredible", "unbelievable", "world-class", "ultimate", "perfect", "exciting news"];

const TIME_BOUND = ["this week only", "today only", "tonight", "this weekend", "limited time", "ends soon", "last chance", "hurry"];

const MARKETING = ["don't miss out", "act now", "limited offer", "exclusive", "revolutionary", "next-level", "cutting-edge"];

function paragraphs(text) {
  return text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

function lines(text) {
  return text.split("\n").map((l) => l.trim()).filter(Boolean);
}

function firstSentence(text) {
  const head = lines(text)[0] ?? "";
  const m = /^(.*?[.!?])(\s|$)/.exec(head);
  return (m ? m[1] : head).trim();
}

function lastLine(text) {
  const all = lines(text);
  return all[all.length - 1] ?? "";
}

function graphemes(text) {
  if (typeof Intl !== "undefined" && Intl.Segmenter) {
    return Array.from(new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text)).length;
  }
  return Array.from(text).length;
}

function findPhrase(text, phrases) {
  const lower = text.toLowerCase();
  for (const phrase of phrases) {
    const at = lower.indexOf(phrase.toLowerCase());
    if (at >= 0) return text.slice(at, at + phrase.length);
  }
  return null;
}

function findAllPhrases(text, phrases) {
  const lower = text.toLowerCase();
  const hits = [];
  for (const phrase of phrases) {
    const at = lower.indexOf(phrase.toLowerCase());
    if (at >= 0) hits.push(text.slice(at, at + phrase.length));
  }
  return hits;
}

function urls(text) {
  return text.match(URL_RE) ?? [];
}

function hashtags(text) {
  return text.match(HASHTAG_RE) ?? [];
}

function emojis(text) {
  return text.match(EMOJI_RE) ?? [];
}

function issue(code, title, detail, anchorText = null, suggestion = null) {
  return { code, title, detail, anchorText, suggestion };
}

const rule = {
  lengthBand:
    (min, max, note) =>
    ({ text, label }) => {
      const n = text.length;
      if (n < min && n > 0) {
        return issue(
          "under_sweet_spot",
          `${n} characters — ${label} reads best at ${min}–${max}`,
          `Short is fine when it says something; check this is not a fragment. ${note ?? ""}`.trim(),
        );
      }
      if (n > max) {
        return issue(
          "over_sweet_spot",
          `${n} characters — ${label} reads best at ${min}–${max}`,
          `Cut ${n - max} characters or split it. ${note ?? ""}`.trim(),
        );
      }
      return null;
    },

  hardLimit:
    (limit, unit = "characters") =>
    ({ text, label }) => {
      const n = unit === "graphemes" ? graphemes(text) : text.length;
      if (n <= limit) return null;
      return issue("over_limit", `${n} ${unit} — ${label} stops at ${limit}`, `Cut ${n - limit} ${unit}; the post will be rejected or truncated as it is.`);
    },

  effectiveLimitWithLinks:
    (target, linkCost) =>
    ({ text, label }) => {
      const found = urls(text);
      const n = text.replace(URL_RE, "").length + found.length * linkCost;
      if (n <= target) return null;
      return issue(
        "over_effective_limit",
        `~${n} characters once links are counted — write ${label} to ${target}`,
        `Each link costs about ${linkCost} characters after shortening. Leave room for a handle or quote-post.`,
      );
    },

  fold:
    (chars) =>
    ({ text, label }) => {
      const first = firstSentence(text);
      if (first.length <= chars) return null;
      return issue(
        "point_below_fold",
        `First sentence runs ${first.length} characters; ${label} shows about ${chars}`,
        "Make the point before the fold. The first sentence should be able to stand on its own.",
        first,
      );
    },

  paragraphLength:
    (maxChars) =>
    ({ text }) => {
      const wall = paragraphs(text).find((p) => p.length > maxChars && !p.includes("\n"));
      if (!wall) return null;
      return issue(
        "wall_of_text",
        `A paragraph runs ${wall.length} characters`,
        "Short paragraphs, one idea each, a blank line between. Break this one up.",
        wall,
      );
    },

  hashtagMax:
    (max) =>
    ({ text, label }) => {
      const tags = hashtags(text);
      if (tags.length <= max) return null;
      const allowed = max === 0 ? "none" : `${max} at most`;
      return issue(
        "hashtag_stuffing",
        `${tags.length} hashtags — ${label} wants ${allowed}`,
        max === 0 ? "Hashtags read as imported marketing on this channel. Remove them." : "Keep the ones a reader would actually follow and drop the rest.",
        tags[max] ?? tags[0],
      );
    },

  hashtagsAtEnd:
    () =>
    ({ text }) => {
      const tags = hashtags(text);
      if (!tags.length) return null;
      const tail = lastLine(text);
      const inBody = tags.find((t) => !tail.includes(t));
      if (!inBody) return null;
      return issue("hashtags_in_body", "Hashtags inside the copy", "Put hashtags on their own line at the end; in the body they break the sentence.", inBody);
    },

  noLinks:
    (why) =>
    ({ text }) => {
      const found = urls(text);
      if (!found.length) return null;
      return issue("link_in_body", "A link in the body", why, found[0]);
    },

  linkWarning:
    (why) =>
    ({ text }) => {
      const found = urls(text);
      if (!found.length) return null;
      return issue("link_in_body", `${found.length === 1 ? "A link" : `${found.length} links`} in the body`, why, found[0]);
    },

  emojiMax:
    (max) =>
    ({ text, label }) => {
      const found = emojis(text);
      if (found.length <= max) return null;
      return issue("emoji_count", `${found.length} emoji — ${label} takes ${max === 0 ? "none" : `at most ${max}`}`, "Emoji read as decoration here. Cut to the one that does work, or none.", found[max]);
    },

  emojiBullets:
    () =>
    ({ text }) => {
      const hit = lines(text).find((l) => EMOJI_RE.test(l.slice(0, 4)) && l.length > 4);
      EMOJI_RE.lastIndex = 0;
      if (!hit) return null;
      return issue("emoji_bullets", "Lines that open with an emoji", "Emoji bullets and emoji headers are the most recognisable template on the feed. Use plain lines.", hit);
    },

  broetry:
    (run, maxWords) =>
    ({ text }) => {
      const ps = paragraphs(text);
      let streak = 0;
      let start = 0;
      for (let i = 0; i < ps.length; i++) {
        const words = ps[i].split(/\s+/).length;
        if (!ps[i].includes("\n") && words <= maxWords) {
          if (streak === 0) start = i;
          streak += 1;
          if (streak >= run) {
            return issue("broetry", `${streak} one-line paragraphs in a row`, "The one. line. per. paragraph. rhythm reads as performance. Group the lines that belong together.", ps[start]);
          }
        } else {
          streak = 0;
        }
      }
      return null;
    },

  phrases:
    (code, title, detail, list) =>
    ({ text }) => {
      const hits = findAllPhrases(text, list);
      if (!hits.length) return null;
      return issue(code, hits.length === 1 ? `${title}: "${hits[0]}"` : `${title}: ${hits.map((h) => `"${h}"`).join(", ")}`, detail, hits[0]);
    },

  opener:
    (code, title, detail, list) =>
    ({ text }) => {
      const first = firstSentence(text);
      const hit = findPhrase(first, list);
      if (!hit || first.toLowerCase().indexOf(hit.toLowerCase()) > 8) return null;
      return issue(code, `${title}: "${hit}"`, detail, first);
    },

  rhetoricalOpener:
    () =>
    ({ text }) => {
      const first = firstSentence(text);
      if (!first.endsWith("?")) return null;
      if (!findPhrase(first, RHETORICAL_OPENERS)) return null;
      return issue("rhetorical_opener", "Opens with a rhetorical question", "Say the thing instead of asking whether the reader has wondered about it.", first);
    },

  weakClose:
    () =>
    ({ text }) => {
      const tail = lastLine(text);
      const hit = findPhrase(tail, ["thoughts?", "agree?", "what do you think?", "let me know", "👇"]);
      if (!hit) return null;
      return issue("weak_close", `Closes with "${hit}"`, "End with a real question or a clear takeaway, not an invitation to react.", tail);
    },

  noMarkdown:
    () =>
    ({ text, label }) => {
      const m = MARKDOWN_RE.exec(text);
      if (!m) return null;
      return issue("markdown_wont_render", `${label} does not render markdown`, "Bold, italics, headings and link syntax show up as literal characters. Use line breaks for structure and paste the bare URL.", m[0]);
    },

  exclamations:
    (max) =>
    ({ text }) => {
      const n = (text.match(/!/g) ?? []).length;
      if (n <= max) return null;
      const at = text.indexOf("!");
      const from = Math.max(0, text.lastIndexOf("\n", at) + 1);
      return issue("exclamation_marks", `${n} exclamation marks`, "State the fact plainly; this reads next to the listing, not in a feed.", text.slice(from, at + 1).trim());
    },

  phoneOrUrl:
    () =>
    ({ text }) => {
      const hit = urls(text)[0] ?? (text.match(PHONE_RE) ?? [])[0];
      if (!hit) return null;
      return issue("contact_in_body", "Phone number or URL in the body", "The profile already carries contact details; a post is for what changed.", hit.trim());
    },

  needsDate:
    () =>
    ({ text }) => {
      const hit = findPhrase(text, ["today", "tomorrow", "this week", "this weekend", "tonight", "next week"]);
      if (!hit) return null;
      const hasDate = /\b(\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}|\d{1,2}\/\d{1,2}|\d{4}-\d{2}-\d{2}|(mon|tues|wednes|thurs|fri|satur|sun)day)\b/i.test(text);
      if (hasDate) return null;
      return issue("relative_time_without_date", `"${hit}" without a date`, "Posts linger for weeks. Put the actual date in the text so it still reads right later.", hit);
    },

  mediaLimit:
    (limit) =>
    ({ text, hasMedia, label }) => {
      if (!hasMedia || text.length <= limit) return null;
      return issue("over_limit_with_media", `${text.length} characters — ${label} allows ${limit} when an image is attached`, `Attaching a picture cuts the budget to ${limit}. Cut ${text.length - limit} characters or drop the image.`);
    },

  requiresHeadings:
    () =>
    ({ text }) => {
      if (/^\s{0,3}#{2,3}\s+\S/m.test(text)) return null;
      if (text.split(/\s+/).length < 300) return null;
      return issue("no_headings", "No H2/H3 headings", "Long-form on the site is scanned first. Break it into sections with headings.");
    },

  requiresInternalLink:
    () =>
    ({ text }) => {
      if (/\]\(\/[^)]*\)/.test(text)) return null;
      if (text.split(/\s+/).length < 300) return null;
      return issue("no_internal_links", "No links to other pages on the site", "Link related pages by path so the piece sits inside the site rather than beside it.");
    },
};

const llmTells = rule.phrases("llm_tells", "Reads as machine-written", "These phrases are the tells readers have learned to skip. Say the specific thing instead.", LLM_TELLS);
const engagementBait = rule.phrases("engagement_bait", "Engagement bait", "Platforms down-rank it and readers resent it. Cut the ask; let the content earn the reply.", ENGAGEMENT_BAIT);
const marketing = rule.phrases("marketing_cadence", "Marketing cadence", "Advertising copy is spotted instantly on this channel. Plain and specific wins.", MARKETING);

export const CHANNEL_RULES = {
  linkedin: [
    rule.hardLimit(3000),
    rule.lengthBand(800, 1600, "Needing more is usually a sign the post is two posts."),
    rule.fold(210),
    rule.paragraphLength(500),
    rule.broetry(5, 12),
    rule.emojiMax(1),
    rule.emojiBullets(),
    rule.hashtagMax(3),
    rule.hashtagsAtEnd(),
    rule.linkWarning("LinkedIn suppresses reach on posts with external links. Put it in the first comment and say so."),
    rule.noMarkdown(),
    rule.opener("throat_clearing", "Opens with throat-clearing", "Open with the concrete sentence only someone who did the thing could write.", ["in today's", "in the world of", "as we all know", "we are excited", "i'm excited", "i am excited", "thrilled to"]),
    rule.weakClose(),
    engagementBait,
    llmTells,
  ],
  instagram: [
    rule.hardLimit(2200),
    rule.lengthBand(150, 400),
    rule.fold(125),
    rule.hashtagMax(5),
    rule.hashtagsAtEnd(),
    rule.noLinks('Links in a caption are not clickable. Say "link in bio" instead.'),
    rule.noMarkdown(),
    engagementBait,
    llmTells,
  ],
  twitter: [
    rule.hardLimit(280),
    rule.effectiveLimitWithLinks(250, 23),
    rule.hashtagMax(1),
    rule.noMarkdown(),
    rule.phrases("thread_bait", "Thread bait", "If it is a sequence, post the sequence. Announcing a thread is the bait.", THREAD_BAIT),
    rule.opener("announcement_opener", "Announcement opener", "Only when something was genuinely just shipped or announced. Otherwise lead with the thing itself.", ANNOUNCEMENT_OPENERS),
    rule.rhetoricalOpener(),
    engagementBait,
    llmTells,
  ],
  threads: [
    rule.hardLimit(500),
    rule.hashtagMax(0),
    rule.noMarkdown(),
    rule.opener("link_first", "Opens with a link", "Say the thing, then link.", ["http://", "https://"]),
    engagementBait,
    llmTells,
  ],
  bluesky: [
    rule.hardLimit(300, "graphemes"),
    rule.hashtagMax(0),
    rule.noMarkdown(),
    marketing,
    engagementBait,
    llmTells,
  ],
  facebook: [
    rule.lengthBand(80, 250, "A long post here is a blog entry in the wrong place."),
    rule.fold(200),
    rule.hashtagMax(2),
    rule.noMarkdown(),
    engagementBait,
    llmTells,
  ],
  tiktok: [
    rule.hardLimit(2200),
    rule.fold(50),
    rule.hashtagMax(4),
    rule.hashtagsAtEnd(),
    rule.noLinks("Links in a TikTok caption are not clickable."),
    marketing,
    llmTells,
  ],
  pinterest: [
    rule.hardLimit(500),
    rule.lengthBand(100, 200),
    rule.hashtagMax(0),
    rule.phrases("time_bound", "Time-bound copy", "Pins surface for years. Cut anything that expires.", TIME_BOUND),
    engagementBait,
  ],
  telegram: [
    rule.hardLimit(4096),
    rule.mediaLimit(1024),
    rule.paragraphLength(600),
    rule.emojiBullets(),
    marketing,
  ],
  google_business: [
    rule.hardLimit(1500),
    rule.lengthBand(150, 300, "Nobody reads a long one next to a listing."),
    rule.hashtagMax(0),
    rule.exclamations(0),
    rule.phoneOrUrl(),
    rule.needsDate(),
    rule.phrases("superlatives", "Marketing language", "Specific beats promotional: the fact, the hours, the change.", [...SUPERLATIVES, ...MARKETING]),
  ],
  website: [rule.requiresHeadings(), rule.requiresInternalLink()],
};

const LABELS = {
  linkedin: "LinkedIn",
  instagram: "Instagram",
  twitter: "X",
  threads: "Threads",
  bluesky: "Bluesky",
  facebook: "Facebook",
  tiktok: "TikTok",
  pinterest: "Pinterest",
  telegram: "Telegram",
  google_business: "Google Business",
  website: "the website",
};

export async function checkChannelRules(text, context = {}) {
  const body = String(text ?? "").replace(/\r\n/g, "\n").trim();
  const channel = context.channelKey ?? null;
  const rules = channel ? CHANNEL_RULES[channel] : null;
  if (!rules) return { summary: null, issues: [] };
  const input = { text: body, hasMedia: !!context.hasMedia, label: LABELS[channel] ?? channel };
  const issues = [];
  for (const check of rules) {
    const found = check(input);
    if (found) issues.push(found);
  }
  return { summary: { channel, rulesChecked: rules.length, flagged: issues.length }, issues };
}

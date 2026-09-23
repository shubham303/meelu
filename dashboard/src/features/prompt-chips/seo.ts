import type { PromptChip } from "./lib";

const WHAT_NOW: PromptChip = {
  label: "What should I do?",
  blurb:
    "The few page edits and merges Search Console already argues for. No vendor spend.",
  prompt: [
    "Strategy: highest return from what Search Console already shows. Do not collect vendor data on this run.",
    "Generate edits from every evidence kind and cannibalisation pairs, then screen, review and rank.",
    "A suggestion passes when the fix is one page's work and the impressions at stake are real for this site.",
    "For the review: keep the few with the most impressions at stake; reject anything that needs a new page unless the evidence is overwhelming.",
    "Adds that come back needing a search snapshot stay draft; list them for me by topic and stop.",
  ].join(" "),
};

const WITH_RESEARCH: PromptChip = {
  label: "What should I do, with keyword research",
  blurb: "The same, after growing the keyword table from the vendor once.",
  prompt: [
    "Strategy: highest return, with one round of keyword research first.",
    "Collect keywords once with the defaults, then generate edits from every evidence kind, cannibalisation pairs, and gap pages when confirmed competitors exist; screen, review and rank.",
    "A suggestion passes when the fix is one page's work or a clearly missing page with volume behind it.",
    "For the review: keep the few with the most impressions or volume at stake.",
  ].join(" "),
};

const COMPETITORS: PromptChip = {
  label: "Analyse competitors",
  blurb:
    "Find who ranks where we do not, and the pages that would close the gap.",
  prompt: [
    "Strategy: competitor gaps. Collect competitor candidates, then stop and wait for me to confirm them on the SEO screen or in chat.",
    "Once confirmed, collect their keywords, generate gap pages, collect search snapshots for the drafts, then screen, review and rank.",
    "A gap passes when two confirmed competitors rank top ten and no page of ours is within thirty.",
    "For the review: reject topics off this site's business, however much volume they carry.",
  ].join(" "),
};

const TOPIC: PromptChip = {
  label: "Content for a topic",
  blurb: "Name a topic; get the long-tail pages nobody here has written.",
  prompt: [
    "Strategy: content for a topic I will name. Grow ideas from the topic, group them, drop groups a page already owns, collect search snapshots for the drafts, then review and rank.",
    "A group passes when long-tail volume exists that no page of ours owns.",
    "For the review: one brief per group, with the working title and what it must cover.",
  ].join(" "),
};

const IMPROVE_PAGE: PromptChip = {
  label: "Improve this page",
  blurb:
    "Name a page; get one brief covering its queries, snippet and questions.",
  prompt: [
    "Strategy: improve one page I will name. Generate edits from every evidence kind narrowed to that page, collect search snapshots for its top queries, then review.",
    "Rows are per query; for the review, consolidate them into one brief for the page and mark the rest rejected.",
  ].join(" "),
};

const CTR: PromptChip = {
  label: "Impressions but no clicks",
  blurb: "Pages that rank and are skipped — titles and snippets first.",
  prompt: [
    "Strategy: click-through. Generate ctr edits only, then review.",
    "A row passes when the click gap is not explained by a featured snippet or AI overview on that results page.",
    "For the review: titles and meta descriptions first; say what the new title should promise.",
  ].join(" "),
};

const WHY_AHEAD: PromptChip = {
  label: "Why is a competitor ahead for a query?",
  blurb:
    "Name a query; compare our page with theirs and write the one change that follows.",
  prompt: [
    "Strategy: explain a ranking gap for a query I will name. Collect the search snapshot for it, then compare our page against the results above us with SQL: title and description terms we lack, features on the page, our coverage, age and inlinks.",
    "Write one suggestion yourself, add or edit, with the comparison as its evidence. It is not always the keywords; say what it is.",
  ].join(" "),
};

const CANNIBAL: PromptChip = {
  label: "Which pages cannibalise each other?",
  blurb: "Pages trading places on the same queries — merge or sharpen them.",
  prompt: [
    "Strategy: cannibalisation. Generate cannibalisation pairs, then review and rank.",
    "For the review: prefer merge over delete; approve the delete only when the weaker page adds no query the stronger lacks.",
  ].join(" "),
};

const PRUNE: PromptChip = {
  label: "What should I prune?",
  blurb: "The pages that only compete with your own.",
  prompt: [
    "Strategy: pruning. Generate cannibalisation pairs, review with a bias to merging, rank with a delete budget of five.",
    "Present only the delete side to me, each with where it redirects.",
  ].join(" "),
};

export function seo(): PromptChip[] {
  return [
    WHAT_NOW,
    WITH_RESEARCH,
    COMPETITORS,
    TOPIC,
    IMPROVE_PAGE,
    CTR,
    WHY_AHEAD,
    CANNIBAL,
    PRUNE,
  ];
}

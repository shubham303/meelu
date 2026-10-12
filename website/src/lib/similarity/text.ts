/**
 * Text handling for the similarity checker.
 *
 * Deliberately free of the DOM and of Node built-ins: the comparison itself
 * runs in the visitor's browser so pasted text never leaves their machine, and
 * the same functions have to work on the server when a URL is fetched instead.
 */

/**
 * A word character. Written as explicit ranges rather than \p{L} because the
 * build targets ES2017, where Unicode property escapes are not available.
 * Latin, Greek, Cyrillic, CJK and the Indic blocks are in; the general and CJK
 * punctuation blocks are deliberately left out.
 */
const WORD_CHAR =
  /[0-9a-z\u00df-\u024f\u0370-\u1fff\u2c00-\u2dff\u3040-\u9fff\ua000-\uabff\uac00-\ud7ff\uf900-\ufaff]/;

const APOSTROPHE = /['‘’ʼ]/;

const foldCache = new Map<string, string>();

/** Lowercases one character and drops its accents. Cached: text is repetitive. */
function foldChar(ch: string): string {
  const hit = foldCache.get(ch);
  if (hit !== undefined) return hit;
  const folded = ch
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  if (foldCache.size < 8192) foldCache.set(ch, folded);
  return folded;
}

export type Token = {
  /** Normalised form: lowercase, unaccented, no punctuation. */
  text: string;
  /** Offsets into the original string, so matches can be highlighted in place. */
  start: number;
  end: number;
};

/**
 * Splits text into normalised word tokens while keeping each token's position
 * in the original string. Apostrophes are swallowed rather than treated as
 * breaks, so "don't" is one token and not two.
 */
export function tokenise(source: string): Token[] {
  const tokens: Token[] = [];
  let buffer = "";
  let start = -1;

  const flush = (end: number) => {
    if (start >= 0 && buffer) tokens.push({ text: buffer, start, end });
    buffer = "";
    start = -1;
  };

  for (let i = 0; i < source.length; i++) {
    const ch = source[i];
    const folded = foldChar(ch);
    if (folded && WORD_CHAR.test(folded[0])) {
      if (start < 0) start = i;
      buffer += folded;
      continue;
    }
    if (start >= 0 && APOSTROPHE.test(ch)) continue;
    flush(i);
  }
  flush(source.length);
  return tokens;
}

export function normalise(source: string): string {
  return tokenise(source)
    .map((t) => t.text)
    .join(" ");
}

/**
 * Words carrying almost no signal about who wrote what. Two unrelated articles
 * share these heavily, which is exactly how a naive checker ends up telling you
 * a recipe and a tax guide are forty per cent the same.
 */
export const STOPWORDS = new Set([
  "a","about","above","after","again","against","all","am","an","and","any","are","aren't","as","at",
  "be","because","been","before","being","below","between","both","but","by",
  "can","cannot","could","couldn't","did","didn't","do","does","doesn't","doing","don't","down","during",
  "each","few","for","from","further","had","hadn't","has","hasn't","have","haven't","having","he","her",
  "here","hers","herself","him","himself","his","how","however","i","if","in","into","is","isn't","it",
  "its","itself","just","let","like","me","more","most","much","must","my","myself",
  "no","nor","not","now","of","off","on","once","only","or","other","ought","our","ours","ourselves","out",
  "over","own","same","shall","she","should","shouldn't","so","some","such","than","that","the","their",
  "theirs","them","themselves","then","there","these","they","this","those","through","to","too","under",
  "until","up","very","was","wasn't","we","were","weren't","what","when","where","which","while","who",
  "whom","why","will","with","won't","would","wouldn't","you","your","yours","yourself","yourselves",
  "dont","doesnt","didnt","isnt","arent","wasnt","werent","hasnt","havent","hadnt","wont","wouldnt",
  "couldnt","shouldnt","cant","its","thats","also","been","get","got","one","two",
]);

export function contentTokens(tokens: string[]): string[] {
  const kept = tokens.filter((t) => !STOPWORDS.has(t) && t.length > 1);
  return kept.length > 0 ? kept : tokens;
}

/**
 * Abbreviations whose full stop does not end a sentence. Kept short on purpose:
 * adding "no." here would merge every sentence that ends in the word no.
 */
const ABBREVIATIONS = new Set([
  "mr","mrs","ms","dr","prof","rev","hon","sr","jr","st","mt","vs","etc","eg","ie","al","fig","figs",
  "vol","vols","pp","ed","eds","inc","ltd","llc","plc","corp","dept","univ","approx","cf","viz",
  "incl","excl","esp","ext","est","ca","pt","pts","ch","chap","sec","para","ref","refs",
  "jan","feb","mar","apr","jun","jul","aug","sep","sept","oct","nov","dec",
  "mon","tue","tues","wed","thu","thurs","fri","sat","sun",
]);

const TERMINATORS = new Set([".", "!", "?", "…", "。", "！", "？"]);
const CLOSERS = new Set(['"', "'", ")", "]", "}", "’", "”", "»"]);

/** The word immediately before position `i`, folded. */
function wordBefore(source: string, i: number): string {
  let s = i;
  while (s > 0) {
    const folded = foldChar(source[s - 1]);
    if (folded && WORD_CHAR.test(folded[0])) s -= 1;
    else break;
  }
  return normalise(source.slice(s, i));
}

function looksLikeStart(ch: string): boolean {
  if (/[0-9"'“‘(\[«—]/.test(ch)) return true;
  const upper = ch.toUpperCase();
  const lower = ch.toLowerCase();
  if (upper !== lower) return ch === upper;
  // Scripts without letter case: any word character starts a sentence.
  return WORD_CHAR.test(ch) && ch.charCodeAt(0) > 0x0370;
}

export type Segment = { text: string; start: number; end: number };

/**
 * Sentence segmentation that survives the two things that break naive splitters:
 * abbreviations ("Dr. Smith", "e.g. this") and decimals ("a 3.5% lift"). A line
 * break always ends a sentence, which suits extracted page text where every
 * block already arrives on its own line.
 */
export function splitSentences(source: string): Segment[] {
  const out: Segment[] = [];
  let start = 0;

  const push = (end: number) => {
    let s = start;
    let e = Math.min(end, source.length);
    while (s < e && /\s/.test(source[s])) s += 1;
    while (e > s && /\s/.test(source[e - 1])) e -= 1;
    if (e > s) out.push({ text: source.slice(s, e), start: s, end: e });
    start = Math.min(end, source.length);
  };

  for (let i = 0; i < source.length; i++) {
    const ch = source[i];
    if (ch === "\n") {
      push(i + 1);
      continue;
    }
    if (!TERMINATORS.has(ch)) continue;

    let j = i;
    while (j + 1 < source.length && TERMINATORS.has(source[j + 1])) j += 1;
    while (j + 1 < source.length && CLOSERS.has(source[j + 1])) j += 1;

    const next = source[j + 1];
    if (next === undefined) {
      push(source.length);
      break;
    }
    if (!/\s/.test(next)) {
      i = j;
      continue;
    }
    if (ch === ".") {
      // 3.5 or 1.000.000
      if (i > 0 && /[0-9]/.test(source[i - 1]) && /^\s*[0-9]/.test(source.slice(j + 1))) {
        i = j;
        continue;
      }
      const previous = wordBefore(source, i);
      if (previous.length === 1 || ABBREVIATIONS.has(previous)) {
        i = j;
        continue;
      }
    }
    const rest = source.slice(j + 1).match(/^\s+(\S)/);
    if (!rest) {
      push(source.length);
      break;
    }
    if (!looksLikeStart(rest[1])) {
      i = j;
      continue;
    }
    push(j + 1);
    i = j;
  }

  push(source.length);
  return out;
}

/**
 * A segment longer than this is not a sentence — it is a wall of text somebody
 * pasted without punctuation. Comparing two of those as single units compares
 * vocabulary rather than wording, which reads as a false match, so they get cut
 * into windows instead.
 */
const MAX_SEGMENT_WORDS = 60;
const TARGET_SEGMENT_WORDS = 40;
const CLAUSE_BREAK = /[,;:\u2013\u2014)\]]/;

function windowsOf(source: string, segment: Segment): Segment[] {
  const tokens = tokenise(segment.text);
  if (tokens.length <= MAX_SEGMENT_WORDS) return [segment];

  const out: Segment[] = [];
  let from = 0;
  for (let i = 0; i < tokens.length; i++) {
    const taken = i - from + 1;
    const after = segment.text.slice(tokens[i].end, tokens[i].end + 2);
    const breakable = taken >= TARGET_SEGMENT_WORDS && CLAUSE_BREAK.test(after);
    if (!breakable && taken < MAX_SEGMENT_WORDS && i < tokens.length - 1) continue;
    const start = segment.start + tokens[from].start;
    const end = segment.start + tokens[i].end;
    out.push({ text: source.slice(start, end), start, end });
    from = i + 1;
  }
  return out;
}

/**
 * Sentences, with over-long ones cut into comparable windows. This is the unit
 * everything downstream matches on.
 */
export function segments(source: string): Segment[] {
  return splitSentences(source).flatMap((segment) => windowsOf(source, segment));
}

/** FNV-1a. Shingle sets are large enough that storing numbers beats storing strings. */
export function hash(value: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < value.length; i++) {
    h ^= value.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Every window of `k` consecutive words — the classic w-shingle. */
export function shingles(tokens: string[], k: number): Set<number> {
  const out = new Set<number>();
  if (tokens.length < k) return out;
  for (let i = 0; i + k <= tokens.length; i++) {
    out.add(hash(tokens.slice(i, i + k).join(" ")));
  }
  return out;
}

export function intersectionSize(a: Set<number>, b: Set<number>): number {
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  let n = 0;
  for (const value of small) if (large.has(value)) n += 1;
  return n;
}

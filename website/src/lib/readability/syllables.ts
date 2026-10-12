/**
 * Syllable counting.
 *
 * There is no exact algorithm for this short of a pronunciation dictionary, so
 * this is a heuristic: count vowel groups, then correct for the endings English
 * spells but does not say. It is deliberately conservative — every rule below
 * was added because it fixes more common words than it breaks. Words the rules
 * get wrong for well-known reasons live in EXCEPTIONS.
 */

const VOWELS = "aeiouy";

/** Words the vowel-group method gets wrong and that turn up often enough to matter. */
const EXCEPTIONS: Record<string, number> = {
  // "-ing" after a vowel that the group rule swallows
  being: 2,
  doing: 2,
  going: 2,
  // silent-e rules that misfire
  whole: 1,
  wholly: 2,
  isle: 1,
  aisle: 1,
  queue: 1,
  queued: 1,
  eye: 1,
  eyes: 1,
  // "-ed" that is still spoken as its own syllable
  sacred: 2,
  wicked: 2,
  naked: 2,
  ragged: 2,
  rugged: 2,
  jagged: 2,
  crooked: 2,
  wretched: 2,
  beloved: 3,
  // vowel pairs pronounced apart
  science: 2,
  sciences: 3,
  scientist: 3,
  quiet: 2,
  quietly: 3,
  poem: 2,
  poems: 2,
  poet: 2,
  ocean: 2,
  oceans: 2,
  area: 3,
  areas: 3,
  idea: 3,
  ideas: 3,
  create: 2,
  creates: 2,
  created: 3,
  creating: 3,
  creative: 3,
  reality: 4,
  // vowel pairs pronounced together
  business: 2,
  businesses: 3,
  wednesday: 2,
  colonel: 2,
  // very common and worth pinning
  the: 1,
  people: 2,
  something: 2,
  anything: 3,
  everything: 3,
};

interface VowelGroup {
  start: number;
  text: string;
}

/** Runs of adjacent vowels. "readable" -> ["ea", "a", "e"]. */
export function vowelGroups(word: string): VowelGroup[] {
  const out: VowelGroup[] = [];
  let i = 0;
  while (i < word.length) {
    if (VOWELS.includes(word[i])) {
      const start = i;
      let end = i;
      while (end < word.length && VOWELS.includes(word[end])) end += 1;
      out.push({ start, text: word.slice(start, end) });
      i = end;
    } else {
      i += 1;
    }
  }
  return out;
}

function isConsonant(ch: string | undefined): boolean {
  return ch !== undefined && ch >= "a" && ch <= "z" && !VOWELS.includes(ch);
}

/** "table", "little", "castle" — the final e is spoken. "whale", "while" — it is not. */
function isConsonantLe(word: string): boolean {
  if (word.length < 3 || !word.endsWith("le")) return false;
  const before = word[word.length - 3];
  return isConsonant(before) && before !== "l";
}

/** After these, "-es" is a spoken syllable: boxes, pages, faces, watches, houses. */
function sibilantBefore(word: string, eIndex: number): boolean {
  const before = word[eIndex - 1];
  return before === "s" || before === "x" || before === "z" || before === "c" || before === "g" || before === "h";
}

/** Strip anything that is not an English letter and fold the word to lower case. */
export function normaliseWord(raw: string): string {
  return raw.toLowerCase().replace(/[^a-z]/g, "");
}

/**
 * Syllables in a single word. Returns 0 for a token with no letters in it,
 * so "2024" costs nothing, and at least 1 for anything else.
 */
export function countSyllables(raw: string): number {
  const word = normaliseWord(raw);
  if (word.length === 0) return 0;

  const known = EXCEPTIONS[word];
  if (known !== undefined) return known;
  if (word.length <= 2) return 1;

  const groups = vowelGroups(word);
  if (groups.length === 0) return 1;

  let count = groups.length;
  const last = groups[groups.length - 1];
  const len = word.length;

  if (word.endsWith("e") && last.text === "e" && last.start === len - 1) {
    // Silent final e: "make", "large". Not silent after a consonant + l.
    if (!isConsonantLe(word)) count -= 1;
  } else if (word.endsWith("es") && last.text === "e" && last.start === len - 2) {
    // "makes" loses the e, "boxes" and "candles" keep it.
    if (!isConsonantLe(word.slice(0, -1)) && !sibilantBefore(word, len - 2)) count -= 1;
  } else if (word.endsWith("ed") && last.text === "e" && last.start === len - 2) {
    // "-ed" is only its own syllable after t or d: "wanted", "needed".
    const before = word[len - 3];
    if (before !== "t" && before !== "d") count -= 1;
  }

  // Word-final "-ia" / "-io" is two syllables unless the consonant in front
  // palatalises it: media, radio, portfolio — but not ratio, social.
  if (len > 3 && (word.endsWith("ia") || word.endsWith("io"))) {
    const before = word[len - 3];
    if (!"ctsxg".includes(before)) count += 1;
  }

  // "-ual" splits: actual, usual, annually. Not after q: equal, equally.
  const ual = word.indexOf("ual");
  if (ual > 0 && word[ual - 1] !== "q") count += 1;

  // "-ing" straight after a vowel: doing, trying, agreeing.
  if (len > 4 && word.endsWith("ing")) {
    const before = word[len - 4];
    if (VOWELS.includes(before)) count += 1;
  }

  return Math.max(1, count);
}

/**
 * Gunning Fog counts "complex" words as three syllables or more, minus three
 * exclusions the original method is explicit about: proper nouns, hyphenated
 * compounds, and verbs that only reach three syllables because of an -es, -ed
 * or -ing ending.
 */
export function isComplexWord(raw: string, syllables: number, isSentenceStart: boolean): boolean {
  if (syllables < 3) return false;
  if (raw.includes("-")) return false;
  if (!isSentenceStart && /^[A-Z]/.test(raw)) return false;

  const word = normaliseWord(raw);
  for (const suffix of ["ing", "ed", "es"]) {
    if (word.endsWith(suffix) && word.length > suffix.length + 2) {
      if (countSyllables(word.slice(0, -suffix.length)) < 3) return false;
    }
  }
  return true;
}

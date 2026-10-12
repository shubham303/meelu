/**
 * The six formulas, written out exactly as published. Nothing here is rounded,
 * weighted or "tuned" — the display layer rounds, these return the raw number.
 */

export interface Ingredients {
  words: number;
  sentences: number;
  syllables: number;
  /** Letters and digits, no spaces or punctuation. */
  letters: number;
  /** Three syllables or more, after the Gunning Fog exclusions. */
  complexWords: number;
  /** Three syllables or more, no exclusions. */
  polysyllables: number;
}

/** Flesch Reading Ease: 206.835 − 1.015 × (words / sentences) − 84.6 × (syllables / words) */
export function fleschReadingEase({ words, sentences, syllables }: Ingredients): number {
  if (words === 0 || sentences === 0) return 0;
  return 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words);
}

/** Flesch-Kincaid Grade: 0.39 × (words / sentences) + 11.8 × (syllables / words) − 15.59 */
export function fleschKincaidGrade({ words, sentences, syllables }: Ingredients): number {
  if (words === 0 || sentences === 0) return 0;
  return 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59;
}

/** ARI: 4.71 × (characters / words) + 0.5 × (words / sentences) − 21.43 */
export function automatedReadabilityIndex({ words, sentences, letters }: Ingredients): number {
  if (words === 0 || sentences === 0) return 0;
  return 4.71 * (letters / words) + 0.5 * (words / sentences) - 21.43;
}

/** Gunning Fog: 0.4 × [(words / sentences) + 100 × (complex words / words)] */
export function gunningFog({ words, sentences, complexWords }: Ingredients): number {
  if (words === 0 || sentences === 0) return 0;
  return 0.4 * (words / sentences + 100 * (complexWords / words));
}

/** SMOG: 1.0430 × √(polysyllables × (30 / sentences)) + 3.1291 */
export function smogIndex({ sentences, polysyllables }: Ingredients): number {
  if (sentences === 0) return 0;
  return 1.043 * Math.sqrt(polysyllables * (30 / sentences)) + 3.1291;
}

/** Coleman-Liau: 0.0588 × L − 0.296 × S − 15.8, L and S per 100 words */
export function colemanLiau({ words, sentences, letters }: Ingredients): number {
  if (words === 0) return 0;
  const l = (letters / words) * 100;
  const s = (sentences / words) * 100;
  return 0.0588 * l - 0.296 * s - 15.8;
}

export type Tone = "good" | "warn" | "bad";

export interface FleschBand {
  min: number;
  label: string;
  school: string;
  tone: Tone;
  audience: string;
}

/** Flesch's own bands, unchanged since 1948. */
export const FLESCH_BANDS: FleschBand[] = [
  {
    min: 90,
    label: "Very easy",
    school: "5th grade",
    tone: "good",
    audience: "An average 11-year-old follows this without effort.",
  },
  {
    min: 80,
    label: "Easy",
    school: "6th grade",
    tone: "good",
    audience: "Conversational. This is roughly where consumer email and ad copy sit.",
  },
  {
    min: 70,
    label: "Fairly easy",
    school: "7th grade",
    tone: "good",
    audience: "Comfortable for almost everyone. Popular fiction lives here.",
  },
  {
    min: 60,
    label: "Plain English",
    school: "8th to 9th grade",
    tone: "good",
    audience: "Most US adults read comfortably here. It is the target for web writing.",
  },
  {
    min: 50,
    label: "Fairly difficult",
    school: "10th to 12th grade",
    tone: "warn",
    audience: "Fine for a trade audience, heavy going for a general one.",
  },
  {
    min: 30,
    label: "Difficult",
    school: "College",
    tone: "warn",
    audience: "Readers will re-read sentences. Acceptable for technical documentation.",
  },
  {
    min: 10,
    label: "Very difficult",
    school: "College graduate",
    tone: "bad",
    audience: "Academic register. Most readers give up rather than decode it.",
  },
  {
    min: Number.NEGATIVE_INFINITY,
    label: "Extremely difficult",
    school: "Professional",
    tone: "bad",
    audience: "Legal and scientific writing. Read by people who are paid to.",
  },
];

export function fleschBand(score: number): FleschBand {
  return FLESCH_BANDS.find((band) => score >= band.min) ?? FLESCH_BANDS[FLESCH_BANDS.length - 1];
}

/** What a US grade number means for the people you are writing for. */
export function gradeAudience(grade: number): string {
  const years = Math.round(grade);
  if (years <= 4) return "4th grade or below. Simple enough for anyone, including a child.";
  if (years === 5) return "5th grade. Very easy. Plain-language public information sits here.";
  if (years === 6) return "6th grade. Easy. The level most newspapers aim for.";
  if (years === 7) return "7th grade. Easy for a general audience.";
  if (years === 8) return "8th grade. Most US adults read comfortably here.";
  if (years === 9) return "9th grade. Still comfortable, slightly formal.";
  if (years === 10) return "10th grade. Fine for a trade or B2B audience.";
  if (years === 11 || years === 12) return "11th to 12th grade. Demanding for a general reader.";
  if (years <= 16) return "College. Expect readers to skim rather than read.";
  return "Postgraduate. Almost nobody reads this voluntarily.";
}

/** The label people mean when they say "grade level". */
export function gradeLabel(grade: number): string {
  const years = Math.max(1, Math.round(grade));
  if (years >= 17) return "Postgraduate";
  if (years >= 13) return `College, year ${years - 12}`;
  const suffix = years === 1 ? "st" : years === 2 ? "nd" : years === 3 ? "rd" : "th";
  return `${years}${suffix} grade`;
}

export function gradeTone(grade: number): Tone {
  if (grade <= 9) return "good";
  if (grade <= 12) return "warn";
  return "bad";
}

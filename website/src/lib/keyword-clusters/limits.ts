export const CLUSTER_LIMITS = {
  maxSeeds: 5,
  suggestionsPerSeed: 150,
  maxKeywords: 200,
  maxSplitGroups: 60,
  maxSerpCalls: 20,
  maxSeedChars: 80,
  defaultMinVolume: 20,
  dailyRuns: 100,
};

export const SERP_SAME = 4;
export const SERP_DIFFERENT = 1;

export type LocationOption = { code: number; name: string; language: string };

export const LOCATIONS: LocationOption[] = [
  { code: 2840, name: "United States", language: "en" },
  { code: 2826, name: "United Kingdom", language: "en" },
  { code: 2124, name: "Canada", language: "en" },
  { code: 2036, name: "Australia", language: "en" },
  { code: 2356, name: "India", language: "en" },
  { code: 2554, name: "New Zealand", language: "en" },
  { code: 2372, name: "Ireland", language: "en" },
  { code: 2276, name: "Germany", language: "de" },
  { code: 2250, name: "France", language: "fr" },
  { code: 2724, name: "Spain", language: "es" },
  { code: 2380, name: "Italy", language: "it" },
  { code: 2528, name: "Netherlands", language: "nl" },
  { code: 2076, name: "Brazil", language: "pt" },
  { code: 2484, name: "Mexico", language: "es" },
];

export const LANGUAGES: Array<{ code: string; name: string }> = [
  { code: "en", name: "English" },
  { code: "de", name: "German" },
  { code: "fr", name: "French" },
  { code: "es", name: "Spanish" },
  { code: "it", name: "Italian" },
  { code: "nl", name: "Dutch" },
  { code: "pt", name: "Portuguese" },
];

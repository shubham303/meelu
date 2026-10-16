const COUNTRY_NAMES = new Intl.DisplayNames(["en"], { type: "region" });

export function countryName(code: string | null | undefined): string {
  return code ? (COUNTRY_NAMES.of(code) ?? code) : "Unknown market";
}

export function marketLabel(
  markets: string[] | undefined,
  language: string | null | undefined,
): string {
  if (!markets?.length) {
    return language && language !== "en"
      ? "Market not set"
      : "English-speaking, worldwide";
  }
  return markets.map(countryName).join(", ");
}

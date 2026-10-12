/**
 * Works out whether a box holds a URL to fetch or text to compare, so the
 * visitor does not have to tell us. Deliberately stricter than the audit tool's
 * parser: "Ltd. Sales fell 3.4%" contains dots too, and guessing wrong there
 * would send a sentence off to be fetched.
 */
const URL_SHAPE =
  /^(https?:\/\/)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+(:\d{2,5})?([/?#]\S*)?$/i;

export type Input =
  | { kind: "url"; url: string }
  | { kind: "text"; text: string }
  | { kind: "empty" };

export function detect(raw: string): Input {
  const trimmed = raw.trim();
  if (!trimmed) return { kind: "empty" };
  if (
    trimmed.length <= 2000 &&
    !/\s/.test(trimmed) &&
    URL_SHAPE.test(trimmed) &&
    /\.[a-z]{2,24}(:\d+)?([/?#]|$)/i.test(trimmed)
  ) {
    return {
      kind: "url",
      url: /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`,
    };
  }
  return { kind: "text", text: raw };
}

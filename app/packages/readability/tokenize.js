const MASK = "\u0001";
export const ABBREVIATIONS = [
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "mt", "rev", "hon", "gen",
    "col", "capt", "lt", "sgt", "messrs", "fig", "figs", "vs", "etc", "al", "inc",
    "ltd", "co", "corp", "dept", "est", "vol", "pp", "approx", "cf", "eg", "ie",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sept", "sep", "oct", "nov",
    "dec", "mon", "tue", "tues", "wed", "thur", "thurs", "thu", "fri", "sat", "sun",
];
const ABBREVIATION_RE = new RegExp(`\\b(?:${ABBREVIATIONS.join("|")})\\.`, "gi");
const WORD_RE = /[A-Za-z0-9À-ɏ]+(?:['’-][A-Za-z0-9À-ɏ]+)*/g;
const LETTER_RE = /[A-Za-z0-9À-ɏ]/g;
const CLOSERS = "\"')]}”’»";
const TERMINATORS = ".!?";
function maskDots(text) {
    return (text
        .replace(/(\d)\.(\d)/g, `$1${MASK}$2`)
        .replace(/\b(?:[A-Za-z]\.){2,}/g, (m) => m.replace(/\./g, MASK))
        .replace(ABBREVIATION_RE, (m) => m.replace(/\./g, MASK))
        .replace(/\b([A-Z])\.(?=\s)/g, `$1${MASK}`)
        .replace(/\.{2,}/g, (m) => MASK.repeat(m.length)));
}
function unmask(text) {
    return text.split(MASK).join(".");
}
export function splitParagraphs(text) {
    return text
        .split(/\r?\n+/)
        .map((line) => line.trim())
        .filter((line) => line.length > 0);
}
export function splitSentences(paragraph) {
    const masked = maskDots(paragraph);
    const out = [];
    let start = 0;
    let i = 0;
    while (i < masked.length) {
        if (!TERMINATORS.includes(masked[i])) {
            i += 1;
            continue;
        }
        let end = i + 1;
        while (end < masked.length && TERMINATORS.includes(masked[end]))
            end += 1;
        while (end < masked.length && CLOSERS.includes(masked[end]))
            end += 1;
        if (end >= masked.length || /\s/.test(masked[end])) {
            const piece = masked.slice(start, end).trim();
            if (piece.length > 0)
                out.push(unmask(piece));
            start = end;
        }
        i = end;
    }
    const tail = masked.slice(start).trim();
    if (tail.length > 0)
        out.push(unmask(tail));
    return out;
}
export function splitWords(text) {
    return text.match(WORD_RE) ?? [];
}
export function countLetters(text) {
    return (text.match(LETTER_RE) ?? []).length;
}

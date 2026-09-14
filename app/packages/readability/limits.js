export const FREE_WORD_LIMIT = 5_000;
const WORD = /\S+/g;
export function limitWords(text, max = FREE_WORD_LIMIT) {
    WORD.lastIndex = 0;
    let seen = 0;
    let cut = -1;
    let match;
    while ((match = WORD.exec(text)) !== null) {
        seen += 1;
        if (seen === max) {
            cut = match.index + match[0].length;
            break;
        }
    }
    if (cut < 0 || text.slice(cut).trim().length === 0) {
        return { text, truncated: false };
    }
    return { text: text.slice(0, cut), truncated: true };
}
export function countWords(text) {
    return text.split(/\s+/).filter(Boolean).length;
}

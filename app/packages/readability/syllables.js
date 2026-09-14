const VOWELS = "aeiouy";
const EXCEPTIONS = {
    being: 2,
    doing: 2,
    going: 2,
    whole: 1,
    wholly: 2,
    isle: 1,
    aisle: 1,
    queue: 1,
    queued: 1,
    eye: 1,
    eyes: 1,
    sacred: 2,
    wicked: 2,
    naked: 2,
    ragged: 2,
    rugged: 2,
    jagged: 2,
    crooked: 2,
    wretched: 2,
    beloved: 3,
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
    business: 2,
    businesses: 3,
    wednesday: 2,
    colonel: 2,
    the: 1,
    people: 2,
    something: 2,
    anything: 3,
    everything: 3,
};
export function vowelGroups(word) {
    const out = [];
    let i = 0;
    while (i < word.length) {
        if (VOWELS.includes(word[i])) {
            const start = i;
            let end = i;
            while (end < word.length && VOWELS.includes(word[end]))
                end += 1;
            out.push({ start, text: word.slice(start, end) });
            i = end;
        }
        else {
            i += 1;
        }
    }
    return out;
}
function isConsonant(ch) {
    return ch !== undefined && ch >= "a" && ch <= "z" && !VOWELS.includes(ch);
}
function isConsonantLe(word) {
    if (word.length < 3 || !word.endsWith("le"))
        return false;
    const before = word[word.length - 3];
    return isConsonant(before) && before !== "l";
}
function sibilantBefore(word, eIndex) {
    const before = word[eIndex - 1];
    return before === "s" || before === "x" || before === "z" || before === "c" || before === "g" || before === "h";
}
export function normaliseWord(raw) {
    return raw.toLowerCase().replace(/[^a-z]/g, "");
}
export function countSyllables(raw) {
    const word = normaliseWord(raw);
    if (word.length === 0)
        return 0;
    const known = EXCEPTIONS[word];
    if (known !== undefined)
        return known;
    if (word.length <= 2)
        return 1;
    const groups = vowelGroups(word);
    if (groups.length === 0)
        return 1;
    let count = groups.length;
    const last = groups[groups.length - 1];
    const len = word.length;
    if (word.endsWith("e") && last.text === "e" && last.start === len - 1) {
        if (!isConsonantLe(word))
            count -= 1;
    }
    else if (word.endsWith("es") && last.text === "e" && last.start === len - 2) {
        if (!isConsonantLe(word.slice(0, -1)) && !sibilantBefore(word, len - 2))
            count -= 1;
    }
    else if (word.endsWith("ed") && last.text === "e" && last.start === len - 2) {
        const before = word[len - 3];
        if (before !== "t" && before !== "d")
            count -= 1;
    }
    if (len > 3 && (word.endsWith("ia") || word.endsWith("io"))) {
        const before = word[len - 3];
        if (!"ctsxg".includes(before))
            count += 1;
    }
    const ual = word.indexOf("ual");
    if (ual > 0 && word[ual - 1] !== "q")
        count += 1;
    if (len > 4 && word.endsWith("ing")) {
        const before = word[len - 4];
        if (VOWELS.includes(before))
            count += 1;
    }
    return Math.max(1, count);
}
export function isComplexWord(raw, syllables, isSentenceStart) {
    if (syllables < 3)
        return false;
    if (raw.includes("-"))
        return false;
    if (!isSentenceStart && /^[A-Z]/.test(raw))
        return false;
    const word = normaliseWord(raw);
    for (const suffix of ["ing", "ed", "es"]) {
        if (word.endsWith(suffix) && word.length > suffix.length + 2) {
            if (countSyllables(word.slice(0, -suffix.length)) < 3)
                return false;
        }
    }
    return true;
}

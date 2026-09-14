import { FREE_WORD_LIMIT, limitWords } from "./limits.js";
import { countLetters, splitParagraphs, splitSentences, splitWords } from "./tokenize.js";
import { countSyllables, isComplexWord, normaliseWord } from "./syllables.js";
import { automatedReadabilityIndex, colemanLiau, fleschBand, fleschKincaidGrade, fleschReadingEase, gradeAudience, gradeLabel, gradeTone, gunningFog, smogIndex, } from "./scores.js";
export const MAX_WORDS = FREE_WORD_LIMIT;
export const LONG_SENTENCE = 25;
export const VERY_LONG_SENTENCE = 35;
export const WORDS_PER_MINUTE = 238;
export const RELIABLE_WORD_COUNT = 100;
const BE_VERBS = new Set([
    "am", "is", "are", "was", "were", "be", "been", "being", "isn't", "aren't",
    "wasn't", "weren't", "isnt", "arent", "wasnt", "werent",
]);
const PASSIVE_INTERRUPTERS = new Set([
    "not", "never", "always", "already", "also", "still", "just", "only", "then",
    "now", "often", "usually", "generally", "typically", "currently", "recently",
    "widely", "largely", "mostly", "rarely", "seldom", "simply", "even", "being",
    "well", "better", "further", "quickly", "slowly", "carefully", "properly",
]);
const IRREGULAR_PARTICIPLES = new Set([
    "beaten", "become", "begun", "bent", "bitten", "blown", "born", "borne",
    "bought", "bound", "broken", "brought", "built", "burnt", "caught", "chosen",
    "come", "cost", "cut", "dealt", "done", "drawn", "driven", "drunk", "eaten",
    "fallen", "fed", "felt", "fought", "found", "forgotten", "frozen", "given",
    "gone", "got", "gotten", "grown", "heard", "held", "hidden", "hit", "hurt",
    "kept", "known", "laid", "led", "leant", "leapt", "learnt", "left", "lent",
    "let", "lost", "made", "meant", "met", "overcome", "paid", "put", "read",
    "rebuilt", "regrown", "retold", "rewritten", "ridden", "risen", "run", "said",
    "seen", "sent", "set", "sewn", "shaken", "shot", "shown", "shut", "slept",
    "sold", "sought", "spent", "split", "spoken", "spread", "stolen", "stood",
    "struck", "sung", "sunk", "sworn", "taken", "taught", "thrown", "told",
    "torn", "understood", "undertaken", "upheld", "withdrawn", "woken", "won",
    "worn", "written",
]);
const NOT_ADVERBS = new Set([
    "only", "family", "reply", "supply", "apply", "imply", "comply", "multiply",
    "july", "italy", "ally", "rally", "bully", "belly", "jelly", "folly", "holly",
    "dolly", "melancholy", "anomaly", "assembly", "monopoly", "panoply", "ugly",
    "holy", "silly", "lonely", "lovely", "friendly", "likely", "deadly", "costly",
    "timely", "orderly", "elderly", "cuddly", "wobbly", "bubbly", "giggly",
    "wrinkly", "burly", "curly", "surly", "gnarly", "measly", "grisly", "ghastly",
    "unruly", "manly", "womanly", "godly", "worldly", "homely", "stately",
    "portly", "chilly", "hilly", "smelly", "shelly", "duly", "truly",
]);
function round(value, places = 1) {
    const factor = 10 ** places;
    return Math.round(value * factor) / factor;
}
function looksLikeParticiple(lower) {
    if (IRREGULAR_PARTICIPLES.has(lower))
        return true;
    return lower.length > 3 && lower.endsWith("ed");
}
function findPassive(words) {
    const hits = [];
    const lower = words.map((w) => normaliseWord(w));
    for (let i = 0; i < words.length; i += 1) {
        if (!BE_VERBS.has(lower[i]) && !BE_VERBS.has(words[i].toLowerCase()))
            continue;
        for (let step = 1; step <= 3 && i + step < words.length; step += 1) {
            const candidate = lower[i + step];
            if (looksLikeParticiple(candidate)) {
                hits.push(words.slice(i, i + step + 1).join(" "));
                i += step;
                break;
            }
            if (!PASSIVE_INTERRUPTERS.has(candidate))
                break;
        }
    }
    return hits;
}
function isAdverb(raw) {
    const word = normaliseWord(raw);
    return word.length > 4 && word.endsWith("ly") && !NOT_ADVERBS.has(word);
}
function readingTimeLabel(seconds) {
    if (seconds < 60)
        return `${Math.max(1, Math.round(seconds))} sec`;
    const minutes = Math.round(seconds / 60);
    return `${minutes} min`;
}
function emptyReport() {
    const ingredients = {
        words: 0,
        sentences: 0,
        syllables: 0,
        letters: 0,
        complexWords: 0,
        polysyllables: 0,
    };
    return {
        empty: true,
        reliable: false,
        counts: {
            characters: 0,
            charactersNoSpaces: 0,
            letters: 0,
            words: 0,
            sentences: 0,
            paragraphs: 0,
            syllables: 0,
            complexWords: 0,
            polysyllables: 0,
            monosyllables: 0,
            longSentences: 0,
            passiveSentences: 0,
            adverbs: 0,
        },
        averages: {
            wordsPerSentence: 0,
            syllablesPerWord: 0,
            lettersPerWord: 0,
            sentencesPerParagraph: 0,
            wordsPerParagraph: 0,
        },
        ingredients,
        scores: [],
        flesch: 0,
        fleschDisplay: "0",
        band: fleschBand(0),
        grade: 0,
        gradeLabel: gradeLabel(0),
        gradeAudience: gradeAudience(0),
        gradeTone: "good",
        consensusGrade: 0,
        readingSeconds: 0,
        readingTime: "0 sec",
        sentences: [],
        paragraphs: [],
        complexList: [],
        adverbList: [],
        passiveList: [],
        longList: [],
        recommendations: [],
    };
}
export function analyse(input, maxWords = MAX_WORDS) {
    const text = limitWords(input, maxWords).text;
    const paragraphs = splitParagraphs(text);
    if (paragraphs.length === 0)
        return emptyReport();
    const sentences = [];
    const complexTally = new Map();
    const adverbList = [];
    const passiveList = [];
    let totalWords = 0;
    let totalSyllables = 0;
    let totalLetters = 0;
    let totalComplex = 0;
    let totalPolysyllables = 0;
    let totalMonosyllables = 0;
    paragraphs.forEach((paragraph, paragraphIndex) => {
        for (const raw of splitSentences(paragraph)) {
            const words = splitWords(raw);
            if (words.length === 0)
                continue;
            let syllables = 0;
            const complexWords = [];
            const adverbs = [];
            words.forEach((word, wordIndex) => {
                const count = countSyllables(word);
                syllables += count;
                if (count === 1)
                    totalMonosyllables += 1;
                if (count >= 3)
                    totalPolysyllables += 1;
                if (isComplexWord(word, count, wordIndex === 0)) {
                    complexWords.push(word);
                    const key = word.toLowerCase();
                    const seen = complexTally.get(key);
                    if (seen)
                        seen.count += 1;
                    else
                        complexTally.set(key, { syllables: count, count: 1 });
                }
                if (isAdverb(word)) {
                    adverbs.push(word);
                    adverbList.push({ word, sentence: sentences.length });
                }
            });
            const passive = findPassive(words);
            for (const phrase of passive) {
                passiveList.push({ phrase, sentence: sentences.length });
            }
            const letters = countLetters(raw);
            const flags = [];
            if (words.length >= VERY_LONG_SENTENCE)
                flags.push("very-long");
            else if (words.length >= LONG_SENTENCE)
                flags.push("long");
            if (complexWords.length >= 3)
                flags.push("complex");
            if (passive.length > 0)
                flags.push("passive");
            sentences.push({
                index: sentences.length,
                paragraph: paragraphIndex,
                text: raw,
                words: words.length,
                syllables,
                letters,
                grade: fleschKincaidGrade({
                    words: words.length,
                    sentences: 1,
                    syllables,
                    letters,
                    complexWords: complexWords.length,
                    polysyllables: complexWords.length,
                }),
                complexWords,
                adverbs,
                passive,
                flags,
            });
            totalWords += words.length;
            totalSyllables += syllables;
            totalLetters += letters;
            totalComplex += complexWords.length;
        }
    });
    if (sentences.length === 0 || totalWords === 0)
        return emptyReport();
    const ingredients = {
        words: totalWords,
        sentences: sentences.length,
        syllables: totalSyllables,
        letters: totalLetters,
        complexWords: totalComplex,
        polysyllables: totalPolysyllables,
    };
    const wordsPerSentence = totalWords / sentences.length;
    const syllablesPerWord = totalSyllables / totalWords;
    const lettersPerWord = totalLetters / totalWords;
    const flesch = fleschReadingEase(ingredients);
    const fk = fleschKincaidGrade(ingredients);
    const ari = automatedReadabilityIndex(ingredients);
    const fog = gunningFog(ingredients);
    const smog = smogIndex(ingredients);
    const cl = colemanLiau(ingredients);
    const scores = [
        {
            id: "flesch",
            name: "Flesch Reading Ease",
            value: flesch,
            display: round(flesch).toFixed(1),
            unit: "score",
            formula: "206.835 − 1.015 × (words ÷ sentences) − 84.6 × (syllables ÷ words)",
            worked: `206.835 − 1.015 × ${round(wordsPerSentence, 2)} − 84.6 × ${round(syllablesPerWord, 3)}`,
            note: "0 to 100, higher is easier. The only one of the six that goes up as the writing gets simpler.",
        },
        {
            id: "fk",
            name: "Flesch-Kincaid Grade",
            value: fk,
            display: round(fk).toFixed(1),
            unit: "grade",
            formula: "0.39 × (words ÷ sentences) + 11.8 × (syllables ÷ words) − 15.59",
            worked: `0.39 × ${round(wordsPerSentence, 2)} + 11.8 × ${round(syllablesPerWord, 3)} − 15.59`,
            note: "Commissioned by the US Navy in 1975. The number most people mean by grade level.",
        },
        {
            id: "ari",
            name: "Automated Readability Index",
            value: ari,
            display: round(ari).toFixed(1),
            unit: "grade",
            formula: "4.71 × (characters ÷ words) + 0.5 × (words ÷ sentences) − 21.43",
            worked: `4.71 × ${round(lettersPerWord, 3)} + 0.5 × ${round(wordsPerSentence, 2)} − 21.43`,
            note: "Counts characters rather than syllables, so it does not depend on a syllable guess at all.",
        },
        {
            id: "fog",
            name: "Gunning Fog Index",
            value: fog,
            display: round(fog).toFixed(1),
            unit: "grade",
            formula: "0.4 × [(words ÷ sentences) + 100 × (complex words ÷ words)]",
            worked: `0.4 × [${round(wordsPerSentence, 2)} + 100 × ${round(totalComplex / totalWords, 4)}]`,
            note: "Complex means three syllables or more, excluding proper nouns, hyphenated compounds and verbs that only get there through -es, -ed or -ing.",
        },
        {
            id: "smog",
            name: "SMOG Index",
            value: smog,
            display: round(smog).toFixed(1),
            unit: "grade",
            formula: "1.0430 × √(polysyllables × (30 ÷ sentences)) + 3.1291",
            worked: `1.0430 × √(${totalPolysyllables} × (30 ÷ ${sentences.length})) + 3.1291`,
            note: sentences.length >= 30
                ? "Designed for health material and validated at 30 sentences or more, which this sample has."
                : `Designed for samples of 30 sentences or more. This one has ${sentences.length}, so read it as indicative.`,
        },
        {
            id: "coleman",
            name: "Coleman-Liau Index",
            value: cl,
            display: round(cl).toFixed(1),
            unit: "grade",
            formula: "0.0588 × L − 0.296 × S − 15.8   (L = letters per 100 words, S = sentences per 100 words)",
            worked: `0.0588 × ${round(lettersPerWord * 100, 2)} − 0.296 × ${round((sentences.length / totalWords) * 100, 2)} − 15.8`,
            note: "Built for machine scoring, so like ARI it counts characters instead of syllables.",
        },
    ];
    const gradeScores = [fk, ari, fog, smog, cl];
    const consensusGrade = gradeScores.reduce((a, b) => a + b, 0) / gradeScores.length;
    const longList = sentences.filter((s) => s.words >= LONG_SENTENCE).map((s) => s.index);
    const passiveSentences = sentences.filter((s) => s.passive.length > 0);
    const complexList = [...complexTally.entries()]
        .map(([word, info]) => ({ word, syllables: info.syllables, count: info.count }))
        .sort((a, b) => b.count - a.count || b.syllables - a.syllables || a.word.localeCompare(b.word));
    const readingSeconds = (totalWords / WORDS_PER_MINUTE) * 60;
    const report = {
        empty: false,
        reliable: totalWords >= RELIABLE_WORD_COUNT,
        counts: {
            characters: text.length,
            charactersNoSpaces: text.replace(/\s/g, "").length,
            letters: totalLetters,
            words: totalWords,
            sentences: sentences.length,
            paragraphs: paragraphs.length,
            syllables: totalSyllables,
            complexWords: totalComplex,
            polysyllables: totalPolysyllables,
            monosyllables: totalMonosyllables,
            longSentences: longList.length,
            passiveSentences: passiveSentences.length,
            adverbs: adverbList.length,
        },
        averages: {
            wordsPerSentence: round(wordsPerSentence, 1),
            syllablesPerWord: round(syllablesPerWord, 2),
            lettersPerWord: round(lettersPerWord, 2),
            sentencesPerParagraph: round(sentences.length / paragraphs.length, 1),
            wordsPerParagraph: round(totalWords / paragraphs.length, 1),
        },
        ingredients,
        scores,
        flesch,
        fleschDisplay: round(flesch).toFixed(1),
        band: fleschBand(flesch),
        grade: fk,
        gradeLabel: gradeLabel(fk),
        gradeAudience: gradeAudience(fk),
        gradeTone: gradeTone(fk),
        consensusGrade: round(consensusGrade, 1),
        readingSeconds,
        readingTime: readingTimeLabel(readingSeconds),
        sentences,
        paragraphs,
        complexList,
        adverbList,
        passiveList,
        longList,
        recommendations: [],
    };
    report.recommendations = recommend(report);
    return report;
}
function recommend(report) {
    const out = [];
    const { counts, averages, sentences } = report;
    const veryLong = sentences.filter((s) => s.words >= VERY_LONG_SENTENCE);
    const long = sentences.filter((s) => s.words >= LONG_SENTENCE);
    if (veryLong.length > 0) {
        out.push({
            id: "very-long",
            tone: "bad",
            title: `${veryLong.length} sentence${veryLong.length === 1 ? " runs" : "s run"} past ${VERY_LONG_SENTENCE} words`,
            body: "A reader loses the start of a sentence this long before reaching the end of it. Find the conjunction in the middle and put a full stop there.",
            sentences: veryLong.map((s) => s.index),
        });
    }
    if (averages.wordsPerSentence > 20) {
        out.push({
            id: "avg-length",
            tone: averages.wordsPerSentence > 25 ? "bad" : "warn",
            title: `Sentences average ${averages.wordsPerSentence} words`,
            body: "Aim for 15 to 20 on average. Sentence length is the heavier of the two inputs to every formula here, so this is also the fastest way to move the score.",
            sentences: long.map((s) => s.index),
        });
    }
    else if (long.length > 0) {
        out.push({
            id: "some-long",
            tone: "warn",
            title: `${long.length} long sentence${long.length === 1 ? "" : "s"} in otherwise short prose`,
            body: `The average is fine at ${averages.wordsPerSentence} words, but these individual sentences are over ${LONG_SENTENCE}. Splitting them costs nothing.`,
            sentences: long.map((s) => s.index),
        });
    }
    const complexRatio = counts.words > 0 ? counts.complexWords / counts.words : 0;
    if (complexRatio > 0.12) {
        const worst = sentences
            .filter((s) => s.complexWords.length >= 3)
            .sort((a, b) => b.complexWords.length - a.complexWords.length)
            .slice(0, 12);
        out.push({
            id: "complex",
            tone: complexRatio > 0.18 ? "bad" : "warn",
            title: `${Math.round(complexRatio * 100)}% of words run to three syllables or more`,
            body: "Under 10% reads easily. Long words are usually replaceable: utilise becomes use, facilitate becomes help, in order to becomes to.",
            sentences: worst.map((s) => s.index),
        });
    }
    const passiveShare = counts.sentences > 0 ? counts.passiveSentences / counts.sentences : 0;
    if (passiveShare > 0.1) {
        out.push({
            id: "passive",
            tone: passiveShare > 0.25 ? "bad" : "warn",
            title: `Passive voice in ${counts.passiveSentences} of ${counts.sentences} sentences`,
            body: "Aim under one in ten. Passive writing hides who did the thing, which is fine when the doer is unknown and evasive when it is not. Check each one — this detection is a pattern match, not a parser.",
            sentences: sentences.filter((s) => s.passive.length > 0).map((s) => s.index),
        });
    }
    const adverbBudget = Math.max(1, Math.round(counts.words / 100));
    if (counts.adverbs > adverbBudget) {
        out.push({
            id: "adverbs",
            tone: counts.adverbs > adverbBudget * 2 ? "warn" : "good",
            title: `${counts.adverbs} adverbs, about ${adverbBudget} would be plenty`,
            body: "One -ly adverb per hundred words is a reasonable ceiling. Most of them prop up a weak verb: ran quickly is sprinted, said loudly is shouted.",
            sentences: sentences.filter((s) => s.adverbs.length > 0).map((s) => s.index),
        });
    }
    if (averages.wordsPerParagraph > 120) {
        out.push({
            id: "paragraphs",
            tone: "warn",
            title: `Paragraphs average ${averages.wordsPerParagraph} words`,
            body: "On a phone that is a wall. Break at every change of idea; three or four sentences is a comfortable maximum for the web.",
            sentences: [],
        });
    }
    if (sentences.length >= 5) {
        const lengths = sentences.map((s) => s.words);
        const mean = lengths.reduce((a, b) => a + b, 0) / lengths.length;
        const variance = lengths.reduce((a, b) => a + (b - mean) ** 2, 0) / lengths.length;
        if (Math.sqrt(variance) < 4) {
            out.push({
                id: "rhythm",
                tone: "good",
                title: "Every sentence is about the same length",
                body: "The formulas will not notice, but readers do. Drop a three-word sentence in after a long one and the paragraph stops sounding metronomic.",
                sentences: [],
            });
        }
    }
    if (out.length === 0) {
        out.push({
            id: "clear",
            tone: "good",
            title: "Nothing to fix on the numbers",
            body: `Sentence length, word length, passive voice and adverbs are all inside the usual limits at a ${report.gradeLabel} reading level. The formulas measure structure, so this is not the same as saying the argument is clear.`,
            sentences: [],
        });
    }
    return out;
}

# Open-source embedding and reranker models for SEO topical similarity and search-intent similarity

Scope note: research done 2026-09-26, 16 web tool calls. Items marked **[prior knowledge, not re-verified]** come from the researcher's training data (cutoff mid-2026), not from a source fetched in this session. Treat them as leads to confirm on the model card before adopting.

## Q0. Framing the two problems (symmetric vs asymmetric; which MTEB categories map to each)

### Takeaway
Both SEO problems are **symmetric** similarity problems (page↔page, query↔query), not asymmetric query→passage retrieval. The MTEB categories that measure them are **STS, Clustering and Pair Classification** (and to a lesser degree Reranking). Retrieval score, the number most "RAG" model choices are made on, measures a different notion. Topical overlap maps to STS + Clustering. Duplicate / near-duplicate / "same intent" yes-no maps to Pair Classification (the MTEB category built on paraphrase / duplicate-question pairs).

### Cited Findings
- MTEB spans eight task types: Bitext Mining, Classification, Clustering, Pair Classification, Reranking, Retrieval, STS, Summarization. — [emergentmind MTEB English](https://www.emergentmind.com/topics/mteb-english-leaderboard); [MTEB paper](https://arxiv.org/pdf/2210.07316)
- MTEB scores clustering with k-means over the embeddings and STS/retrieval with cosine similarity. — [MTEB paper via search snippet](https://arxiv.org/pdf/2210.07316)
- jina-embeddings-v3 makes the symmetric/asymmetric split explicit in its adapters: `retrieval.query` / `retrieval.passage` for asymmetric retrieval, `text-matching` for "tasks that quantify similarity between two texts, such as STS or symmetric retrieval", `separation` for clustering and re-ranking, `classification` for classification. — [jina v3 paper](https://arxiv.org/abs/2409.10173); [jina model page](https://jina.ai/models/jina-embeddings-v3/)
- EmbeddingGemma ships distinct prompts for the same split: retrieval query `task: search result | query:`, document `title: … | text:`, plus `task: clustering | query:`, `task: sentence similarity | query:`, `task: classification | query:`. — [EmbeddingGemma model card](https://huggingface.co/google/embeddinggemma-300m)
- The "Embedder's Dilemma" study (Aug 2026, 26 embedders 118M–14B vs 10 LLMs, 37 tasks) found LLMs and embedders "match on clustering, STS, and pair classification", LLMs lead only on reasoning-heavy retrieval, and embedders win classification. An LLM cost up to 1,431x more per benchmark pass (USD 154 vs USD 0.11). The authors recommend "use embedding models for similarity, classification, and clustering, and reserve LLMs for reasoning-intensive retrieval." — [arXiv 2608.12875](https://arxiv.org/abs/2608.12875)

### Inferences
- Formal mapping for the product:
  - (a) Topical overlap / cannibalization / pillar grouping = symmetric doc↔doc STS + clustering. Use the model's *clustering* or *similarity* mode on **both** sides. Never embed one page as "query" and the other as "passage".
  - Duplicate / near-duplicate = Pair Classification (binary, thresholded), best served first by lexical hashing (see Q4).
  - (b) Search-intent similarity for keywords = symmetric short-text query↔query similarity. The ground truth is behavioral (SERP overlap / co-clicks), not linguistic. Page↔query intent match is asymmetric, but "do these two pages satisfy the same intent" is symmetric again.
- The Embedder's Dilemma result supports the user's pipeline shape. Spending the LLM budget on the similarity step itself buys nothing on STS/clustering/pair tasks. The LLM earns its cost only on the final judgement.
- A likely source of "garbage candidates" today is using the retrieval query/passage prefixes (or a retrieval-only model) for page↔page comparison. Asymmetric training rewards "the passage answers the query", which places a broad hub page near many specific pages. That is exactly the false-positive pattern in cannibalization detection.

### Gaps
- There is no public MTEB-style benchmark of long web pages (1–5k tokens) for topical overlap. MTEB STS is mostly sentence-level. Clustering tasks use titles/abstracts (arXiv, Reddit, StackExchange), which are closer to page titles + H1s than to full bodies.

## Q1. Which open models score best on STS / clustering / pair classification, and does that ranking differ from retrieval?

### Takeaway
On the symmetric categories the ranking is **flatter** than on retrieval, and small models are close to the top. Qwen3-Embedding-0.6B reaches STS 86.57 / Clustering 54.05 / PairClass 84.37. The 8B reaches 88.58 / 58.57 / 87.52. On **pair classification** older/smaller models (gte-Qwen2-1.5B-instruct 87.52, multilingual-e5-large-instruct 86.24) **match or beat** Qwen3-0.6B (84.37) even though they trail badly on retrieval (50.25 / 53.47 vs 61.83). So yes, the ranking differs: retrieval gaps of 8–11 points shrink to ≤3 points, and sometimes invert, on STS / pair classification.

### Cited Findings
- MTEB English v2 (from the Qwen3-Embedding model card):

  | Model | Params | Mean | Clust. | PairCls | Rerank | Retrieval | STS |
  |---|---|---|---|---|---|---|---|
  | Qwen3-Embedding-0.6B | 0.6B | 70.70 | 54.05 | 84.37 | 48.18 | 61.83 | 86.57 |
  | multilingual-e5-large-instruct | 0.6B | 65.53 | 49.89 | 86.24 | 48.74 | 53.47 | 84.72 |
  | gte-Qwen2-1.5B-instruct | 1.5B | 67.20 | 53.54 | 87.52 | 49.25 | 50.25 | 82.51 |
  | Qwen3-Embedding-4B | 4B | 74.60 | 57.51 | 87.01 | 50.76 | 68.46 | 88.72 |
  | Qwen3-Embedding-8B | 8B | 75.22 | 58.57 | 87.52 | 51.56 | 69.44 | 88.58 |
  — [Qwen3-Embedding-0.6B card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- MMTEB (multilingual): Qwen3-0.6B Clust 52.33 / PairCls 80.83 / STS 76.17. multilingual-e5-large-instruct 50.75 / 80.86 / 76.81, so it ties or beats Qwen3-0.6B on pair classification and STS. NV-Embed-v2 (7B) scores only 40.80 / 78.94 / 71.10. Qwen3-8B scores 57.65 / 86.40 / 81.08. — [Qwen3-Embedding-0.6B card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- Qwen3-Embedding: Apache-2.0, 32k context, MRL dims 32–1024 (0.6B), instruction-aware; 8B was #1 on MMTEB multilingual (70.58) as of 2025-06-05. — [Qwen3-Embedding-0.6B card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B); [QwenLM GitHub](https://github.com/QwenLM/Qwen3-Embedding)
- A 2026 robustness study notes Qwen3-Embedding 8B/4B are among the best for STS and achieved the best clustering results. — [arXiv 2605.31142 (search snippet)](https://arxiv.org/pdf/2605.31142)
- EmbeddingGemma-300M: Gemma license (custom terms, not OSI), 2048-token context, 768d with MRL to 512/256/128, MTEB English v2 mean(task) 69.67, multilingual v2 61.15. Has dedicated clustering and sentence-similarity prompts. Runs in <200MB RAM quantized. — [EmbeddingGemma card](https://huggingface.co/google/embeddinggemma-300m); [BentoML guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)
  - A search snippet gave EmbeddingGemma STS 0.681 / pair classification 0.696 / clustering 0.402. It comes from a third-party evaluation with in-context demos, not the official MTEB protocol, and is **not comparable** to the table above. — [search snippet, arXiv 2608.12875/2605.01372](https://arxiv.org/pdf/2608.12875)
- jina-embeddings-v3: 570M, 8192 ctx, task LoRAs <3% of params (retrieval.query/passage, text-matching, separation, classification). — [jina v3 arXiv](https://arxiv.org/abs/2409.10173); [jina model page](https://jina.ai/models/jina-embeddings-v3/)
- jina-embeddings-v4: built on Qwen2.5-VL-3B-Instruct, **CC-BY-NC-4.0 (non-commercial)**, 2048d with MRL, adapters for retrieval / text-matching / code. — [BentoML guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)
- Nomic Embed Text V2: MoE with 475M total / 305M active, 512-token max, 768d (MRL→256), task prefixes like `search_document:`, open source. — [BentoML guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)
- BGE-M3: 8192 ctx, 100+ languages, dense+sparse+multi-vector. — [BentoML guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)
- gte-multilingual-base: 305M, 70+ languages, elastic dense + sparse output. — [BentoML guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)
- Newer 2026 entrants: KaLM-Embedding-Gemma3-12B (Tencent) tops a May 2026 MMTEB v2 snapshot on retrieval (75.7), but it is new (June 2026 arXiv). llama-embed-nemotron-8b (NVIDIA) held #1 Borda on MMTEB in Oct 2025. Qwen3-VL-Embedding-8B (Jan 2026) is multimodal SOTA on MMEB-V2 (77.8). — [link.sc / builderai 2026 roundups via search](https://link.sc/blog/best-embedding-models-2026); [Qwen3-VL-Embedding arXiv 2601.04720](https://arxiv.org/pdf/2601.04720). QZhou-Embedding claimed #1 on both MTEB leaderboards (Aug 2025) — [arXiv 2508.21632](https://arxiv.org/pdf/2508.21632). LGAI-Embedding-Preview posted STS 86.69 / PairCls 88.67 (June 2025) — [arXiv 2506.07438](https://arxiv.org/pdf/2506.07438).

### Inferences
- Licenses and specs **[prior knowledge, not re-verified]**:
  - bge-m3: MIT, 568M.
  - multilingual-e5-large-instruct: MIT.
  - gte-Qwen2-1.5B/7B-instruct: Apache-2.0.
  - NV-Embed-v2: CC-BY-NC-4.0, non-commercial, so excluded.
  - jina-embeddings-v3: CC-BY-NC-4.0, non-commercial despite open weights, so excluded for a commercial product unless licensed.
  - Snowflake arctic-embed-m/l v2.0: Apache-2.0.
  - mxbai-embed-large-v1: Apache-2.0.
  - nomic-embed-text-v1.5 / v2: Apache-2.0.
  - Stella (stella_en_400M/1.5B_v5): MIT, with instruction prompts for s2s vs s2p.
  - ModernBERT-based embedders (e.g., gte-modernbert-base, nomic-modernbert-embed): Apache-2.0, 8k ctx.
- Practical shortlist for a cheap, high-recall first stage, self-hosted and permissively licensed:
  1. **Qwen3-Embedding-0.6B** (Apache-2.0, 32k ctx, instructions, MRL). Best balance across STS / clustering / pair classification at small size. Its long context fits whole pages.
  2. **multilingual-e5-large-instruct** or **gte-Qwen2-1.5B-instruct** if pair-classification recall matters more than retrieval, since both beat Qwen3-0.6B on PairCls.
  3. **Qwen3-Embedding-4B** when the GPU budget allows. It gives +3.5 STS/clustering points and matches 8B on PairCls.
  4. **EmbeddingGemma-300M** for CPU/edge. Note the Gemma license and the 2k context: embed title+H1+summary rather than full bodies.
- Because the top-model gaps on these symmetric categories are only 1–4 points, input choice matters more than a model upgrade: what text is embedded (title+H1+headings vs. boilerplate-stripped body vs. chunk-pooled), plus correct symmetric prompting.

### Gaps
- Could not fetch a live MTEB leaderboard view sorted by STS/Clustering/PairCls. Per-category scores for EmbeddingGemma, arctic-embed v2, nomic v2, Stella, KaLM-Gemma3, and nemotron were not retrieved. The jina v3 HF card fetch failed (page too large), so its license is not confirmed in-session.
- MTEB PairClassification in English is mostly paraphrase / duplicate-question data (e.g., Twitter paraphrase, SprintDuplicateQuestions). No category measures "same search intent".

## Q2. Do instruction-tuned embedders change behaviour when told "same topic" vs "same search intent"?

### Takeaway
There is evidence that instructions shift embeddings: +1–5% on downstream tasks for Qwen3, and INSTRUCTOR/InBedder show the same text maps to different embeddings per task. There is **no published evidence specific to "same topic" vs "same search intent"** instructions. General instruction-following of embedders is weak on hard instruction benchmarks: Qwen3-0.6B scores 5.09 on MMTEB Instruction Retrieval, and multilingual-e5-large-instruct scores −0.40. Expect task-type prefixes (clustering vs retrieval vs similarity) to matter. Expect subtle free-text semantics ("intent, not topic") to be largely ignored unless the model is fine-tuned on that distinction.

### Cited Findings
- Qwen3: "using instructions typically yields an improvement of 1% to 5% compared to not using them." — [Qwen3-Embedding-0.6B card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- MMTEB "Inst. Retrieval" (FollowIR-style instruction sensitivity) scores: Qwen3-0.6B 5.09, 4B 11.56, 8B 10.06, multilingual-e5-large-instruct −0.40, NV-Embed-v2 1.04. — [Qwen3-Embedding-0.6B card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- INSTRUCTOR encodes the same input into different embeddings depending on the task instruction, is evaluated on 70 tasks (66 unseen), and is reported "robust to changes in instructions". Robustness here also means small rewordings do little. — [arXiv 2212.09741](https://arxiv.org/abs/2212.09741)
- LLM-based embedders under task instructions align the same text to different key tokens (e.g., emotion tokens under a sentiment instruction). This is mechanistic evidence that instructions redirect the embedding. — [arXiv 2406.17378](https://arxiv.org/pdf/2406.17378)
- GSTransform (following the InBedder protocol) evaluates instruction-following embedding on Clustering, STS and Triplet Alignment. This is the closest existing benchmark design to "cluster by aspect X vs aspect Y". — [arXiv 2505.24754](https://arxiv.org/pdf/2505.24754)

### Inferences
- A cheap internal experiment would settle it for this product. Take ~200 keyword pairs labelled by SERP overlap (same intent = ≥3–4 shared top-10 URLs). Embed them with Qwen3 under (i) no instruction, (ii) "Retrieve semantically similar text", (iii) "Given a search query, retrieve queries that would be satisfied by the same search results". Compare AUC. The FollowIR-type scores above predict small differences between (ii) and (iii).
- The robust lever is **fine-tuning, not prompting**. A 0.6B model contrastively fine-tuned on (keyword, keyword) positives drawn from SERP overlap is the direct analogue of Bing's GEN Encoder (Q3).

### Gaps
- No paper or blog found that measures an embedder under "topic" vs "intent" instructions on query pairs.

## Q3. SEO-/intent-specific work: SERP-overlap and click-graph supervision, intent datasets and classifiers

### Takeaway
Behavioral supervision for intent similarity is well established in industry research. Bing's **GEN Encoder** (SIGIR 2019) trained query embeddings on ~200M co-clicked query groups, which is the click-graph analogue of SERP overlap. No public model weights were found. For intent *labels*, **ORCAS-I** is the standard open dataset: 2M weakly labelled queries plus a 1,000-query expert gold set, labelled navigational / transactional / informational{factual, instrumental, abstain}. On short queries, fine-tuned or prompted LLMs beat the weak-supervision classifier on recall but lose on precision. SEO practitioners treat SERP overlap as ground truth and embeddings as a fast first pass.

### Cited Findings
- GEN Encoder (Bing): maps queries that share clicks to nearby embeddings, using ~200M co-clicked query groups from six months of logs, then fine-tunes on paraphrase tasks. It shows "robust and significant advantages over previous representation methods" on query-intent similarity, and ANN over it cut unseen queries by ~50%. No public release was indicated. — [arXiv 1907.10710](https://arxiv.org/abs/1907.10710)
- Intent-aware query similarity (CIKM 2011) learns latent intents from result-snippet words regularized by query co-clicks. — [ACM](https://dl.acm.org/doi/10.1145/2063576.2063619)
- Learning with click graph for query intent classification (TOIS): semi-supervised label propagation across a query–URL click graph. — [ACM](https://dl.acm.org/doi/10.1145/1777432.1777435)
- Product search: queries that click the same product are treated as positive pairs to fine-tune SimCSE-large. — [arXiv 2204.05231](https://arxiv.org/pdf/2204.05231)
- Microsoft holds a patent on an "intent encoder trained using search logs". — [USPTO 11138285](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11138285)
- ORCAS-I: labelled ORCAS (18M query–URL clicks, 10M queries). Taxonomy: navigational, transactional, informational → factual / instrumental / abstain. Labelled with Snorkel weak supervision; ORCAS-I-2M for training plus a 1,000-query expert gold test set; Snorkel labels "not outperformed by competing ML approaches". — [arXiv 2205.00926](https://arxiv.org/abs/2205.00926); [TU Wien data](https://researchdata.tuwien.ac.at/records/pp7xz-n9a06)
- SIGIR 2025 follow-up: LLaMA-3.1-8B/70B (in-context and fine-tuned) vs ORCAS-I weak supervision. "LLMs outperform weak supervision in recall, they continue to struggle with precision." — [arXiv 2504.21398](https://arxiv.org/abs/2504.21398)
- ORCAS-I predictor packaged as a TIRA component (WOWS 2024). — [WOWS 2024 paper](https://www.cs.ru.nl/~hiemstra/wows2024/WOWS_2024_paper_3.pdf)
- HF intent classifiers exist but are niche:
  - `dejanseo/bulgarian-search-query-intent` (mDeBERTa-v3; commercial-investigation / informational / navigational / transactional). — [HF](https://huggingface.co/dejanseo/bulgarian-search-query-intent)
  - Generic chatbot-intent models (`Falconsai/intent_classification`, `Serj/intent-classifier`) are not web-search-intent models. — [HF Falconsai](https://huggingface.co/Falconsai/intent_classification)
- Practitioner framing:
  - SERP clustering puts keywords together when they share significant top-10 URLs. SERP overlap is "the more reliable signal because it's grounded in what the ranking algorithm actually does".
  - Embeddings "cannot detect intent overlap that only exists in actual search results".
  - A 0.75–0.85 cosine threshold is typical for semantic clustering.
  - SERP overlap can mislead in thin or highly competitive niches.
  - The hybrid of semantic first pass then SERP validation is common.
  — [KeyClusters semantic clustering](https://www.keyclusters.com/blog/semantic-keyword-clustering); [KeyClusters tools comparison](https://www.keyclusters.com/blog/keyword-clustering-tools-comparison); [topicalmap.ai 2026 comparison](https://topicalmap.ai/blog/auto/keyword-clustering-software-comparison-2026). These are vendor blogs, and the figures are practitioner heuristics, not measured.

### Inferences
- The product already fetches SERP data server-side through the seo-data facade (DataForSEO). That makes a **self-supervised intent embedder** feasible. Mine (kw_a, kw_b) positives where top-10 URL Jaccard or shared-URL count ≥ threshold, and hard negatives where the embeddings are close but the SERPs are disjoint. Fine-tune Qwen3-Embedding-0.6B or an e5/gte-base with MultipleNegativesRanking / contrastive loss. This reproduces GEN Encoder's recipe at small scale. At inference it then needs no SERP call for new keywords.
- For intent **labels**, a small classifier (DeBERTa-v3 / ModernBERT) fine-tuned on ORCAS-I-2M covers nav/trans/info. It will not cover "commercial investigation", which SEO tools use and ORCAS-I lacks, so labelling that class needs an LLM or extra labels. Given the precision weakness of LLM intent labelling, keep the LLM as reviewer, not first-pass labeller.
- **[prior knowledge, not re-verified]** MS MARCO has query-type tags (description / numeric / entity / location / person). These are answer-type labels, not navigational/commercial intent, so they are of limited use here. TREC Web Track diversity tasks annotated query subtopics/intents, which is also of limited SEO relevance.

### Gaps
- No published open paper or model found that trains specifically on **Google SERP overlap** (as opposed to click logs) as the positive signal. No SEO tool (Keyword Insights, SE Ranking, Ahrefs, Semrush) was found publishing precision/recall of its clustering. Their pages are marketing and do not disclose models or thresholds.
- No open pretrained "search-intent similarity" embedding weights were found on HF.

## Q4. Near-duplicate detection: SimHash/MinHash vs embeddings, and when each wins

### Takeaway
Use **lexical hashing (MinHash/SimHash on boilerplate-stripped text) for duplicates and near-duplicates**. Use **embeddings for topical overlap and cannibalization** where wording differs. Screaming Frog, the de facto crawler reference, does exactly this: exact dupes by hash, near dupes by MinHash at a default 90% threshold, and a separate embedding-based "Semantically Similar" filter at a default cosine of 0.95 (adjustable down to 0.5).

### Cited Findings
- Screaming Frog near-duplicates: MinHash on page text (not HTML), default 90% similarity, nav/footer auto-excluded, include/exclude selectors configurable. Near dupes "can cause cannibalisation issues, crawling and indexing inefficiencies". — [SF Near Duplicates](https://www.screamingfrog.co.uk/seo-spider/issues/content/near-duplicates/); [SF v13 release](https://www.screamingfrog.co.uk/blog/seo-spider-13/)
- Screaming Frog v22 "Semantically Similar": LLM embeddings (OpenAI, Gemini, or local Ollama). Pages above 0.95 are flagged by default, and the threshold is adjustable to 0.5. It is aimed at pages "with different phrases but overlapping themes, covering the same subject multiple times, which can cause cannibalisation". — [SF Semantically Similar](https://www.screamingfrog.co.uk/seo-spider/issues/content/semantically-similar/); [SF v22](https://www.screamingfrog.co.uk/blog/seo-spider-22/)

### Inferences
- When each wins:
  - **MinHash (Jaccard over shingles)**: templated or boilerplate-heavy pages, location/variant pages, syndicated copies. It is deterministic, CPU-cheap, LSH-indexable, and precise at high thresholds. It is blind to paraphrase.
  - **SimHash**: the same use case with a fixed 64-bit fingerprint and Hamming-distance lookup. **[prior knowledge]** Google's Manku et al. (WWW 2007) used 64-bit SimHash with k≈3 for web-scale near-dup detection.
  - **Embeddings**: paraphrased or rewritten content, and same topic with different wording. This is the cannibalization case. Their weakness is that very high cosines (0.9+) also occur for pages that merely share a template, a domain vocabulary, or a long common boilerplate. That is why SF strips boilerplate and defaults to 0.95.
- Recommended layering for this product: (1) exact hash, (2) MinHash LSH ≥0.9 → "near-duplicate" with no model needed, (3) embeddings on title+H1+main content for "same topic" candidates, (4) cross-encoder or decision model, (5) LLM review. The embedding stage should exclude pairs already caught by stage 2, so the expensive stages only see paraphrase-level overlap.
- For cannibalization, supplement content similarity with **query-overlap evidence**: two URLs ranking for or receiving GSC clicks on the same queries. GSC stays in the app. This is the site-level equivalent of SERP overlap and is a behavioral ground truth embeddings cannot supply.

### Gaps
- No published head-to-head (precision/recall) of MinHash vs embeddings on web-page near-dup found in this session.

## Q5. Cross-encoder rerankers as a second stage for symmetric tasks

### Takeaway
Permissive, self-hostable options: **Qwen3-Reranker (0.6B/4B/8B, Apache-2.0, 32k ctx)**, **bge-reranker-v2-m3 (568M, Apache-2.0, multilingual)** and **mxbai-rerank-v2 (base 0.5B / large 1.5B, Apache-2.0)**. All are trained for query→passage relevance, so they are asymmetric by construction. Qwen3-Reranker accepts an instruction, which lets it be framed as a symmetric pair judge ("do these two pages cover the same topic?"), making it the closest open drop-in for the user's "decision model" stage.

### Cited Findings
- bge-reranker-v2-m3: Apache-2.0, 568M, 100+ languages; called the default "best quality/latency/license combination" for 2026. — [futureagi 2026](https://futureagi.com/blog/best-rerankers-for-rag-2026/); [HF card](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- mxbai-rerank-v2: base 0.5B / large 1.5B, Qwen-2.5 based, Apache-2.0, trained with a three-stage RL pipeline (GRPO, contrastive, preference). — [futureagi 2026](https://futureagi.com/blog/best-rerankers-for-rag-2026/)
- Qwen3-Reranker (June 2025): Apache-2.0, 100+ languages, "only mainstream open reranker with a 32K context", 4B called the sweet spot. — [futureagi 2026](https://futureagi.com/blog/best-rerankers-for-rag-2026/)
- Qwen3-VL-Reranker (Jan 2026) extends the family to multimodal. — [arXiv 2601.04720](https://arxiv.org/pdf/2601.04720)

### Inferences
- For symmetric pair judgements a reranker's score is not symmetric (score(A,B) ≠ score(B,A)). Score both orders and average, or use min for precision.
- An instruction-capable LLM reranker (Qwen3-Reranker) turned into a yes/no pair classifier via its instruction, and optionally fine-tuned on the product's own accepted/rejected suggestions, is the cheapest precision gain. It sits in exactly the "small decision model" slot the user already has, and it is self-hostable.
- Classic symmetric cross-encoders **[prior knowledge, not re-verified]** such as `cross-encoder/stsb-roberta-large` and `cross-encoder/quora-distilroberta-base` (duplicate-question) are trained on STS/paraphrase pairs and are truly symmetric-task models. They are small, fast, and Apache-2.0, but have 512-token limits, so they suit titles/H1/keywords, not full pages.

### Gaps
- No benchmark found of rerankers on symmetric STS/duplicate tasks (MTEB Reranking is asymmetric). No SEO-specific reranker exists that I could find.

## Q6. Practical recall/precision profile for cannibalization / keyword clustering (SEO tool posts, papers)

### Takeaway
Hard numbers are essentially absent. SEO vendors publish default thresholds, not measured precision/recall:
- Screaming Frog: MinHash 0.90, embedding cosine 0.95.
- Semantic keyword clustering: practitioner cosine 0.75–0.85.

The consistent qualitative finding is that embeddings are high-recall but conflate topic with intent (false merges), while SERP overlap is higher-precision for intent but costs a SERP fetch per keyword and misleads in thin niches.

### Cited Findings
- SF semantic similarity defaults to 0.95 cosine and near-duplicates to 90% MinHash. — [SF Semantically Similar](https://www.screamingfrog.co.uk/seo-spider/issues/content/semantically-similar/); [SF Near Duplicates](https://www.screamingfrog.co.uk/seo-spider/issues/content/near-duplicates/)
- Semantic keyword clustering "measures linguistic relatedness rather than confirmed search-engine behavior, so two keywords can embed close together and still not share SERP real estate". Threshold 0.75–0.85 is cited as producing "clean clusters without over-merging". — [KeyClusters](https://www.keyclusters.com/blog/semantic-keyword-clustering)
- LLM intent labelling: higher recall, weaker precision than weak supervision on ORCAS-I. — [arXiv 2504.21398](https://arxiv.org/abs/2504.21398)
- A practitioner claim that "modern BERT-based intent classifiers hit 90%+ accuracy" appeared in a glossary page. It is unsourced and should be treated as marketing. — [sorank glossary via search](https://www.sorank.com/glossary-geo-seo/search-intent-classification)

### Inferences
- Absolute cosine thresholds do not transfer between models: Qwen3, e5 and bge have very different cosine distributions (e5 famously compresses into 0.7–1.0). The user should calibrate a per-model threshold on labelled pairs, or use rank-based candidate generation (top-k per page plus a mutual-kNN filter) instead of a global cutoff. Mutual-kNN is a cheap way to cut hub-page garbage candidates.
- The main precision failure modes for cannibalization, based on the mechanisms cited above, and their fixes:
  1. Shared boilerplate/template text inflates similarity → strip boilerplate, as SF does.
  2. Hub/pillar pages are near everything under asymmetric embedding → use symmetric prompts and a mutual-kNN filter.
  3. Same topic but different intent (e.g., "best X" vs "X price") → add behavioral evidence (shared GSC queries / SERP overlap) before the LLM stage.

### Gaps
- No published precision/recall from Keyword Insights, SE Ranking, Ahrefs, Semrush or Screaming Frog. None of their engineering blogs surfaced in search with model or metric disclosures. Google Search Central guidance on cannibalization/duplicates was not fetched in this session.

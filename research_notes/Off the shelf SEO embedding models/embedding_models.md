# Off-the-shelf open-weight embedding models for an SEO product (as of Sept 2026)

Baseline in use: Xenova/multilingual-e5-small (quantized ONNX, CPU), "passage: " for page chunks averaged into a page vector, "query: " for keywords. Embeddings are recall only; Jev + LLM review decide correctness afterwards.

Source-quality legend used below:
- **[P]** = primary source fetched this session (model card, vendor blog, arXiv paper).
- **[S]** = secondary source or search snippet (aggregator blog, search-engine summary). Treat with caution.
- **[K]** = well-known spec from the model card that was NOT re-fetched in this session (budget ran out). The card URL is given so it can be checked. No benchmark numbers are given on [K] basis.

## Q1. Candidate specs: params, license, context, dims/MRL, languages, prompts, category scores

### Takeaway
The only sub-1B models with published per-category MMTEB scores that clearly beat the e5 family AND are commercially usable without a contact-sales step are **Qwen3-Embedding-0.6B (Apache 2.0)** and **EmbeddingGemma-300M (Gemma Terms of Use, commercial allowed with use-policy restrictions)**. The newest small model with the best headline MMTEB number, **jina-embeddings-v5-text (Feb 2026)**, is **CC-BY-NC-4.0** and needs a commercial licence from Elastic, as do jina v3/v4 and NV-Embed-v2.

### Cited Findings

**Qwen3-Embedding 0.6B / 4B / 8B (Alibaba Qwen, June 2025)**
- License **Apache 2.0**; 0.6B params; 32K context; output dims up to 1024 with custom dims 32–1024 (MRL); instruction-aware; 100+ languages incl. code — [P: HF model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- Conflict: one aggregator lists the Qwen3-Embedding license as "Tongyi Qianwen (custom)" and dates the models "early 2026" — both contradicted by the model card (Apache 2.0, June 2025 leaderboard date) — [S: presenc.ai](https://presenc.ai/research/best-open-weight-embedding-models-2026) vs [P: HF card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- MTEB **Multilingual** (MMTEB) per category, from the Qwen3 model card [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B):

| Model | Size | Mean(Task) | Bitext | Classif. | Clustering | Inst. Retrieval | Pair Class. | Rerank | Retrieval | STS |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-Embedding-0.6B | 0.6B | 64.33 | 72.22 | 66.83 | 52.33 | 5.09 | 24.59 | 80.83 | 61.41 | 64.64 |
| Qwen3-Embedding-4B | 4B | 69.45 | 79.36 | 72.33 | 57.15 | 11.56 | 26.77 | 85.05 | 65.08 | 69.60 |
| Qwen3-Embedding-8B | 8B | 70.58 | 80.89 | 74.00 | 57.65 | 10.06 | 28.66 | 86.40 | 65.63 | 70.88 |
| multilingual-e5-large-instruct | 0.6B | 63.22 | 80.13 | 64.94 | 50.75 | -0.40 | 22.91 | 80.86 | 62.61 | 57.12 |
| NV-Embed-v2 | 7B | 56.29 | 57.84 | 57.29 | 40.80 | 1.04 | 18.63 | 78.94 | 63.82 | 56.72 |
| BGE-M3 | 0.6B | 59.56 | 79.11 | 60.35 | 40.88 | -3.11 | 20.10 | 80.76 | 62.79 | 54.60 |
| gte-Qwen2-7B-instruct | 7B | 62.51 | 73.92 | 61.55 | 52.77 | 4.94 | 25.48 | 85.13 | 65.55 | 60.08 |
| Gemini Embedding (closed) | — | 68.37 | 79.28 | 71.82 | 54.59 | 5.18 | 29.16 | 83.63 | 65.58 | 67.71 |

- MTEB **English v2** per category, same card [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B):

| Model | Params | Mean(Task) | Classif. | Clustering | Pair Class. | Rerank | Retrieval | STS | Summ. |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3-Embedding-0.6B | 0.6B | 70.70 | 85.76 | 54.05 | 84.37 | 48.18 | 61.83 | 86.57 | 33.43 |
| Qwen3-Embedding-4B | 4B | 74.60 | 89.84 | 57.51 | 87.01 | 50.76 | 68.46 | 88.72 | 34.39 |
| Qwen3-Embedding-8B | 8B | 75.22 | 90.43 | 58.57 | 87.52 | 51.56 | 69.44 | 88.58 | 34.83 |
| multilingual-e5-large-instruct | 0.6B | 65.53 | 75.54 | 49.89 | 86.24 | 48.74 | 53.47 | 84.72 | 29.89 |
| NV-Embed-v2 | 7.8B | 69.81 | 87.19 | 47.66 | 88.69 | 49.61 | 62.84 | 83.82 | 35.21 |
| gte-Qwen2-7B-instruct | 7.6B | 70.72 | 88.52 | 58.97 | 85.90 | 50.47 | 58.09 | 82.69 | 35.74 |
| Gemini-embedding-exp-03-07 (closed) | — | 73.3 | 90.05 | 59.39 | 87.7 | 48.59 | 64.35 | 85.29 | 38.28 |

- Note: MMTEB "Pair Classification" values (~20–29) and English "Pair Class." values (~84–88) are on different task sets and are not comparable across the two tables — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- Qwen3-Embedding-8B was "No.1 in the MTEB multilingual leaderboard (as of June 5, 2025, score 70.58)" — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- Qwen3 prompt convention: instruction goes on the query side only ("Instruct: {task}\nQuery:{text}"); documents are embedded without an instruction; the card states omitting the instruction typically costs ~1–5% — [K: HF card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)

**EmbeddingGemma-300M (Google, Sept 2025)**
- 300M params (paper: 308M); 2,048-token context; 768 dims with MRL to 512/256/128; license = Gemma Terms of Use ("Terms"), not an OSI licence — [P: HF card](https://huggingface.co/google/embeddinggemma-300m); [P: paper](https://arxiv.org/html/2509.20354)
- Commercial use: Gemma Terms permit commercial use subject to Google's Prohibited Use Policy and pass-through of terms — [K: Gemma terms](https://ai.google.dev/gemma/terms) (not re-fetched; verify)
- Task prompts (asymmetric and symmetric): retrieval query `task: search result | query: {content}`; document `title: {title | "none"} | text: {content}`; clustering `task: clustering | query: {content}`; STS `task: sentence similarity | query: {content}`; classification `task: classification | query: {content}` — [P: HF card](https://huggingface.co/google/embeddinggemma-300m)
- MTEB scores (Mean Task / Mean TaskType): Multilingual v2 — 768d 61.15/54.31, 512d 60.71/53.89, 256d 59.68/53.01, 128d 58.23/51.77; English v2 — 768d 69.67/65.11, 512d 69.18/64.59, 256d 68.37/64.02, 128d 66.66/62.70; Code v1 768d 68.76 — [P: HF card](https://huggingface.co/google/embeddinggemma-300m)
- QAT checkpoints Q4_0, Q8_0 and mixed precision with "minimal performance degradation" — [P: HF card](https://huggingface.co/google/embeddinggemma-300m)
- Paper: EmbeddingGemma is #1 on MMTEB multilingual among models <500M params; comparison rows (Mean Task / Mean Type): Gecko Embedding 278M 53.47/46.23; **gte-multilingual-base 305M 58.24/51.44**; **multilingual-e5-large-instruct 560M 63.22/55.08** — [P: arXiv 2509.20354](https://arxiv.org/html/2509.20354)

**jina-embeddings-v5-text small / nano (Jina AI / Elastic, Feb 2026)**
- License **CC-BY-NC-4.0**; commercial use requires contacting Elastic sales — [S: search summary of Jina/HF pages](https://huggingface.co/jinaai/jina-embeddings-v5-text-small)
- v5-text-small 677M params, 32K context, 1024 dims; v5-text-nano 239M, 8K context, 768 dims; omni-small 1.7B (released May 7 2026), omni-nano 1.0B; text-small released Feb 18 2026 — [S: search summary](https://jina.ai/models/jina-embeddings-v5-text-small/)
- MMTEB 67.0 for v5-text-small vs "next best sub-1B model (Qwen3-0.6B with instructions at 64.3)"; MTEB English: v5-text-small 71.7, KaLM-mini-v2.5 71.3, v5-text-nano 71.0; retrieval avg 63.28 vs jina-embeddings-v4 (3.8B) 63.62 — [P: Jina blog](https://jina.ai/news/jina-embeddings-v5-text-distilling-4b-quality-into-sub-1b-multilingual-embeddings/)

**IBM granite-embedding-english-r2 (Aug 15 2025)**
- **Apache 2.0**; 149M params (47M small variant, 384 dims); 8,192 context; 768 dims; ModernBERT architecture; English; multilingual R2 sibling exists — [P: HF card](https://huggingface.co/ibm-granite/granite-embedding-english-r2)
- BEIR (15) 53.1 nDCG@10; MTEB-v2 (41 datasets) 62.8; CoIR 55.3; MLDR-en 40.7; vs bge-base-en-v1.5, e5-base-v2, gte-modernbert-base, modernbert-embed-base, arctic-embed-m-v2.0 it averages 59.5 across retrieval suites; MTEB-v2 Retrieval 56.4; 144 docs/s on H100 — [P: HF card](https://huggingface.co/ibm-granite/granite-embedding-english-r2)
- Card is retrieval-focused; no STS/Clustering breakdown given — [P](https://huggingface.co/ibm-granite/granite-embedding-english-r2)

**Snowflake arctic-embed-m-v2.0 / l-v2.0**
- **Apache 2.0**, 74 languages, paper arXiv 2412.04506 — [P: HF card (partial fetch)](https://huggingface.co/Snowflake/snowflake-arctic-embed-m-v2.0)
- m-v2.0 ≈305M params (113M non-embedding), 8,192 context, 768 dims with MRL to 256, "query: " prefix on queries only; l-v2.0 ≈568M, 1024 dims; retrieval-optimised — [K](https://huggingface.co/Snowflake/snowflake-arctic-embed-m-v2.0)

**Other candidates — licence/specs (card facts not re-fetched; no scores claimed)**

| Model | Params | Licence | Ctx | Dims / MRL | Lang | Prompts |
|---|---|---|---|---|---|---|
| multilingual-e5-small (current) | 118M | MIT | 512 | 384 | multi (~100) | "query: " / "passage: " — [K](https://huggingface.co/intfloat/multilingual-e5-small) |
| multilingual-e5-base | 278M | MIT | 512 | 768 | multi | same — [K](https://huggingface.co/intfloat/multilingual-e5-base) |
| multilingual-e5-large | 560M | MIT | 512 | 1024 | multi | same — [K](https://huggingface.co/intfloat/multilingual-e5-large) |
| multilingual-e5-large-instruct | 560M | MIT | 512 | 1024 | multi | "Instruct: …\nQuery: " on queries — [K](https://huggingface.co/intfloat/multilingual-e5-large-instruct) |
| bge-m3 | 568M | MIT | 8192 | 1024 (dense+sparse+ColBERT) | multi | no prefix — [K](https://huggingface.co/BAAI/bge-m3) |
| bge-small / base-en-v1.5 | 33M / 109M | MIT | 512 | 384 / 768 | English | optional query instruction — [K](https://huggingface.co/BAAI/bge-small-en-v1.5) |
| gte-multilingual-base | 305M | Apache 2.0 | 8192 | 768 (elastic 128–768) + sparse | multi (70+) | none — [K](https://huggingface.co/Alibaba-NLP/gte-multilingual-base) |
| gte-modernbert-base | 149M | Apache 2.0 | 8192 | 768 | English | none — [K](https://huggingface.co/Alibaba-NLP/gte-modernbert-base) |
| gte-Qwen2-1.5B / 7B-instruct | 1.5B / 7.6B | Apache 2.0 | 32K | 1536 / 3584 | multi | query instruction — [K](https://huggingface.co/Alibaba-NLP/gte-Qwen2-7B-instruct) |
| nomic-embed-text-v1.5 | 137M | Apache 2.0 | 8192 | 768, MRL to 64 | English | `search_query:` `search_document:` `clustering:` `classification:` — [K](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) |
| nomic-embed-text-v2-moe | 475M total / ~305M active | Apache 2.0 | 512 | 768, MRL to 256 | multi (~100) | `search_query:` / `search_document:` — [K](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe) |
| mxbai-embed-large-v1 | 335M | Apache 2.0 | 512 | 1024, MRL + binary | English | query prompt only — [K](https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1) |
| jina-embeddings-v3 | 570M | **CC-BY-NC-4.0** | 8192 | 1024, MRL | multi | LoRA task adapters (retrieval.query / retrieval.passage / separation / classification / text-matching) — [K](https://huggingface.co/jinaai/jina-embeddings-v3) |
| jina-embeddings-v4 | 3.8B (Qwen2.5-VL-3B base) | **CC-BY-NC-4.0** | 32K | 2048, MRL; multi-vector option | multi, multimodal | task adapters — [K](https://huggingface.co/jinaai/jina-embeddings-v4) |
| NV-Embed-v2 | 7.85B | **CC-BY-NC-4.0** | 32K | 4096 | English-centric | instruction on queries — licence also listed as CC-BY-NC by [S: presenc.ai](https://presenc.ai/research/best-open-weight-embedding-models-2026) |
| stella_en_400M_v5 / 1.5B_v5 | 0.4B / 1.5B | MIT (per [S: presenc.ai](https://presenc.ai/research/best-open-weight-embedding-models-2026)) | 512–8192 | MRL 256–8192 | English | s2p / s2s prompts — [K](https://huggingface.co/NovaSearch/stella_en_400M_v5) |
| Linq-Embed-Mistral | 7B | **CC-BY-NC** | — | 4096 | English | — [S: presenc.ai](https://presenc.ai/research/best-open-weight-embedding-models-2026) |

- Aggregator headline "MTEB" numbers (mixed MTEB versions, unverified): BGE-M3 ~68.2, bge-large-en-v1.5 ~64.2, stella-en-1.5B-v5 ~69.4, nomic-embed-text-v2 ~63.8, jina-v3 ~65.5, mxbai-embed-large-v1 ~64.7, gte-Qwen2-7B ~70.2 — [S: presenc.ai](https://presenc.ai/research/best-open-weight-embedding-models-2026). These do not match primary numbers (e.g. BGE-M3 is 59.56 on MMTEB per the Qwen card) and should not be used for decisions.

### Inferences
- For a commercial product the clean shortlist is Apache/MIT: Qwen3-Embedding-0.6B, gte-multilingual-base, snowflake-arctic-embed-m/l-v2.0, granite-embedding (r2), nomic-embed-text-v2-moe, bge-m3, multilingual-e5-*. EmbeddingGemma is usable commercially but under custom Gemma terms (legal review needed). Jina v3/v4/v5 and NV-Embed-v2, Linq are out without a paid licence.
- Qwen3-Embedding-0.6B beats multilingual-e5-large-instruct (same 0.6B size class) on MMTEB STS (+7.5) and Clustering (+1.6), and on English Clustering (+4.2) and STS (+1.9), while losing slightly on Retrieval and English Pair Classification. Its 32K context and MRL down to 32 dims also suit page vectors.
- CPU cost: Qwen3-0.6B (decoder, 1024d) will be several times slower on CPU than e5-small (118M encoder); EmbeddingGemma-300M or gte-multilingual-base are middle options. Throughput was not measured in any source fetched.

### Gaps
- Per-category MMTEB numbers for multilingual-e5-small/base/large were confirmed to exist in the MMTEB paper Table 2 ([arXiv 2502.13595](https://arxiv.org/html/2502.13595)) but the fetch tool would not reproduce them. Pull them from that table or the [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard).
- No per-category (STS/Clustering/PairClass) numbers were retrieved for EmbeddingGemma, gte-multilingual-base, arctic-v2, nomic v2, granite, gte-modernbert, mxbai, jina v5; only Mean(Task)/Mean(Type) for EmbeddingGemma and gte-multilingual-base.
- FollowIR / Instruction Retrieval only reported in the Qwen card table (MMTEB "Inst. Retrieval"): Qwen3-4B 11.56 is best; all sub-1B non-Qwen models ≤ ~0.
- Other 2025–2026 releases not investigated in this session: KaLM-Embedding (mini-v2.5 mentioned by Jina at 71.3 MTEB-en), F2LLM, QZhou-Embedding ([arXiv 2508.21632](https://arxiv.org/pdf/2508.21632)), Qwen3-VL-Embedding-2B (mentioned in [S: benchmark blog](https://zc277584121.github.io/rag/2026/03/20/embedding-models-benchmark-2026.html)), any open Voyage/Perplexity models. Licences unverified.
- Whether IBM released an r2 multilingual model with published scores: only mentioned as existing on the r2 card.

## Q2. Which models beat multilingual-e5-small for symmetric similarity / clustering, and by how much?

### Takeaway
Every modern candidate beats e5-small on MMTEB aggregate, but exact margins versus e5-small could not be extracted this session; the verified comparison is against e5-large-instruct (which is itself well above e5-small): Qwen3-0.6B is +7.5 STS / +1.6 Clustering over it on MMTEB, and EmbeddingGemma-300M sits between gte-multilingual-base and e5-large-instruct on MMTEB mean.

### Cited Findings
- MMTEB mean(task): Qwen3-Embedding-0.6B 64.33; multilingual-e5-large-instruct 63.22; EmbeddingGemma-300M 61.15; BGE-M3 59.56; gte-multilingual-base 58.24 — [P: Qwen card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B); [P: EmbeddingGemma paper](https://arxiv.org/html/2509.20354)
- MMTEB Clustering: Qwen3-8B 57.65, Qwen3-4B 57.15, gte-Qwen2-7B 52.77, Qwen3-0.6B 52.33, mE5-large-instruct 50.75, BGE-M3 40.88, NV-Embed-v2 40.80 — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- MMTEB STS: Qwen3-8B 70.88, Qwen3-4B 69.60, Qwen3-0.6B 64.64, gte-Qwen2-7B 60.08, mE5-large-instruct 57.12, NV-Embed-v2 56.72, BGE-M3 54.60 — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- BGE-M3, though strong at retrieval (62.79 MMTEB retrieval), is weak on MMTEB Clustering (40.88) and STS (54.60) — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- jina-v5-text-small claims +2.7 MMTEB over Qwen3-0.6B (67.0 vs 64.3) but is non-commercial — [P: Jina blog](https://jina.ai/news/jina-embeddings-v5-text-distilling-4b-quality-into-sub-1b-multilingual-embeddings/)

### Inferences
- For page-vs-page overlap and pillar clustering, clustering/STS scores matter more than retrieval. On those, the ranking among commercially usable open models is Qwen3-8B ≈ Qwen3-4B > Qwen3-0.6B > mE5-large-instruct > BGE-M3. BGE-M3 is a poor choice for the symmetric tasks despite its popularity.
- e5 model cards recommend the "query: " prefix on both sides for symmetric tasks (STS, clustering, paraphrase) and "passage: " only for the document side of retrieval [K: e5 card FAQ](https://huggingface.co/intfloat/multilingual-e5-small). The current pipeline uses "passage: " for page vectors that are then compared page-to-page; switching symmetric page comparisons to "query: " (or keeping separate symmetric and retrieval page vectors) is a zero-cost experiment.
- Because Jev + LLM review filter afterwards, a jump from e5-small to EmbeddingGemma-300M or Qwen3-0.6B is most likely to show up as higher recall at the same candidate budget, not as fewer final errors.

### Gaps
- e5-small's own MMTEB Clustering/STS/PairClass values were not extracted (see Q1 gaps), so the "by how much vs e5-small" number is not given here.
- No independent SEO-domain benchmark (pages, keywords) comparing these models was found.

## Q3. Short keyword / query similarity

### Takeaway
No primary source was found that benchmarks keyword-to-keyword search-intent similarity specifically. The best proxies are STS and Pair Classification scores plus models that expose an explicit symmetric prompt (EmbeddingGemma `task: sentence similarity`, `task: clustering`; Qwen3 with an instruction; nomic `clustering:`).

### Cited Findings
- EmbeddingGemma exposes dedicated symmetric prompts for sentence similarity and clustering, separate from retrieval query/document prompts — [P: HF card](https://huggingface.co/google/embeddinggemma-300m)
- Qwen3-Embedding is instruction-aware, so a custom instruction such as "identify search queries with the same intent" can be supplied on the query side — [P: HF card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- English STS: Qwen3-0.6B 86.57, mE5-large-instruct 84.72, NV-Embed-v2 83.82, gte-Qwen2-7B 82.69; English Pair Classification: NV-Embed-v2 88.69, mE5-large-instruct 86.24, Qwen3-0.6B 84.37 — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)

### Inferences
- For keyword clustering, use the model's symmetric prompt on both sides (e5: "query: " both sides; EmbeddingGemma: `task: clustering | query:`), not the retrieval pair.
- Pair Classification (duplicate-question style) is the closest proxy for "same intent?" — mE5-large-instruct is competitive there and stays in the e5 family (same prefixes, MIT).
- Short keywords carry little signal; SERP-overlap (shared ranking URLs, available from the DataForSEO facade) is the usual SEO industry method for intent grouping and can complement embeddings — not sourced in this session.

### Gaps
- No benchmark specifically on short keyword intent similarity found; recommend an internal eval on labelled keyword pairs.

## Q4. Asymmetric retrieval: internal-link candidates and social/lead matching

### Takeaway
For query→document recall, Qwen3-Embedding (instruction on query side, 32K context) is the strongest commercially licensed open option per size; among small encoders, arctic-embed-v2.0 and granite-embedding r2 are retrieval-specialised Apache models with 8K context. Instruction-following retrieval is weak in all sub-1B models.

### Cited Findings
- MMTEB Retrieval: Qwen3-8B 65.63, gte-Qwen2-7B 65.55, Qwen3-4B 65.08, NV-Embed-v2 63.82, BGE-M3 62.79, mE5-large-instruct 62.61, Qwen3-0.6B 61.41 — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- English Retrieval: Qwen3-8B 69.44, Qwen3-4B 68.46, NV-Embed-v2 62.84, Qwen3-0.6B 61.83, gte-Qwen2-7B 58.09, mE5-large-instruct 53.47 — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- MMTEB Instruction Retrieval (FollowIR-style): Qwen3-4B 11.56, Qwen3-8B 10.06, Qwen3-0.6B 5.09, gte-Qwen2-7B 4.94, NV-Embed-v2 1.04, mE5-large-instruct -0.40, BGE-M3 -3.11 — [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- granite-embedding-english-r2 (149M): MTEB-v2 retrieval 56.4, BEIR 53.1, MLDR-en 40.7 with 8K context — [P](https://huggingface.co/ibm-granite/granite-embedding-english-r2)

### Inferences
- Instruction conditioning ("find pages this page should link to") only meaningfully works at Qwen3-4B+; at 0.6B and below, treat instructions as a small bonus and rely on Jev/LLM for the "should link" judgement.
- For social posts / lead profiles (short docs vs free-text description), 512-token models are fine; long-context matters only for page-level retrieval.

### Gaps
- No source evaluated internal-link suggestion as a task.

## Q5. Long-document page embedding: whole page vs chunk averaging vs late chunking

### Takeaway
Late chunking (encode whole doc with a long-context model, then mean-pool per chunk) gives a modest ~1.9-point absolute nDCG@10 gain over naive chunking on BEIR, larger for small chunks, but can lose on synthetic needle tasks. No primary source compared "average of chunk vectors" vs "single long-context embedding" for document-to-document similarity.

### Cited Findings
- Late chunking vs naive chunking, averaged over 3 models × 4 BEIR datasets: fixed 256-token 54.0 vs 52.2; sentence boundaries 54.3 vs 52.4 ("3.63% relative improvement (1.9% absolute)"); semantic boundaries 53.8 vs 52.4 — [P: arXiv 2409.04701](https://arxiv.org/html/2409.04701v2)
- Late chunking helps most at small chunk sizes; on Needle-8192/Passkey-8192 naive chunking with large chunks won, i.e. late chunking hurts when the relevant info sits inside unrelated context — [P](https://arxiv.org/html/2409.04701v2)
- For documents >8192 tokens, "long late chunking" beat truncation on non-synthetic reading-comprehension sets — [P](https://arxiv.org/html/2409.04701v2)
- Late chunking requires a long-context embedder (the paper used jina v2/v3 and nomic); e5-small's 512-token limit rules it out — [P](https://arxiv.org/html/2409.04701v2)
- Long-context open options with commercial licences: Qwen3-Embedding (32K) [P](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B); granite-embedding-english-r2 (8K) [P](https://huggingface.co/ibm-granite/granite-embedding-english-r2); EmbeddingGemma (2K) [P](https://huggingface.co/google/embeddinggemma-300m); gte-multilingual-base, arctic-embed-v2.0, bge-m3, nomic-v1.5 (8K) [K]
- Related literature not fetched: [Reconstructing Context (arXiv 2504.19754)](https://arxiv.org/pdf/2504.19754) and [Context is Gold (arXiv 2505.24782)](https://arxiv.org/pdf/2505.24782) evaluate late chunking vs contextual retrieval — titles from search results only [S]

### Inferences
- For page-vs-page topical overlap, a whole-page embedding from an 8K/32K model (first ~2–8K tokens of main content) is a simpler alternative to chunk averaging; chunk averaging dilutes pages with mixed topics toward a centroid, which is acceptable for pillar clustering but blurs cannibalisation of specific subsections. Keeping chunk vectors for max-sim comparisons alongside the mean is a cheap hedge.
- Since chunk vectors already exist, "max over chunk-pair similarities" for near-duplicate/cannibalisation candidates and "mean vector" for clustering can be computed without re-embedding.

### Gaps
- No study found comparing mean-of-chunks vs whole-document embedding for document-level similarity/clustering specifically.

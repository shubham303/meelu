# Open-weight rerankers / cross-encoders for an SEO product (as of Sept 2026)

Context: the reranker is a cheap pre-filter between embedding recall and the Jev decision model + LLM review. Current model: Xenova/bge-reranker-base (quantized ONNX, CPU, 512 tokens). Tasks: (a) social post vs topic description with exclusions, (b) lead profile vs prose ICP, (c) directed "should A link to B", (d) page-vs-page overlap/cannibalization.

Notation: items marked **[unverified]** come from prior knowledge, not a source fetched in this session; treat them as leads to check on the model card.

## Q1. Candidate specs: params, license, context, multilingual, instruction support, output, benchmarks, latency

### Takeaway
The only models that are at once commercially licensed (Apache 2.0), instruction-aware and clearly stronger than bge-reranker-base are the Qwen3-Reranker family (0.6B/4B/8B), the mxbai-rerank-v2 family (0.5B/1.5B) and zerank-1-small. For a cheap CPU slot, the strongest drop-in plain cross-encoders are gte-reranker-modernbert-base (149M, 8k ctx, has ONNX) and the new Ettin reranker family (17M–1B, Apache, 8k ctx, May 2026). Almost every Jina reranker/ColBERT model, zerank-2, and all Contextual AI v2 rerankers are **non-commercial** (CC-BY-NC / CC-BY-NC-SA).

### Cited Findings

**Qwen3-Reranker (0.6B / 4B / 8B)**
- Apache-2.0; 0.6B has 28 layers; 32k context; 100+ languages — [HF Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- Takes a free-text instruction: prompt is `<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {doc}`; score = P(yes) = yes/(yes+no) from the next-token logits — [HF Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- Benchmarks from the Qwen card (MTEB-R / CMTEB-R / MMTEB-R / MLDR / MTEB-Code / FollowIR p-MRR) — [HF Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B):
  - Qwen3-Reranker-0.6B: 65.80 / 71.31 / 66.36 / 67.28 / 73.42 / **5.41**
  - Qwen3-Reranker-4B: 69.76 / 75.94 / 72.74 / 69.97 / 81.20 / **14.84**
  - Qwen3-Reranker-8B: 69.02 / 77.45 / 72.94 / 70.19 / 81.22 / **8.05**
  - bge-reranker-v2-m3 (0.6B): 57.03 / 72.16 / 58.36 / 59.51 / 41.38 / **-0.01**
  - gte-multilingual-reranker-base (0.3B): 59.51 / 74.08 / 59.44 / 66.33 / 54.18 / **-1.64**
  - jina-multilingual-reranker-v2-base (0.3B): 58.22 / 63.37 / 63.73 / 39.66 / 58.98 / **-0.68**
  - (Vendor-reported; note 4B beats 8B on FollowIR and MTEB-R.)
- Latency: in AIMultiple's H100 test, Qwen3-Reranker-4B took "over a second per query" (1000+ ms for top-100) vs 188 ms for jina-reranker-v3 and 243 ms for nemotron-rerank-1b; Hit@1 77.67% vs 83.00% for the best — [AIMultiple](https://aimultiple.com/rerankers) (secondary benchmark; the "autoregressive decoding" explanation there is questionable, since Qwen3-Reranker scores from one forward pass's logits — the cost is decoder size/prompt length, not generation).

**BGE family (BAAI)**
- bge-reranker-v2-m3: 0.6B, XLM-RoBERTa (bge-m3 base), multilingual, Apache-2.0, raw logit → sigmoid to [0,1]; no instruction input — [HF bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- bge-reranker-v2-gemma: ~3B (gemma-2b base), card says Apache 2.0, fixed prompt "Given a query A and a passage B, determine whether the passage contains an answer to the query by providing a prediction of either 'Yes' or 'No'.", score = "Yes" logit, max length 1024 (configurable) — [HF bge-reranker-v2-gemma](https://huggingface.co/BAAI/bge-reranker-v2-gemma). Flag: weights derived from Gemma are normally also bound by Google's Gemma Terms of Use regardless of the repo tag — check before commercial use **[unverified]**.
- bge-reranker-v2-gemma is slow: 7.20 s vs 0.89 s for mxbai-rerank-large-v2 on Mixedbread's A100 latency test; BEIR 55.38 — [Mixedbread blog](https://www.mixedbread.com/blog/mxbai-rerank-v2) (vendor-reported)
- bge-reranker-v2.5-gemma2-lightweight: Gemma-2-9B based, layerwise output + token compression **[unverified]**; Gemma license terms apply **[unverified]**. Not covered by any source fetched.
- bge-reranker-base / large: 278M / ~560M XLM-R, MIT, 512 tokens, zh/en **[unverified for license/length]**; bge-reranker-base is 278M per [AIMultiple](https://aimultiple.com/rerankers).

**Mixedbread**
- mxbai-rerank-base-v2 0.5B and mxbai-rerank-large-v2 1.5B, Apache 2.0, Qwen-2.5 base, 8K context ("32K compatible"), 100+ languages; trained with GRPO + contrastive + preference learning — [Mixedbread blog](https://www.mixedbread.com/blog/mxbai-rerank-v2)
- BEIR avg nDCG@10: large-v2 57.49, base-v2 55.57, Cohere-rerank-3.5 55.39, bge-reranker-v2-gemma 55.38, Voyage-rerank-2 54.54, jina-reranker-v2 54.35; A100 latency 0.67 s (base) / 0.89 s (large) — [Mixedbread blog](https://www.mixedbread.com/blog/mxbai-rerank-v2) (vendor-reported)
- mxbai v2 supports an optional instruction string in its Python package **[unverified]** — see [mxbai-rerank GitHub](https://github.com/mixedbread-ai/mxbai-rerank)
- mxbai-rerank-xsmall (v1, 70M): 64.67% Hit@1 in AIMultiple test (weakest of 8) — [AIMultiple](https://aimultiple.com/rerankers). v1 family (xsmall/base/large) is Apache 2.0, DeBERTa-based, 512 tokens **[unverified]**.

**Alibaba GTE**
- gte-reranker-modernbert-base: 149M, Apache 2.0, 8192 tokens, English, BEIR 56.73, LoCo 90.68, COIR 79.99; ships Transformers.js and **ONNX**, TEI CPU/GPU — [HF gte-reranker-modernbert-base](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base)
- In AIMultiple's test it tied the 1.2B nemotron-rerank-1b at 83.00% Hit@1 (MRR@10 0.8483 vs 0.8514) — [AIMultiple](https://aimultiple.com/rerankers)
- gte-multilingual-reranker-base: 0.3B (numbers above from Qwen card); Apache 2.0, 8k ctx **[unverified]**.

**Ettin Reranker family (new, 19 May 2026)**
- Six CrossEncoders 17M–1B (17.6M, 32.8M, 68.6M, 150.9M, 401.6M, 1.00B), Apache 2.0, ModernBERT-style Ettin encoders (JHU), 8,192 tokens; distilled (pointwise MSE) from mxbai-rerank-large-v2 over 143M pairs — [HF blog: Ettin Reranker](https://huggingface.co/blog/ettin-reranker)
- MTEB Retrieval nDCG@10: 17M 0.5576, 32M 0.5779 ("outperforms 568M BGE by +0.025"), 150M 0.5994, 1B 0.6114 (≈ teacher) — [HF blog](https://huggingface.co/blog/ettin-reranker)
- H100 bf16+FA2 throughput: 17M 7,517 pairs/s; 32M 6,602; 150M 3,237; 1B 928 — [HF blog](https://huggingface.co/blog/ettin-reranker)
- No instruction input mentioned (plain query/doc cross-encoder) — [HF blog](https://huggingface.co/blog/ettin-reranker)

**ZeroEntropy**
- zerank-1-small: Apache 2.0, 32,768 ctx, BF16, loads as sentence-transformers CrossEncoder; card-reported NDCG@10 0.861 finance, 0.680 STEM — [HF zerank-1-small](https://huggingface.co/zeroentropy/zerank-1-small). Param count reported as 1.7B; the fetch also returned "Base Model: Qwen/Qwen3-4B", which is inconsistent with 1.7B (likely Qwen3-1.7B) — verify on the card.
- zerank-2: on HF under a **non-commercial** license; commercial use needs a separate agreement — [ZeroEntropy blog](https://zeroentropy.dev/articles/open-source-alternatives-to-cohere-rerank/). zerank-1 (4B) license not confirmed in sources (believed CC-BY-NC **[unverified]**).

**Jina (all non-commercial)**
- jina-reranker-v2-base-multilingual: CC-BY-NC-4.0 — [HF card](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual) (via search summary)
- jina-reranker-m0 (multimodal): CC BY-NC 4.0 — [HF card](https://huggingface.co/jinaai/jina-reranker-m0) (via search summary)
- jina-reranker-v3: 0.6B on Qwen3-0.6B, listwise "last but not late" interaction, up to 64 docs in 131K ctx, BEIR 61.94; CC BY-NC 4.0 — [arXiv 2509.25085](https://arxiv.org/abs/2509.25085); [HF](https://huggingface.co/jinaai/jina-reranker-v3). 81.33% Hit@1 at 188 ms in AIMultiple — [AIMultiple](https://aimultiple.com/rerankers)
- jina-reranker-v3.5 (July 2026): 0.6B, hybrid sliding-window/global attention, BEIR 63.20, up to 1.56x faster than v3; **CC BY-NC-SA 4.0** — [arXiv 2607.18152](https://arxiv.org/abs/2607.18152)
- jina-colbert-v2: CC-BY-NC 4.0 — [HF discussion](https://huggingface.co/jinaai/jina-colbert-v2/discussions/15)

**Contextual AI (non-commercial)**
- ctxl-rerank-v2-instruct-multilingual 1B / 2B / 6B (+ quantized, e.g. 2b-nvfp4), instruction-following, multilingual, license cc-by-nc-sa-4.0 — [HF collection](https://huggingface.co/collections/ContextualAI/contextual-ai-reranker-v2) (via search summary); [HF 2B](https://huggingface.co/ContextualAI/ctxl-rerank-v2-instruct-multilingual-2b)
- Vendor claims: beats Qwen3-Reranker on InfoSearch and FollowIR; "~35% increase in recency-awareness" for quantized 2B vs second-best — [Contextual AI blog](https://contextual.ai/blog/rerank-v2) (no exact numbers in fetched text)

**NVIDIA**
- llama-nemotron-rerank-1b-v2: OpenMDW-1.1 license plus Llama 3.2 Community License (commercial use allowed under Llama terms) — [HF card](https://huggingface.co/nvidia/llama-nemotron-rerank-1b-v2) (via search summary). Best in AIMultiple: 83.00% Hit@1, MRR@10 0.8514, 243 ms on H100 — [AIMultiple](https://aimultiple.com/rerankers)

**Classic MS MARCO cross-encoders (sentence-transformers)**
- ms-marco-TinyBERT-L2-v2: DL19 nDCG@10 69.84, MRR@10 32.56, ~9000 docs/s; MiniLM-L6-v2: 74.30 / 39.01 / ~1800 docs/s; MiniLM-L12-v2: 74.31 / 39.02 / ~960 docs/s (V100 figures) — [SBERT pretrained cross-encoders](https://www.sbert.net/docs/cross_encoder/pretrained_models.html). Apache 2.0, 512 tokens, English **[unverified license]**.

**Late interaction (ColBERT)**
- GTE-ModernColBERT-v1 (LightOn): Apache-2.0, BEIR 54.67 ("first model to outperform ColBERT-small on BEIR"), LongEmbed 88.39 at 32k docs; trained at 300-token docs — [HF card](https://huggingface.co/lightonai/GTE-ModernColBERT-v1). (Card fetch said ~100M params; the ModernBERT-base backbone is ~149M — verify.)
- answerai-colbert-small-v1: ~33M, Apache 2.0 **[unverified]**.
- jina-colbert-v2: non-commercial (above).

**Reasoning / instruction-trained LLM rerankers**
- Rank1 (JHU): 0.5B–32B, Qwen2.5 bases, generates a reasoning chain then decides relevance; Rank1-0.5B ≈ RankLLaMA-13B on BRIGHT (13.9 avg); Rank1-32B NevIR pairwise accuracy 70.1% (= RankGPT-4o) vs RankLLaMA-13B 43.2%; Rank1-7B mFollowIR nDCG@20 0.586 vs FollowIR-7B 0.325 — [arXiv 2502.18418](https://arxiv.org/html/2502.18418v2). License not stated in fetched text (HF cards believed MIT **[unverified]**). Per-doc latency not reported; generation of reasoning tokens makes it far costlier than one-pass scoring.
- FollowIR-7B: Mistral-7B-Instruct-v0.2 base, +12.2 avg p-MRR on FollowIR (vs MonoT5-3B +2.5, MonoBERT -3.5, BGE/TART/INSTRUCTOR -2.4 to -5.0) — [FollowIR arXiv 2403.15246](https://arxiv.org/html/2403.15246)
- Promptriever: a promptable **bi-encoder** (retriever, not reranker): +14.3 p-MRR / +3.1 nDCG on FollowIR, +12.9 Robustness@10 on InstructIR, +1.4 BEIR via prompting — [arXiv 2409.11136](https://arxiv.org/abs/2409.11136). Llama-based, so Llama license terms apply **[unverified]**.

### Inferences
- Commercially safe shortlist (Apache/MIT/Llama-community/OpenMDW): Qwen3-Reranker 0.6B/4B/8B, mxbai-rerank base/large v2 (and v1), bge-reranker-v2-m3 / base / large, gte-reranker-modernbert-base, gte-multilingual-reranker-base, Ettin rerankers, zerank-1-small, nemotron-rerank-1b-v2, MS MARCO MiniLM, GTE-ModernColBERT, answerai-colbert-small. Excluded for commercial use without a deal: all Jina (v2, v3, v3.5, m0, colbert-v2), Contextual AI v2, zerank-2 (and likely zerank-1). bge gemma variants need a Gemma-terms check.
- For a CPU/ONNX pre-filter, the lowest-risk upgrade over bge-reranker-base is gte-reranker-modernbert-base (ONNX published, 16x the context, BEIR 56.73) or an Ettin 32M–150M model (would need ONNX export). Neither reads instructions.
- Qwen3-Reranker-0.6B is the smallest commercially licensed model that takes an instruction and was measured positive on FollowIR (5.41); 4B is markedly better at instructions (14.84), comparable to FollowIR-7B's +12.2 at about half the size. On CPU a 0.6B decoder is roughly 2x bge-reranker-v2-m3 compute per pair and much slower than a 149M encoder.

### Gaps
- No primary-source numbers found for bge-reranker-v2.5-gemma2-lightweight, mxbai v1, answerai-colbert-small, gte-multilingual-reranker-base license.
- No CPU/ONNX latency measurements for any candidate in fetched sources (all latency figures are GPU: H100 or A100).
- Contextual AI's exact FollowIR/InfoSearch numbers were not in the fetched blog text.
- Rank1 and Promptriever licenses not confirmed.

## Q2. Which rerankers follow instructions/criteria, and which handle negation?

### Takeaway
Classic cross-encoders (MonoBERT, MS MARCO MiniLM, BGE, TART-style) ignore or misuse instructions — they treat them as extra keywords, which means exclusion clauses like "not agencies" can *raise* the score of agency posts. Only LLM-based rerankers trained on instructions (Qwen3-Reranker, FollowIR-7B, Rank1, Contextual AI v2) show positive p-MRR. Negation (NevIR) is handled reasonably only by cross-encoders and listwise LLM rerankers; bi-encoders are near random.

### Cited Findings
- FollowIR: most models get negative p-MRR (BM25 -2.1, E5-base-v2 -3.9, MonoBERT -3.5, MonoT5-base -1.8, TART/INSTRUCTOR/BGE -2.4 to -5.0); positives are MonoT5-3B +2.5, Gecko +2.3, FollowIR-7B +12.2 — [FollowIR](https://arxiv.org/html/2403.15246)
- FollowIR finding: "models use instructions for keyword matching and are unused to longer instructions that may contain slightly less relevant words"; giving only keywords from the instruction matched or beat full instructions — [FollowIR](https://arxiv.org/html/2403.15246)
- Qwen card FollowIR p-MRR: Qwen3-Reranker 0.6B 5.41, 4B 14.84, 8B 8.05; bge-reranker-v2-m3 -0.01, gte-multilingual-reranker-base -1.64, jina-v2-multilingual -0.68 — [HF Qwen3-Reranker](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- NevIR reproduction (SIGIR 2025): most IR models "perform at or below the level of random ranking when dealing with negation"; "only cross-encoders and listwise LLM re-rankers achieve reasonable performance across both negation tasks" (NevIR and ExcluIR); listwise LLM rerankers best but below humans; fine-tuning on one negation dataset does not reliably transfer to the other — [arXiv 2502.13506](https://arxiv.org/abs/2502.13506)
- Rank1-32B reaches 70.1% NevIR pairwise accuracy (= RankGPT-4o); RankLLaMA-13B 43.2% — [Rank1](https://arxiv.org/html/2502.18418v2)
- Contextual AI markets v2 as instruction-following (e.g. recency, source preference) and claims wins on FollowIR/InfoSearch — [Contextual AI blog](https://contextual.ai/blog/rerank-v2) — but non-commercial license.
- bge-reranker-v2-gemma uses a fixed Yes/No prompt; the card does not document custom instructions — [HF](https://huggingface.co/BAAI/bge-reranker-v2-gemma)

### Inferences
- For tasks (a) and (b) with exclusions, do **not** paste the exclusion text into the query of a classic cross-encoder (bge-base, MiniLM, gte-modernbert, Ettin); keep the query to the positive topic and let Jev/LLM enforce exclusions. If the reranker must see criteria, Qwen3-Reranker (4B best, 0.6B acceptable) is the only commercially licensed off-the-shelf option with measured positive instruction following.
- Even Qwen3's FollowIR scores are small in absolute terms; treat instruction-following as a soft tilt, not a filter — consistent with the reranker being a pre-filter only.

### Gaps
- No NevIR/ExcluIR numbers found for Qwen3-Reranker, mxbai v2, gte-modernbert or Ettin.
- No FollowIR numbers for mxbai-rerank-v2 or zerank-1-small.

## Q3. Evidence on symmetric pair classification (duplicate / same-topic) with rerankers

### Takeaway
Query→document rerankers are trained on asymmetric relevance (short query, passage answering it); there is no primary evidence in the sources that they are calibrated for symmetric "same topic / duplicate" judgments. Purpose-trained symmetric cross-encoders exist (Quora duplicates, STS-B, NLI) and are the documented off-the-shelf fit, though they are older, English-only and 512-token.

### Cited Findings
- cross-encoder/quora-roberta-base 87.80 AP, quora-roberta-large 87.91 AP on Quora duplicates; stsb-roberta-base 90.17, stsb-roberta-large 91.47 (STS-B); nli-deberta-v3-base 90.04 MNLI-mm — [SBERT pretrained cross-encoders](https://www.sbert.net/docs/cross_encoder/pretrained_models.html)
- Quora cross-encoders output a 0–1 duplicate probability for a question pair — [SBERT Quora example](https://sbert.net/examples/cross_encoder/training/quora_duplicate_questions/README.html)
- Qwen3-Reranker's instruction field lets the task be redefined (default is web-search retrieval) — [HF Qwen3-Reranker](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)

### Inferences
- For (d) cannibalization, a practical off-the-shelf approach: score both directions (A→B and B→A) with a normal reranker and take min/mean, or use Qwen3-Reranker with an instruction such as "Judge whether the two pages target the same search intent". Both are untested workarounds; validate on a small labelled set.
- Page-level (long) pairs exceed 512 tokens; if a cross-encoder is used, 8k-context models (gte-reranker-modernbert-base, Ettin, mxbai v2, Qwen3) fit much more of each page than bge-reranker-base. Embedding cosine (already computed at recall) may be as good a pre-filter for (d) as any reranker.

### Gaps
- No benchmark found evaluating modern rerankers (Qwen3, mxbai v2, bge-v2) on symmetric duplicate/STS tasks.

## Q4. Is any reranker suited to directed "should A link to B" judgments?

### Takeaway
No open-weight reranker found is trained for directed internal-link suitability. The closest fit is an instruction-taking reranker (Qwen3-Reranker) with A as the "query" (the source passage/anchor context) and B as the "document", plus an instruction describing link suitability; classic cross-encoders can only score topical relevance of B to A.

### Cited Findings
- Reranker input is inherently ordered (query, document), and Qwen3 accepts an arbitrary `<Instruct>` string with P(yes) output — [HF Qwen3-Reranker](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- Classic rerankers reduce instructions to keyword matching — [FollowIR](https://arxiv.org/html/2403.15246)

### Inferences
- Use the ordered slot: query = anchor sentence/paragraph from A (short, like a real query), document = B's title + summary/lead. This matches how rerankers were trained (short query, passage) better than feeding whole page A.
- The directional judgment itself ("B deepens A's point, not a sibling duplicate") is exactly what the downstream Jev/LLM stages are for; the reranker should only prune topically irrelevant targets.

### Gaps
- No paper or benchmark on reranker performance for internal link recommendation was found in this session.

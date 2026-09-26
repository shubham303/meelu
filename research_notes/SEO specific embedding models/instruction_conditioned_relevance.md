# Instruction-Conditioned Relevance Matching (social-listening filter, content-match scoring, ICP/lead matching)

Scope: models and evidence for "does item X satisfy natural-language criteria C" where C is long, compositional and often negated ("not agencies", "must mention pricing pain"). Context: the current pipeline is embedding recall, then a small hosted yes/no decision model, then LLM review on a short list. Research date: 2026-09-26.

## Q1. For "does X satisfy C" with negations, how do bi-encoders, cross-encoder rerankers, NLI zero-shot and small generative judges compare?

### Takeaway
The evidence consistently ranks them the same way: bi-encoders and late-interaction models are near or below random on negation. Classic cross-encoders are middling. Instruction-trained or LLM-based rerankers and reasoning judges are clearly best. Even the best open models (Rank1-32B at 70.1% NevIR pairwise accuracy) stay below o3-mini (77.3%). So embeddings belong only in the recall stage, and a constraint or negation must be judged by a model that reads the criteria and the item together.

### Cited Findings
- NevIR (negation in IR) ranking: cross-encoders do best, late-interaction models next, bi-encoders and sparse models worst. Bi-encoder document representations are "nearly identical despite negation words", and ColBERT's MaxSim ignores negation words. Most IR models score at or below random ranking. — [NevIR, EACL 2024](https://aclanthology.org/2024.eacl-long.139/); [arXiv](https://arxiv.org/pdf/2305.07614)
- Original NevIR pairwise accuracy: the largest MonoT5 scores 50.6%. Bi-encoders and sparse models mostly score 5–10%, some below 2% (random = 25%). — [NevIR](https://arxiv.org/pdf/2305.07614)
- NevIR reproduction (2025), pairwise accuracy by class:
  - Bi-encoders: DPR 6.5%, ColBERT variants 12.8–19.8%, RepLlama 13.0%, Qwen-based embedders 11.8–19.0%, GritLM-7B 39.0%.
  - Cross-encoders: MonoT5 27.7–50.6%, BGE rerankers 32.2–43.5%, jina-reranker-v2 65.2%.
  - Listwise LLM rerankers: Qwen2-7B-Instruct 36.9%, Mistral-7B-Instruct 46.3%, GPT-4o-mini 64.1%, GPT-4o 70.1%, o3-mini 77.3%.
  — [Reproducing NevIR, arXiv 2502.13506](https://arxiv.org/html/2502.13506v1)
- The same reproduction finds that fine-tuning on NevIR barely transfers to ExcluIR (exclusion queries): models learn dataset shortcuts, not general negation logic. Cross-encoders transfer better than other architectures. Improving negation sometimes hurt general MS MARCO retrieval. — [arXiv 2502.13506](https://arxiv.org/html/2502.13506v1)
- Reasoning reranker Rank1 (pointwise, writes a reasoning chain, then true/false) on NevIR: Rank1-7B 65.1, Rank1-14B 67.5, Rank1-32B 70.1. RankLLaMA-7B scores 31.6, RankLLaMA-13B 43.2, MonoT5-3B 50.6. The authors say Rank1 matches GPT-4o and is "15+ points higher than the next closest model". — [Rank1, COLM 2025, arXiv 2502.18418](https://arxiv.org/pdf/2502.18418)
- FollowIR, built from TREC assessor narratives, finds that existing retrievers "fail to correctly use instructions, using them for basic keywords and struggling to understand long-form information". It introduces a pairwise instruction-sensitivity metric (p-MRR). — [FollowIR, arXiv 2403.15246](https://arxiv.org/abs/2403.15246)
- Standard rerankers score near zero or negative p-MRR on FollowIR, meaning they ignore changes to the instruction: jina-multilingual-reranker-v2-base −0.68, gte-multilingual-reranker-base −1.64, BGE-reranker-v2-m3 −0.01. The instruction-trained Qwen3-Reranker scores 0.6B 5.41, 4B 14.84, 8B 8.05. — [Qwen3-Reranker-0.6B model card](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- Bi-encoders can be trained to follow instructions. Promptriever trains on ~500k MS MARCO instances with instance-level instructions and "instruction negatives" (the same query where the instruction makes a passage non-relevant). Results: +14.3 p-MRR and +3.1 nDCG on FollowIR, +12.9 Robustness@10. The instruction negatives alone add +3.1 p-MRR. — [Promptriever, arXiv 2409.11136](https://arxiv.org/abs/2409.11136); [code](https://github.com/orionw/promptriever)
- NLI zero-shot: MoritzLaurer's deberta-v3-large-zeroshot-v2.0 (435M, 512 tokens) scores each (text, hypothesis) pair as entailment or not_entailment. It is trained on Mixtral-generated synthetic data plus commercially usable NLI data (MNLI, FEVER-NLI), evaluated on 28 classification tasks, and beats bart-large-mnli. — [model card](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0)
- Laurer et al. frame NLI as a "universal classification task" like instruction tuning. Their BERT-sized models do zero-shot and few-shot classification and are far more efficient than generative LLMs. The released classifier covers 33 datasets and 389 classes. — [arXiv 2312.17543](https://arxiv.org/abs/2312.17543)
- GLiClass (Knowledgator) scores all labels in one encoder forward pass instead of one pass per (text, label) as a cross-encoder does. It claims cross-encoder-level accuracy at lower cost, reports average zero-shot F1 0.6183 in its own benchmark, and can also act as a RAG reranker. — [GLiClass GitHub](https://github.com/knowledgator/gliclass); [gliclass-modern-base-v3.0](https://huggingface.co/knowledgator/gliclass-modern-base-v3.0); [docs](https://docs.knowledgator.com/docs/frameworks/gliclass/)
- Rank1 limitation relevant to high-recall filtering: it can be "particularly stringent in marking passages as true". On one TREC-COVID query it marked every passage non-relevant because none named the specific Wuhan wet market. A prompt telling it to assume a naive user helped. — [Rank1 §6](https://arxiv.org/pdf/2502.18418)

### Inferences
- Current pipeline: the embedding stage cannot enforce "not agencies" or "must mention pricing pain", so it should be tuned for recall only (loose threshold, large k), never as the filter. The negation comes back after the embedding stage whatever you do.
- The "small decision model answering yes/no" stage is exactly what Qwen3-Reranker and Rank1-style models are trained to do: score P(yes) from (instruction, query, document). Swapping a general small LLM for an instruction-trained reranker should give better-calibrated scores at the same or lower cost. It also returns a continuous score instead of a hard yes/no, which you need for recall-oriented thresholds.
- NLI zero-shot fits criteria that split into short atomic hypotheses ("This post is written by a marketing agency", "The author complains about pricing"). It is weaker on long compositional criteria because of the 512-token limit and because it was trained on single-sentence hypotheses. A practical pattern: an LLM breaks the ICP or topic prompt into 3–8 atomic hypotheses once per criteria, NLI scores each hypothesis against each item, and a boolean combination (AND of musts, NOT of exclusions) makes the decision. This is inferred, not benchmarked in the sources above.
- Exclusion and negation are the documented weak spot even for trained models (poor NevIR→ExcluIR transfer). Checking negative constraints as separate positive hypotheses ("Is this an agency?" → reject if yes) is likely more robust than one prompt that contains "not X".

### Gaps
- No head-to-head benchmark found comparing NLI zero-shot (DeBERTa/GLiClass) against instruction rerankers against small LLM judges on the same compositional-criteria task. The comparison above is stitched from different benchmarks.
- No NevIR or FollowIR numbers found for Qwen3-Reranker-0.6B/4B on NevIR, or for GLiClass/DeBERTa-NLI on either benchmark.

## Q2. Which open instruction-following rerankers and retrievers are strongest and smallest as of September 2026?

### Takeaway
- Best small pointwise instruction-aware reranker with a permissive license: Qwen3-Reranker (0.6B / 4B / 8B, Apache 2.0). The 4B has the best FollowIR score in its family (14.84).
- For hard negation or reasoning cases: Rank1 (Qwen2.5 bases, 0.5B–32B) trades much higher latency for large gains.
- mxbai-rerank-v2 (0.5B / 1.5B, Apache 2.0) is a strong general reranker. No instruction-following numbers were found for it.
- jina-reranker-v3 and v3.5 (0.6B listwise) are strong on BEIR but CC BY-NC (non-commercial).
- A new line of RL-distilled compact instruction-following rerankers (1B student from a 4B teacher, MAIR benchmark) appeared in September 2026.

### Cited Findings
- Qwen3-Reranker, Apache 2.0, 32K context. The model outputs a "yes"/"no" token; the score is the logit difference, and a sigmoid turns it into a 0–1 probability. It takes a custom instruction, which the authors say typically improves results by 1–5%. Scores:

  | Model | Params | MTEB-R | MMTEB-R | FollowIR p-MRR |
  |---|---|---|---|---|
  | Qwen3-Reranker-0.6B | 0.6B | 65.80 | 66.36 | 5.41 |
  | Qwen3-Reranker-4B | 4B | 69.76 | 72.74 | 14.84 |
  | Qwen3-Reranker-8B | 8B | 69.02 | 72.94 | 8.05 |
  | BGE-reranker-v2-m3 | 0.6B | 57.03 | 58.36 | −0.01 |

  — [HF card 0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B); [4B](https://huggingface.co/Qwen/Qwen3-Reranker-4B); [8B](https://huggingface.co/Qwen/Qwen3-Reranker-8B); [Qwen3 Embedding paper](https://arxiv.org/pdf/2506.05176)
- A sequence-classification conversion of Qwen3-Reranker-0.6B exists for sentence-transformers CrossEncoder use. — [tomaarsen/Qwen3-Reranker-0.6B-seq-cls](https://huggingface.co/tomaarsen/Qwen3-Reranker-0.6B-seq-cls)
- Rank1: the Qwen2.5 family was trained on ~600k MS MARCO examples with R1 reasoning chains (reasoning chains stay under 1000 tokens), in sizes 0.5B, 1.5B, 3B, 7B, 14B and 32B. There is a Llama 3.1 8B ablation, which slightly underperforms Qwen 7B. On BRIGHT, Rank1 often reaches about 2x the nDCG@10 of same-size rerankers (18.7 vs 7.7 cited for Rank1-7B vs a baseline). Returns diminish above 7B: Rank1-0.5B is comparable to RankLLaMA-13B. Quantized versions run all sizes, including 32B, on one 24GB GPU. In mFollowIR, the gap to the instruction-trained FollowIR-7B is +10.1 vs +4.8 p-MRR (multilingual). — [Rank1, arXiv 2502.18418](https://arxiv.org/pdf/2502.18418); [GitHub](https://github.com/orionw/rank1)
- Rank-K extends test-time reasoning to listwise reranking. — [arXiv 2505.14432](https://arxiv.org/pdf/2505.14432)
- mxbai-rerank-v2: Apache 2.0, large = 1.5B (base = 0.5B), trained in three RL stages (GRPO, contrastive, preference). BEIR average nDCG@10 57.49. The vendor claims 4.5x faster than bge-reranker-v2-m3. — [Mixedbread blog](https://www.mixedbread.com/blog/mxbai-rerank-v2); [docs](https://www.mixedbread.com/docs/models/reranking/mxbai-rerank-large-v2); [GitHub](https://github.com/mixedbread-ai/mxbai-rerank)
- jina-reranker-v3: 0.6B (Qwen3-0.6B base), listwise ("last but not late interaction"), up to 64 documents per pass in a 131K context. BEIR nDCG@10 61.94. License CC BY-NC 4.0. — [HF card](https://huggingface.co/jinaai/jina-reranker-v3); [arXiv 2509.25085](https://arxiv.org/abs/2509.25085)
- jina-reranker-v3.5 (July 2026): 0.6B, BEIR 63.20 ("matching a 4B model"), up to 1.56x lower listwise latency than v3 through hybrid attention, and +9.6 nDCG@10 on semi-structured retrieval. Non-commercial license. The abstract reports no instruction-following results. — [arXiv 2607.18152](https://arxiv.org/abs/2607.18152); [Jina blog](https://jina.ai/news/jina-reranker-v3-5-faster-listwise-reranking-hybrid-attention-self-distillation/)
- On-policy distillation plus off-policy GRPO for compact instruction-following rerankers (EMNLP 2026 Findings): a 4B teacher is improved with GRPO using LLM-judge rewards (88K examples) and distilled into a 1B student. Results: MAIR-11 nDCG@6 0.7670 (+4.6 over offline listwise KD), MAIR-Full (126 tasks, 9,356 queries) nDCG@6 0.6808 and MRR@6 0.7865. The student "exceeds two released 7B RL-trained rerankers". The paper is CC-BY-4.0. — [arXiv 2609.01947](https://arxiv.org/abs/2609.01947)
- Querit-Reranker (June 2026): compact multilingual rerankers trained by label-free distribution adaptation. — [arXiv 2606.19037](https://arxiv.org/pdf/2606.19037)
- FollowIR-7B, fine-tuned on FollowIR training data, is the original instruction-following reranker baseline. — [FollowIR](https://arxiv.org/abs/2403.15246)

### Inferences
- For the "decision model" slot, the default choice is Qwen3-Reranker-0.6B (cheap), with 4B if quality matters. The 4B's FollowIR score is nearly 3x the 0.6B's, and it beats the 8B. Put the product description or ICP in the instruction field, the post or profile in the document field, and read P(yes).
- Rank1-0.5B / 1.5B are candidates for a middle stage between the reranker and the final LLM, used only on borderline scores. Their reasoning chain also gives the reviewer an explanation.
- Avoid jina v3/v3.5 for a commercial product unless you get a license.

### Gaps
- License of the Rank1 model weights and of the 2609.01947 checkpoints was not confirmed. The "CC-BY-4.0" found applies to the arXiv paper. Check the HF cards.
- Not researched in depth (no fetched evidence): bge-reranker-v2-gemma / v2.5-gemma2-lightweight / v2-minicpm-layerwise (Gemma-based models carry Gemma terms), jina-reranker-m0 (multimodal, non-commercial as far as I know), RankZephyr (listwise 7B), InstructIR and BRIGHT details, MAIR construction. Their specific numbers are not reported here.
- No public leaderboard found that ranks all 2026 rerankers on an instruction-following benchmark specifically.

## Q3. Is there prior work or public data on social-listening relevance filtering and ICP/lead matching?

### Takeaway
No public benchmark dataset for "is this social post relevant to brand/product X" or "does this company/person match this ICP" was found. Commercial tools (Octolens and others) describe the same LLM-scoring pattern as the user's pipeline and rely on negative keywords plus user feedback. Academic lead-scoring work in 2026 is about conversion ranking from CRM data, not matching against an ICP written in prose.

### Cited Findings
- Octolens: an "AI relevance scoring engine" reads each keyword-matched post in context against the business description, tags intent (buying signals, churn risk) and filters name collisions. Users tune it with negative keywords and by marking wrong keeps, and the filter "tightens from their feedback". — [Octolens](https://octolens.com/); [keyword monitoring](https://octolens.com/keyword-monitoring)
- Reported failure modes: false positives when the keyword appears only in a URL, and pain-point monitoring across a broad problem space costing ~10 minutes of triage per hit. A competitor argues that AI-only filtering leaves "no lever to pull" when the AI drops a relevant mention. (These are competitor and aggregator sources, so treat them as anecdotal.) — [Snitchfeed comparison](https://snitchfeed.com/compare/octolens)
- Homonym brand names pulling in huge volumes of irrelevant content are the standard social-listening noise problem. — [Swydo roundup](https://www.swydo.com/blog/best-social-listening-tools/)
- A USPTO patent on "automatic annotation of social media communications for noise cancellation" shows the problem has been treated as supervised classification. — [US 10785182](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10785182)
- Lead scoring with LLMs (June 2026): a discriminative LLM framework that combines structured CRM features with unstructured interaction logs and uses hierarchical preference ranking. It targets long-cycle domains such as automotive and real estate. It notes that general LLMs "generate text rather than comparable scores". — [arXiv 2606.04387](https://arxiv.org/abs/2606.04387)
- SalesLoop (July 2026): an RL-from-performance-feedback approach to ranking sales leads. — [arXiv 2607.20655](https://arxiv.org/pdf/2607.20655)
- A patent covers targeted demand generation from ideal customer profiles. — [USPTO 9665885](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9665885)

### Inferences
- Because no public dataset exists, the practical path is to build one from your own logs. Every final-LLM-review verdict and every user keep/dismiss on the Social Listening and Lead Management desks is a labelled (criteria, item, label) triple. A few thousand of these are enough to calibrate thresholds (Q5). They may also be enough to fine-tune Qwen3-Reranker-0.6B or a DeBERTa NLI model, following the Promptriever lesson of including instruction negatives: the same item, labelled differently under different criteria.
- "Must score comparably, not generate text" (2606.04387) is the same argument for using a reranker's P(yes) over a generative yes/no.
- For ICP matching, firmographic constraints (employee count, industry, geography) are structured. They should be hard filters on enriched fields, not left to a text model. Only the soft parts ("founders who ...", "struggling with ...") need semantic matching.

### Gaps
- Brandwatch, Syften, Common Room, Clay and Apollo were not fetched. Their public descriptions of relevance filtering and ICP scoring are not in these notes.
- No public job-title normalisation or company-similarity embedding models were researched in this pass.

## Q4. What do latency and cost look like at thousands of items per minute?

### Takeaway
Encoder cross-encoders and NLI/GLiClass models (0.1–0.6B, one forward pass per pair) handle thousands of pairs per minute easily on one GPU, and are workable on CPU for short posts. LLM-based pointwise rerankers such as Qwen3-Reranker-0.6B are several times slower per pair but still fit on one GPU. Reasoning rerankers (Rank1) generate up to ~1000 tokens per judgment, so they belong only on small borderline sets.

### Cited Findings
- Aggregator benchmark (hardware and setup not fully described): top-20 rerank per query takes 831.4 ms for Qwen3-Reranker-0.6B (batch 32), 1,875.5 ms for Qwen3-Reranker-8B (batch 4) and 132.1 ms for jina-reranker-v2 at 0.3B (batch 1024). BGE-reranker-v2-m3 averages ~241 ms. The same source attributes the speed gap to sequence-classification heads (bge, gte-modernbert) using one forward pass, versus the Qwen3 LLM template. — [AIMultiple reranker benchmark](https://aimultiple.com/rerankers) (secondary source; treat numbers as indicative)
- Reported BGE throughput: A100 about 2,850 queries/s at batch 32, V100 1,320/s, T4 610/s. (Secondary source; unit "queries" is ambiguous.) — [search summary of reranker benchmarks](https://aimultiple.com/rerankers)
- The vendor claims mxbai-rerank-large-v2 (1.5B) is 4.5x faster than bge-reranker-v2-m3. — [Mixedbread](https://www.mixedbread.com/blog/mxbai-rerank-v2)
- GLiClass scores N labels in one forward pass, where an NLI cross-encoder needs N passes. This matters when one item is checked against many atomic hypotheses. — [GLiClass](https://github.com/knowledgator/gliclass)
- Rank1: up to 1000 output tokens per judgment. The authors use vLLM and quantization, and state that test-time compute "requires spending more compute" than classification-head rerankers. — [Rank1 §6](https://arxiv.org/pdf/2502.18418)
- TEI (Hugging Face Text Embeddings Inference) is a common self-hosting path for embedders and rerankers on GPU. — [Spheron TEI guide](https://www.spheron.network/blog/self-host-embedding-reranker-tei-gpu-cloud/)

### Inferences
- Rough arithmetic from the cited latencies: 831 ms per 20 pairs for Qwen3-Reranker-0.6B is ~1,400 pairs/minute unoptimised. With vLLM, larger batches and short social posts (~100–300 tokens) expect much more. Thousands per minute on one mid-range GPU is plausible but needs measuring.
- DeBERTa-v3-large NLI (435M) at 512 tokens is heavier than base models. Short posts batched on a GPU should easily exceed thousands of pairs per minute. On CPU, prefer deberta-v3-base-zeroshot or GLiClass small/base.

### Gaps
- No primary, same-hardware throughput benchmark was found across Qwen3-Reranker, mxbai-v2, DeBERTa-NLI and GLiClass. The numbers above come from an aggregator and vendor claims. Benchmark locally.

## Q5. How should thresholds be calibrated for high recall?

### Takeaway
No primary source was fetched for this question, so what follows is method, not evidence. Use the reranker's continuous P(yes), not a hard yes/no, and choose the threshold on a labelled sample from your own traffic so that recall reaches a target (for example 95%). Re-derive the threshold per criteria when possible.

### Cited Findings
- Qwen3-Reranker exposes a yes/no logit difference that a sigmoid maps to a 0–1 probability, so the score can be given a threshold. — [Qwen3-Reranker card](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- Reasoning rerankers can be over-strict (Rank1 marked every passage non-relevant on one query). The authors expect calibration-specific training data to reduce this, and a prompt telling the model to assume less prior knowledge helped. — [Rank1](https://arxiv.org/pdf/2502.18418)
- Octolens-style products calibrate through user feedback: marking wrong keeps tightens the filter. — [Octolens](https://octolens.com/keyword-monitoring)

### Inferences
- Procedure:
  1. Sample several hundred items per criteria type from the embedding-recall stage.
  2. Label them with the final LLM reviewer, spot-checked by a human.
  3. Plot the reranker P(yes) distribution for positives and negatives.
  4. Pick the largest threshold that keeps recall at or above target. A conformal-style lower quantile of positive scores gives a distribution-free recall guarantee.
  5. Monitor the positive rate per criteria and re-calibrate when it drifts.
- Scores are not comparable across criteria: a long, strict ICP compresses P(yes). Use a per-criteria threshold, or normalise with a small per-criteria set of known positives and negatives, which you can generate synthetically with the LLM.
- Put the recall tolerance in the cheap stage and the precision in the expensive stage. Use a loose embedding cutoff and a recall-targeted reranker threshold, then let the final LLM review (and optionally Rank1 on the borderline band) remove false positives.

### Gaps
- No fetched source on conformal prediction or recall-targeted threshold selection for rerankers specifically. The above is a standard method, not something found in this research.

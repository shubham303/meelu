# Building Datasets and Training Domain-Specific Small Models for SEO / Marketing Tasks

Scope: the seven tasks are (1) topical overlap, (2) intent similarity, (3) internal-link-worthiness, (4) social post vs. domain relevance, (5) content vs. free-text criteria, (6) lead vs. ICP, (7) page-type classification. The current pipeline is embed, then a small decision model, then LLM review. This file covers where to get labels, how to train, how to evaluate, and what gains have been reported. Research date: 2026-09-26.

## Q1. For each of the 7 tasks, what is the cheapest credible labeled-data source, and how many examples are typically enough?

### Takeaway
For almost every task, the cheapest credible label source is data the product already owns: DataForSEO SERP overlap (intent), GSC query-page clicks (query-page relevance), the user's own crawled link graph (link-worthiness positives), and the logged accept/reject decisions from the LLM review stage (every task). LLM-generated labels fill the gaps. Most public web-scale sets (MS MARCO, ORCAS) are research-only and cannot ship in a commercial model. Public reports show a few thousand to about 15k synthetic pairs is enough to fine-tune an embedder, and 8 labeled examples per class can already be competitive for SetFit classification.

### Cited Findings

**Intent similarity: SERP overlap (DataForSEO)**
- The SEO industry heuristic is that two keywords sharing 3 or more of the same top-10 URLs belong in the same cluster, and 0 or 1 shared URLs means separate pages. That is about 40% overlap. — [Nightwatch keyword clustering](https://nightwatch.io/blog/keyword-clustering/); [HubSpot keyword clustering](https://blog.hubspot.com/marketing/keyword-clustering)
- One tool uses graded bands of shared top-10 URLs: 7 to 10 means same page, 4 to 6 means shared cluster, 2 to 3 means weak adjacency, and 0 to 1 means separation. — [Claude SEO seo-cluster](https://claude-seo.md/skills/seo-cluster)
- Some clustering tools let the user set URL overlap between 4 and 10 as the strictness threshold. — [SEOcrawl](https://seocrawl.ai/blog/keyword-clustering); [thruuu](https://thruuu.com/blog/keyword-clustering-with-search-intent/)
- The reasoning behind this label: when Google returns the same top-10 for two queries, Google has decided they share one information need. — [Nightwatch](https://nightwatch.io/blog/keyword-clustering/)

**Query-page relevance: click logs (ORCAS / MS MARCO)**
- ORCAS has 18M clicked query-document connections over 10M distinct queries and 1.4M TREC DL documents. — [ORCAS](https://microsoft.github.io/msmarco/ORCAS.html); [arXiv 2006.05324](https://arxiv.org/pdf/2006.05324)
- **Licensing:** MS MARCO and ORCAS are for **non-commercial research only**. Microsoft grants no license and may not own the rights to the underlying documents. — [MS MARCO Terms](https://microsoft.github.io/msmarco/Notice.html)
- ORCAS-I adds intent labels to ORCAS queries using weak supervision. It inherits the same restriction. — [arXiv 2205.00926](https://arxiv.org/pdf/2205.00926)
- Promptriever's instruction training set is built on MS MARCO: about 491k queries, each with one positive and 30 hard negatives. That makes its data research-only too. — [Promptriever, OpenReview](https://openreview.net/pdf?id=odvSjn416y); [arXiv 2409.11136](https://arxiv.org/abs/2409.11136)

**Commercial-friendly query-product relevance: Amazon ESCI**
- About 130k queries and 2.6M human-labeled (query, product) judgments in 4 grades (Exact / Substitute / Complement / Irrelevant). It covers English, Japanese and Spanish. The repository is **Apache-2.0**. — [amazon-science/esci-data](https://github.com/amazon-science/esci-data); [arXiv 2206.06588](https://arxiv.org/abs/2206.06588)

**Page-type labels (task 7)**
- WebOrganizer released a 24-category **Format** taxonomy and classifiers. Categories include Product Page, About (Org.), Documentation, Tutorial, FAQ, Listicle, News Article, Personal Blog, Customer Support, Legal Notices, Content Listing, User Review, Spam/Ads and Q&A Forum. — [WebOrganizer/FormatClassifier](https://huggingface.co/WebOrganizer/FormatClassifier)
- The classifier is 140M parameters, built on `Alibaba-NLP/gte-base-en-v1.5`. Its input is `{URL}\n\n{text}`. It was trained on annotations from Llama-3.1-405B-Instruct prompted with detailed domain descriptions. There is a matching 24-category Topic classifier. — [HF model card](https://huggingface.co/WebOrganizer/FormatClassifier); [arXiv 2502.10341](https://arxiv.org/html/2502.10341v1)
- Models and training data are on the HF Hub and the code is on GitHub. — [WebOrganizer site](https://weborganizer.allen.ai/); [GitHub](https://github.com/CodeCreator/WebOrganizer)
- Web Data Commons extracts schema.org and other structured data from Common Crawl. It publishes class-specific subsets. — [WDC Schema.org series, WWW'23](https://dl.acm.org/doi/10.1145/3543873.3587331)
- The WDC product corpus (LSPM) has over 26M product offers from 79k websites, all annotated with schema.org. — [arXiv 2007.13829](https://arxiv.org/pdf/2007.13829)

**Link graph / anchor text (tasks 1 and 3)**
- WAT files hold JSON metadata extracted from Common Crawl WARCs, including the outlinks on each page. There is open-source code that pulls anchor text (followed and nofollowed) from WAT files. — [rjonesx/common-crawl-anchor-text-extraction](https://github.com/rjonesx/common-crawl-anchor-text-extraction)
- WDC hyperlink graphs: the 2012 graph has 3.5B pages and 128B links, and the 2014 graph has 1.7B pages and 64B links. These are page-level graphs without anchor text. — [WDC Hyperlink Graphs](https://webdatacommons.org/hyperlinkgraph/)
- ClueWeb22 includes an "anchor graph" (links plus anchor texts) described as useful context for documents in search. — [arXiv 2211.15848](https://arxiv.org/pdf/2211.15848)

**Lead / ICP matching (task 6)**
- The People Data Labs Free Company Dataset is **CC BY 4.0**, which allows any use including commercial use, with attribution. It is about 9M lines in CSV/JSON. — [PDL docs](https://docs.peopledatalabs.com/docs/free-company-dataset)

**How many examples are enough**
- Databricks fine-tuned embedders on ~6,000 (FinanceBench), 8,727 (DocsQA) and 14,220 (ManufactQA) synthetic samples. They got large Recall@10 gains (see Q2). — [Databricks blog](https://www.databricks.com/blog/improving-retrieval-and-rag-embedding-model-finetuning)
- With only 8 labeled examples per class on Customer Reviews sentiment, SetFit was competitive with RoBERTa-Large fine-tuned on the full 3k training set. — [huggingface/setfit](https://github.com/huggingface/setfit); [arXiv 2209.11055](https://arxiv.org/pdf/2209.11055)
- The HF reranker example used 99k GooAQ query-answer pairs, expanded to 578k labeled pairs by hard-negative mining. — [HF blog: Training rerankers](https://huggingface.co/blog/train-reranker)

### Inferences
Per-task cheapest source. These are my recommendations, built from the findings above.
1. **Topical overlap:** Use the user's corpora. Take pages from the same site section or cluster, plus pairs that GSC shows sharing many queries, as positives. Relabel with an LLM (Gecko-style, see Q3). Start with 5k to 15k pairs.
2. **Intent similarity:** DataForSEO SERP overlap is the best label here, and it is cheap because the product already pays for SERP calls. Use graded overlap (0 to 10 shared URLs, normalised) as the target for CoSENT/AnglE, or bucket it (≥4 shared = positive, ≤1 = negative) for MNRL. Gold GSC click pairs can also be used, since a page receiving clicks for a query is a positive query-page pair. Tens of thousands of query pairs are cheap to build.
3. **Internal-link-worthiness:** Existing contextual in-body links in the crawled sites are weak positives, after dropping nav, footer and breadcrumb links (same anchor on most pages means boilerplate). Common Crawl WAT anchors give external-scale data. Links are directional, so train a cross-encoder with the input "source page ⟶ target page" rather than a symmetric embedder. Negatives are topically similar pages that are not linked. LLM review logs become the gold label once they exist.
4. **Social post vs. domain relevance:** Use Apify-scraped posts scored by an LLM against domain descriptions. Community membership (subreddit to topic) is a weak signal. Around 2k to 5k LLM-labeled pairs per start is my estimate; I found no published number.
5. **Content vs. free-text criteria:** This is instruction-conditioned relevance, which is Promptriever's setting. Generate the criteria and hard "instruction negatives" with an LLM. Do not ship on Promptriever's MS MARCO data because of the licence.
6. **Lead vs. ICP:** Use the PDL free company data (CC BY 4.0) plus LLM-written ICP descriptions, and have an LLM label the matches. Company firmographics are structured, so a classifier on features plus a text cross-encoder may beat pure embeddings.
7. **Page type:** WebOrganizer Format labels and schema.org types from WDC (Product/Offer, FAQPage, Article, etc.) give weak labels. Collapse them to the product's taxonomy (money, product, category, pricing, docs, blog). About 50 to 200 LLM-labeled examples per class is enough for SetFit or a ModernBERT head.

### Gaps
- I did not verify the WebOrganizer model or data licence. The model card page shown did not state one. Check the HF repo before commercial use.
- I did not verify the current terms for Common Crawl, WDC or Reddit data. Common Crawl has its own terms of use, and each page stays under its original copyright. Reddit's API terms limit commercial and ML use. Both need a legal check. HN data via the official API is not assessed here.
- Crunchbase open data and "LinkedIn-like" datasets were not researched. LinkedIn scraping carries legal and ToS risk.
- No published source gives example counts for link-worthiness or social relevance specifically.

## Q2. What gains have domain-specific fine-tunes shown over general embedders/rerankers?

### Takeaway
Reported gains are large when the base model is weak on the domain. Databricks raised gte-large Recall@10 from 0.293 to 0.552 on FinanceBench, and a 150M reranker trained on in-domain data beat 13 baselines, including a 1.5B model. Gains are smaller when the base model is already near its ceiling. Performance on general benchmarks does not predict domain performance, so the only reliable test is on your own data.

### Cited Findings
- **Databricks** fine-tuned embedders on in-domain synthetic data. Recall@10 changes: gte-large-en-v1.5 went 0.293→0.552 (FinanceBench), 0.821→0.873 (ManufactQA), 0.849→0.884 (DocsQA). e5-mistral-7b went 0.479→0.670, 0.836→0.913, and 0.899→0.899 (no gain). Queries were generated by Llama 3 405B and filtered by GPT-4o as a judge. Fine-tuned embeddings "performed as well as or better than reranking" on several datasets. — [Databricks](https://www.databricks.com/blog/improving-retrieval-and-rag-embedding-model-finetuning)
- **HF reranker (ModernBERT-base, 150M)**, fine-tuned on GooAQ, reached 77.14 NDCG@10 when reranking the top 30, against 73.56 for the best of 13 baselines. With all positives included it reached 83.51, against 80.04 for a 1.54B competitor. Training took about 30 minutes on one RTX 3090, and the 396M large variant took under 1 hour. — [HF blog](https://huggingface.co/blog/train-reranker)
- In the sentence-transformers reranker example on gooaq-dev (1000 queries), MAP went 53.28→67.28 and NDCG@10 went 59.12→71.35. — [sbert.net rerankers](https://sbert.net/examples/cross_encoder/training/rerankers/README.html)
- **Voyage finance-2** averaged +7% over OpenAI (the next best) and +12% over Cohere on financial retrieval sets. — [Voyage finance blog](https://blog.voyageai.com/2024/06/03/domain-specific-embeddings-finance-edition-voyage-finance-2/)
- **Voyage law-2** was evaluated on 8 legal retrieval datasets. **Harvey + Voyage** fine-tuned a custom model from voyage-law-2 on more than 20B tokens of US case law plus expert-annotated questions. — [Voyage law blog](https://blog.voyageai.com/2024/04/15/domain-specific-embeddings-and-retrieval-legal-edition-voyage-law-2/); [Harvey](https://www.harvey.ai/blog/harvey-partners-with-voyage-to-build-custom-legal-embeddings)
- **FinMTEB ("Do We Need Domain-Specific Embedding Models?")**: seven SOTA embedders dropped significantly on finance tasks compared to MTEB. MTEB performance was "not correlated" with FinMTEB performance. — [arXiv 2409.18511](https://arxiv.org/abs/2409.18511)
- **LLM-teacher to small cross-encoder (e-commerce)**: using an LLM to label data for fine-tuning a TinyBERT cross-encoder gave +10% precision and +24% recall in one reported case. This comes from a search snippet; the Roku engineering page would not render, so treat it as unverified. — [Roku engineering](https://engineering.roku.com/improving-search-relevance-using-crossencoders-and-llms)
- **Amazon rationale-guided distillation**: LLM rationales used to guide a lightweight cross-encoder gave ROC-AUC +1.4% on multilingual e-commerce and +2.4% on ESCI. — [Amazon Science](https://www.amazon.science/publications/rationale-guided-distillation-for-e-commerce-relevance-classification-bridging-large-language-models-and-lightweight-cross-encoders)
- **eBay LLMDistill4Ads**: an LLM teacher, a cross-encoder assistant and a bi-encoder student for ad keyphrase relevance. It uses LLMs "as a scalable proxy for human judgments" to reduce click bias. The abstract gives no numbers. — [arXiv 2508.03628](https://arxiv.org/abs/2508.03628)
- **Rank-DistiLLM**: cross-encoders distilled from ranking LLMs reach effectiveness similar to the LLMs while being orders of magnitude more efficient. — [arXiv 2405.07920](https://arxiv.org/html/2405.07920v3)

### Inferences
- Expect the largest gains on the SEO-specific judgments a general embedder has never seen: intent (SERP-defined), link-worthiness (directional), and page type. Expect smaller gains on generic topical similarity, where strong general embedders are already good. This matches the e5-mistral DocsQA result, which gained nothing.
- A fine-tuned small embedder may remove the need for a reranker at the first stage (Databricks finding). That supports running embed-only filtering with a lower threshold for recall.

### Gaps
- I found no published SEO- or marketing-specific embedding fine-tune case study with numbers. I did not verify Jina, Nomic or Cohere domain fine-tuning case studies.
- I did not extract FinMTEB's exact numeric gap (only the abstract was readable).

## Q3. What's the recommended recipe to distill an LLM judge into a small fast classifier while preserving recall? (Includes training tooling, synthetic data and cost.)

### Takeaway
Recipe: (a) LLM-generate or LLM-relabel candidate pairs, Gecko-style. (b) Mine hard negatives with a first-stage embedder, keeping a margin to avoid false negatives. (c) Train a bi-encoder with (Cached)MNRL / GISTEmbed, plus Matryoshka if you want smaller dimensions. (d) Train a ModernBERT-class cross-encoder or a LoRA-tuned small LLM on the judge's yes/no labels or soft scores with BCE and `pos_weight`. (e) Calibrate the threshold on a gold set at a fixed target recall. (f) Loop the LLM-review accept/reject logs back in as new labels. Compute is cheap: a reranker trains in under 1 hour on a consumer GPU, and H100s rent for about $2–3/hr.

### Cited Findings

**Synthetic data and LLM distillation**
- **Wang et al., "Improving Text Embeddings with LLMs" (E5-mistral):** proprietary LLMs generated synthetic data for hundreds of thousands of embedding tasks across 93 languages. Training needs "less than 1k training steps". It is strong with no labeled data, and SOTA on BEIR/MTEB when synthetic and labeled data are mixed. — [arXiv 2401.00368](https://arxiv.org/abs/2401.00368)
- **Gecko / FRet:** for each passage, an LLM generates a task description and a query. Candidates are then retrieved and relabeled by the same LLM. The top-scored passage becomes the positive (often not the seed passage), and a lower-scored one becomes the hard negative. FRet is mixed with human data such as STS, NLI and classification. — [DeepMind](https://deepmind.google/research/publications/85521/); [HF summary](https://huggingface.co/blog/vladbogo/gecko)
- **Promptriever:** instance-level instructions are generated per query, and "instruction negatives" are mined. These are passages that are relevant to the query but violate the instruction. Results: +14.3 p-MRR / +3.1 nDCG on FollowIR, +12.9 Robustness@10 on InstructIR, and +1.4 BEIR from prompting. — [arXiv 2409.11136](https://arxiv.org/abs/2409.11136)
- Related: SyNeg creates LLM-synthesised hard negatives. ARHN uses answer-centric LLM relabeling of hard negatives to remove false negatives. — [SyNeg](https://arxiv.org/pdf/2412.17250); [ARHN](https://arxiv.org/pdf/2604.11092)
- WebOrganizer itself follows the "distil a 405B judge into a 140M classifier" pattern for page categories. — [arXiv 2502.10341](https://arxiv.org/html/2502.10341v1)

**Hard negative mining (sentence-transformers)**
- Reranker recipe: `mine_hard_negatives(num_negatives=5, range_min=10, range_max=100, max_score=0.8, margin=0.1)`. It skips the top-10 candidates, which are likely unlabeled positives, and caps similarity. Train with `BinaryCrossEntropyLoss` with `pos_weight` set to the negatives-to-positives ratio. Alternatives are LambdaLoss and ListNetLoss. — [HF blog](https://huggingface.co/blog/train-reranker)
- Caveat: training on only hard negatives can hurt easier cases. Reranking the top 200 can give worse top-10 than reranking the top 100. Mix hard and random negatives. — [sbert.net CE training overview](https://sbert.net/docs/cross_encoder/training_overview.html)

**Loss selection (sentence-transformers bi-encoder)**
- Pairs with a score: CoSENTLoss, AnglELoss, CosineSimilarityLoss. (anchor, positive) pairs: MultipleNegativesRankingLoss, or CachedMNRL for large effective batches on limited GPU memory. GISTEmbedLoss uses a guide model to drop in-batch false negatives. MatryoshkaLoss trains embeddings that can be truncated to smaller dimensions. Use the NO_DUPLICATES batch sampler with in-batch-negative losses. — [sbert.net training overview](https://sbert.net/docs/sentence_transformer/training_overview.html)
- Qwen3-Embedding and BERT-family embedders can be fine-tuned through Unsloth, which uses sentence-transformers underneath. — [Unsloth embedding fine-tuning](https://unsloth.ai/docs/basics/embedding-finetuning)
- SetFit trains in two steps: contrastive fine-tuning of the sentence encoder on pairs, then a classifier head. It works at about 8 examples per class. — [SetFit docs](https://huggingface.co/docs/setfit/conceptual_guides/setfit)
- LoRA freezes the base weights and trains low-rank adapters, reaching accuracy comparable to full fine-tuning. — [DataCamp Qwen3 fine-tuning](https://www.datacamp.com/tutorial/fine-tuning-qwen3)
- A study compares fine-tuning causal LLMs for classification with an embedding/classification head versus instruction (generate yes/no). — [arXiv 2512.12677](https://arxiv.org/html/2512.12677)

**Compute cost**
- ModernBERT-base reranker: about 30 minutes on one RTX 3090. Large (396M): under 1 hour. — [HF blog](https://huggingface.co/blog/train-reranker)
- H100 on-demand, mid-2026: about $2–3/GPU-hr on RunPod and Vast.ai (RunPod H100 PCIe from $1.99, SXM from $2.69). Hyperscalers go up to about $11/hr. — [IntuitionLabs](https://intuitionlabs.ai/articles/h100-rental-prices-cloud-comparison); [Spheron on RunPod](https://www.spheron.network/blog/runpod-h100-pricing-2026/); [Lambda pricing](https://lambda.ai/pricing)
- A100 about $1.99/hr, H100 from $3.29/hr on some clouds. — [SynpixCloud](https://www.synpixcloud.com/blog/cloud-gpu-pricing-comparison-2026)

### Inferences
Recommended recipe, synthesised from the sources above:
1. **Seed:** sample candidate pairs from real traffic, meaning what the embed stage actually passes. Label them with the strong LLM as yes/no plus a 0–1 confidence, or a graded 0–3 score. Keep the rationale if you want the Amazon-style rationale distillation.
2. **Mix in weak labels** where they exist: SERP overlap for intent, GSC clicks, in-body links. Use the LLM to relabel disagreements (Gecko).
3. **Student choice:**
   - For stage 1 recall, use a bi-encoder (e.g. gte/ModernBERT-embed or Qwen3-Embedding-0.6B) with CachedMNRL or GISTEmbed plus Matryoshka.
   - For stage 2, use a cross-encoder (ModernBERT-base/large) with BCE and soft labels. Soft teacher probabilities keep more information than hard labels.
   - For free-text criteria (task 5) and lead/ICP (task 6), where the instruction varies per call, use a LoRA-tuned Qwen3 0.6–1.7B yes/no model (TRL/Unsloth). Alternatively, use a Promptriever-style instruction-trained cross-encoder that concatenates the criteria with the text.
4. **Preserve recall:**
   - Weight positives (`pos_weight`) or oversample them.
   - Choose the threshold on a held-out gold set at the target recall (e.g. 0.95–0.98), not at 0.5.
   - Mix random and hard negatives.
   - Filter false negatives with a margin or `max_score`.
5. **Flywheel:**
   - Log every LLM-review decision along with the student's score.
   - Periodically retrain on the disagreements: uncertainty sampling around the threshold, plus every case the student rejected that the LLM would have accepted. Audit a random slice of student rejects with the LLM, because otherwise student false negatives are never seen.
6. **Cost:** a full train of either student fits in under 2 GPU-hours, which is about $5–10 per run on rented H100s. LLM labeling cost (for example 20k pairs) will dominate.

### Gaps
- No source here gave a quantified "recall kept vs. teacher" figure for yes/no distillation. The Roku +24% recall figure is unverified.
- I did not verify sentence-transformers v5 specifics (e.g. SparseEncoder) or exact Unsloth/TRL/Axolotl classification recipes and timings for Qwen3/Gemma.

## Q4. Evaluation for high-recall filtering

### Takeaway
Evaluate each stage on a small gold set (a few hundred to a thousand LLM-plus-human-verified pairs per task). Report recall@k or recall at a threshold, precision at fixed recall, and pass-through rate (the fraction forwarded to the next, costlier stage). Calibrate thresholds on held-out data, not training data.

### Cited Findings
- Standard reranker metrics are MAP, MRR@10 and NDCG@10. The HF blog separates a "realistic" setting (reranking the retriever's top-k, so misses are counted) from an evaluation that includes all positives. Use the realistic setting to measure end-to-end recall. — [HF blog](https://huggingface.co/blog/train-reranker); [sbert.net](https://sbert.net/examples/cross_encoder/training/rerankers/README.html)
- Databricks measured Recall@10 plus downstream RAG accuracy. Their eval sets were small (150 and 139 queries). — [Databricks](https://www.databricks.com/blog/improving-retrieval-and-rag-embedding-model-finetuning)
- The number of candidates reranked (100 vs. 200) changes outcomes for hard-negative-trained models, so tune k together with the model. — [sbert.net CE overview](https://sbert.net/docs/cross_encoder/training_overview.html)

### Inferences
- Metrics per stage:
  - Recall against the gold positives.
  - Pass-through rate.
  - Cost per 1k candidates, where cost = pass-through × downstream unit cost.
  - End-to-end recall, which is the product of stage recalls.
- Build gold labels first: LLM-label about 1k pairs per task, then have a human check the disagreements and a random sample.
- Measure "cost saved" as the reduction in LLM-review calls at equal end-to-end recall.

### Gaps
- No source here gives specific calibration methods (Platt or isotonic) or benchmarks for high-recall cascades.

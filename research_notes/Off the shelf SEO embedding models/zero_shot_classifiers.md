# Open-weight zero-shot / off-the-shelf classifiers for page_type pre-labelling and criteria screening (as of Sept 2026)

## Zero-shot NLI classifiers (MoritzLaurer zeroshot-v2.0, ModernBERT variants, bart-large-mnli, tasksource)

### Takeaway
The MoritzLaurer zeroshot-v2.0 family is the most mature open NLI option. The `-c` variants (roberta/deberta/bge-m3 `-zeroshot-v2.0-c`) are trained only on commercially friendly data. deberta-v3-large-zeroshot-v2.0 has the best accuracy of the family but only a 512-token context. The bge-m3 and ModernBERT variants accept up to 8k tokens, which matters for 8,000 characters of page body. NLI cost grows linearly with the number of labels (one forward pass per label), and a 2026 benchmark found NLI cross-encoders stop improving as the backbone grows.

### Cited Findings
- deberta-v3-large-zeroshot-v2.0: 0.4B params, MIT license. It reaches a mean F1-macro of 0.676 zero-shot (0.673 in the few-shot setting) across 28 datasets. The facebook/bart-large-mnli baseline scores 0.497. Context is 512 tokens for deberta-v3; the bge-m3 variants take 8,192. ONNX weights are published. — [HF card](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0)
- Licensing split: all v2.0 models use Mixtral-8x7B-generated synthetic data plus MNLI and FEVER-NLI, which the card calls "commercially-friendly". Models without the "-c" suffix also include ANLI, WANLI and LingNLI, which carry a "broader mix of licenses". The variants are roberta-base/large-zeroshot-v2.0-c, deberta-v3-base/large-zeroshot-v2.0-c, deberta-v3-base/large-zeroshot-v2.0, bge-m3-zeroshot-v2.0-c and bge-m3-zeroshot-v2.0. — [HF card](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0)
- The deberta-v3 models "perform clearly better than roberta, but [are] a bit slower". — [HF card](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0)
- ModernBERT-large-zeroshot-v2.0: 0.4B params, Apache 2.0, 8k context window. Its card reports mean accuracy 0.85 and F1-macro 0.834 on its own test suite, and 1,116 texts/sec on an A100 40GB at batch size 32. The author says it "performs slightly worse than DeBERTav3 on average" but is "multiple times faster and consumes multiple times less memory". It was trained on "the same dataset mix as the zeroshot-v2.0 models". The card does not say whether that is the `-c` mix, so its commercial cleanliness is ambiguous even though the weights carry an Apache tag. The author said a newer version with better synthetic data was in preparation to make use of the 8k context. — [HF card](https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0); a base variant also exists ([HF](https://huggingface.co/MoritzLaurer/ModernBERT-base-zeroshot-v2.0)); bf16 gives roughly a 2x speedup ([author on X](https://x.com/MoritzLaurer/status/1876307846268166513))
- Laurer et al., "Building Efficient Universal Classifiers with NLI": trained on 33 datasets with 389 classes, with a reported 9.4% zero-shot improvement over earlier models. Predecessor models had more than 55M downloads by Dec 2023. The paper includes reusable notebooks. — [arXiv 2312.17543](https://arxiv.org/abs/2312.17543)
- facebook/bart-large-mnli: 0.4B params, MIT license. It uses hypothesis templates such as "This example is {label}." and supports `multi_label=True`. — [HF card](https://huggingface.co/facebook/bart-large-mnli)
- tasksource/ModernBERT-base-nli: 0.1B params, Apache 2.0. It is trained for 200k steps on a large NLI mix (MNLI, ANLI, SICK, WANLI, doc-nli, LingNLI, FOLIO, LogicNLI and others). The card claims it beats Llama 3.1 8B Instruct on ANLI and FOLIO. The training mix includes ANLI, WANLI and LingNLI, which is the same license caveat as Laurer's non-`-c` models (this is my inference). — [HF card](https://huggingface.co/tasksource/ModernBERT-base-nli)
- The BTZSC benchmark (22 datasets, 38 checkpoints; arXiv, Mar 2026) found that NLI cross-encoder performance "plateaued despite increased backbone size". Rerankers led (Qwen3-Reranker-8B, macro F1 0.72). Embedding models such as GTE-large-en-v1.5 gave "the best trade-off between accuracy and latency". Instruction-tuned 4–12B LLMs reached macro F1 up to 0.67. — [arXiv 2603.11991](https://arxiv.org/abs/2603.11991)

### Inferences
- For page_type over url + title + meta + ~8k characters, a 512-token deberta would see only the first ~2k characters. bge-m3-zeroshot-v2.0-c (8k, commercially clean) or ModernBERT-large-zeroshot-v2.0 (8k, license ambiguity) fit the input length better.
- A 7-label question costs 7 NLI passes per page. That is acceptable on CPU/ONNX for a base-size model, but GLiClass (below) does it in one pass.
- For a commercial product, the safest NLI choices are the `-c` variants.

### Gaps
- I found no published accuracy for any NLI model on a web-page "page role" task.
- I found no CPU/ONNX latency numbers for these models at 8k tokens.
- I found no primary per-model numbers from BTZSC beyond the headline figures. The abstract-level summary did not list deberta/ModernBERT zeroshot scores.

## GLiClass (Knowledgator) and GLiNER-style universal classifiers

### Takeaway
GLiClass v3 (Apache 2.0 weights, 33M–439M params) scores all labels in one forward pass. Its paper reports that the large variant beats deberta-v3-large-zeroshot-v2.0 on average F1 while being about 4x faster. It degrades far less than NLI as the label count grows. Context is about 1,024 tokens, so long page bodies must be truncated.

### Cited Findings
- The GLiClass-V3 family has five variants: Edge (32.7M), Modern-Base (151M), Modern-Large (399M), Base (187M) and Large (439M). The model cards carry the Apache-2.0 license. — [HF card](https://huggingface.co/knowledgator/gliclass-modern-base-v3.0)
- The paper uses a uni-encoder architecture: text and labels are encoded jointly. Context is limited to about 1,024 tokens. gliclass-large-v3.0 has an average F1 of 0.7193 against 0.6821 for deberta-v3-large-zeroshot-v2.0 (+5.5% relative). Throughput on an A6000 is 25.22 ex/s for GLiClass-Large, against 6.03 for DeBERTa-v3-Large and 10.63 for DeBERTa-v3-Base cross-encoders. Scaling from 1 to 128 labels, Edge drops from 103.81 to 82.64 ex/s, while the DeBERTa-v3-Base cross-encoder drops from 24.55 to 0.47 ex/s. — [arXiv 2508.07662](https://arxiv.org/html/2508.07662)
- Few-shot: with 8 examples per label, the Edge and Modern-Base variants gain about 50% relative F1 and Large gains +0.1063 (+17.1%). Stated limitation: it "struggles with complex scenarios involving logical and semantic constraints". — [arXiv 2508.07662](https://arxiv.org/html/2508.07662)
- Conflicting numbers between sources: the model card reports a 13-dataset average F1 of 0.5571 for modern-base and 0.7001 for large, and 54.46 ex/s for modern-base. The paper reports 0.7193 for large. The difference is probably a different dataset set or run. — [HF card](https://huggingface.co/knowledgator/gliclass-modern-base-v3.0) vs [paper](https://arxiv.org/html/2508.07662)
- License note: the arXiv paper itself is CC BY-NC-ND 4.0. That is the license of the paper text, not the weights, which are Apache-2.0 on HF. — [arXiv](https://arxiv.org/html/2508.07662), [HF](https://huggingface.co/knowledgator/gliclass-modern-base-v3.0)

### Inferences
- GLiClass-modern-base or Edge is the strongest candidate for a cheap CPU pre-labeller for the 7-way page_type. It runs one pass per page regardless of label count.
- The "logical constraints" weakness suggests it is not a good fit for criteria-with-exclusions screening.

### Gaps
- The card and paper summaries do not confirm official ONNX export.
- I did not find CPU latency figures.
- I did not research GLiNER, the entity-extraction sibling, separately. It is a span/NER model, not a document classifier.

## ModernBERT-Large-Instruct, Laya (Convai) and other open "decision models"; SetFit fallback

### Takeaway
ModernBERT-Large-Instruct (Apache 2.0) does zero-shot multiple-choice through its MLM head but is weak in absolute terms. Laya (Convai, Apache 2.0, released 18 Sept 2026) is the open analogue to Jev, but its own card says the base model is near chance zero-shot on typed decisions. It is a base to fine-tune, not a drop-in replacement. SetFit is the proven few-shot fallback at 8 examples per class.

### Cited Findings
- ModernBERT-Large-Instruct: 0.4B, Apache 2.0. It answers a multiple-choice prompt by predicting the answer token at a [MASK] position. Zero-shot MMLU is 43.06% (RoBERTa-Large: 31.30%). The card calls it "a first version" with likely failure cases, and its training data is mainly English and code. — [HF card](https://huggingface.co/answerdotai/ModernBERT-Large-Instruct) (paper: arXiv 2502.03793; not fetched)
- Laya: 421M params (ModernBERT-large, English) and 322M (mmBERT-base, multilingual), Apache 2.0. Context is 512 (English) or 1,024 (multilingual), with "up to 8,192 for long documents". It answers typed `choice`, `score`, `noul` (yes/no) and `action` questions. Zero-shot typed-decisions accuracy is 0.362 (English) and 0.342 (multilingual); the card says "base checkpoints are near chance on typed-decisions zero-shot". Other zero-shot results: XNLI-en 0.860, AG News 0.950. The fine-tuned laya-typed-decisions checkpoint scores 0.766. Latency on a T4 is 32.8–39.5 ms for one question and 72.3–158.6 ms for 10 batched. It supports ONNX (`laya[onnx]`) and CPU. Caveats: accuracy degrades with 50+ choice options; `noul` "can follow its option labels instead of the state"; it ships over-confident (ECE 0.466, falling to 0.081 after temperature calibration). — [HF card](https://huggingface.co/convaiinnovations/laya)
- A secondary source compares Laya and Jev. Jev is a closed, metered API ("$0.042 per million input tokens") with 236–276 ms latency. The 0.362 zero-shot score is "below the 0.461 majority-class baseline". On Banking77, Laya scored 0.425 and Jev 0.870. Jev's 0.727 typed-decisions score and Laya's scores "were never measured in the same run". — [Flowtivity blog (secondary)](https://flowtivity.ai/blog/laya-open-source-jev-alternative/); release date and Apache licensing are corroborated by [AI Weekly](https://aiweekly.co/alerts/convai-ships-laya-a-421m-modernbert-decision-model-apache-20)
- SetFit: with 8 labelled examples per class on Customer Reviews, it is competitive with RoBERTa-Large fine-tuned on the full 3k set. The paper reports that at N=8 it beats standard fine-tuning by 19.3 points on average and is on par with T-Few 3B, and at N=64 it beats T-Few by 5 points while being 27x smaller. — [SetFit GitHub](https://github.com/huggingface/setfit), [arXiv 2209.11055](https://arxiv.org/pdf/2209.11055) (numbers via search snippet of the paper and README; flag as snippet-level)

### Inferences
- Laya's Banking77 result (0.425 vs Jev 0.870) suggests it would not replace Jev zero-shot for page_type. Fine-tuned on Jev's own past page_type answers, it could become a cheap local pre-labeller: Jev acts as teacher and Laya as student, the same pattern as WebOrganizer and FineWeb-Edu.
- Since Jev answers already exist per page, a SetFit model or a logistic-regression head could be trained on them at almost no cost.

### Gaps
- I did not independently verify Laya's CPU latency.
- I found no other open "decision model" releases in Sept 2026 besides Laya.
- I did not fetch the ModernBERT-instruct paper for its classification-specific zero-shot numbers.

## Ready-made web page type classifiers (WebOrganizer, FineWeb-Edu, URL/DOM classifiers, schema.org)

### Takeaway
WebOrganizer's FormatClassifier is the closest off-the-shelf "page role" model. It is a 140M gte-base model with 24 formats, including Product Page, Documentation, Customer Support, About (Org.), Legal Notices and Personal Blog/Knowledge Article. It takes URL + text, and the repo is Apache-2.0. No accuracy figure was found in the card or README. It has no "pricing" or "commercial landing" label. The small Rust XGBoost classifier covers a different 7-type set.

### Cited Findings
- WebOrganizer/FormatClassifier: based on Alibaba-NLP/gte-base-en-v1.5, about 140M params. It has 24 labels: Academic Writing, Content Listing, Creative Writing, Customer Support, Comment Section, FAQ, Truncated, Knowledge Article, Legal Notices, Listicle, News Article, Nonfiction Writing, About (Org.), News (Org.), About (Pers.), Personal Blog, Product Page, Q&A Forum, Spam/Ads, Structured Data, Documentation, Audio Transcript, Tutorial and User Review. The input is `{url}\n\n{text}`. It was distilled in two stages: 1M documents labelled by Llama-3.1-8B, then 100K labelled by Llama-3.1-405B-FP8. The card reports no accuracy. — [HF card](https://huggingface.co/WebOrganizer/FormatClassifier)
- TopicClassifier: 24 topics (e.g. Software Dev., Finance & Business, Health, Travel). There are NoURL variants of both classifiers. — [HF card](https://huggingface.co/WebOrganizer/TopicClassifier), [GitHub](https://github.com/CodeCreator/WebOrganizer)
- The repo license is Apache-2.0. The HF cards I fetched showed no explicit license tag. The training data comes from DCLM RefinedWeb. — [GitHub](https://github.com/CodeCreator/WebOrganizer)
- Label definitions from the paper: Product Page covers "descriptions and promotions for a product or service". Documentation is "meant for developers and experts", unlike Customer Support, which is for "a general audience". Legal Notices covers "terms of service, legal disclaimers, privacy policy". The paper is ICML 2025. Classifier accuracy sits in Appendix B, which I could not retrieve. — [arXiv 2502.10341](https://arxiv.org/html/2502.10341)
- HuggingFaceFW/fineweb-edu-classifier: Snowflake arctic-embed plus a regression head, 0.1B, Apache 2.0. It predicts an educational score from 0 to 5. Binary F1 at a threshold of 3 is 82%, and 6-way accuracy is 71%. It was trained on 450k Llama3-70B annotations with the encoder frozen and only the head trained. — [HF card](https://huggingface.co/HuggingFaceFW/fineweb-edu-classifier)
- Murrough-Foley/web-page-classifier (Rust, MIT/Apache-2.0): 7 types (Article, Forum, Product, Collection, Listing, Documentation, Service). It uses 89 URL/DOM numeric features plus 100 TF-IDF features in an embedded 1.1MB XGBoost model. It reports 87.3% accuracy (macro F1 0.824) and runs in under 1 ms, but it was trained on only 1,497 pages. It has no pricing, legal or about classes and no Python bindings. — [GitHub](https://github.com/Murrough-Foley/web-page-classifier)
- Older research says URL features alone can match or beat full-text classification for some web page tasks. — [Kan, NUS (URL features)](https://www.comp.nus.edu.sg/~kanmy/papers/nustrc8_05.pdf) (via search snippet)

### Inferences
- A rough mapping from WebOrganizer formats to the product's labels: Product Page → product/commercial, Documentation/Customer Support/FAQ/Tutorial → docs/support, Knowledge Article/Personal Blog/Listicle/News → informational, About (Org.) → company, Legal Notices → legal. Pricing and "money landing" have no direct label and would need URL rules (`/pricing`, `/plans`) or Jev.
- Cheap deterministic signals probably resolve a large share of the easy pages before any model runs: URL path patterns (`/blog/`, `/docs/`, `/legal`, `/privacy`, `/terms`, `/about`, `/pricing`) and schema.org JSON-LD `@type` (Product, Article/BlogPosting, FAQPage, AboutPage, Organization). This is my inference; I found no benchmark for it.
- FineWeb-Edu shows that a frozen encoder plus a head trained on LLM labels works at scale. The same recipe applies to training on Jev's labels.

### Gaps
- I found no published accuracy for the WebOrganizer classifiers (Appendix B was not retrieved).
- I found no open dataset or model with an explicit "pricing" or "landing page" role label.
- I did not research schema.org type coverage statistics (e.g. Web Data Commons).

## Decomposing criteria into atomic hypotheses and scoring with NLI: negation/exclusion handling

### Takeaway
The evidence consistently says dense embeddings treat negation as a weak modifier and still match excluded concepts. Cross-encoders do best among retrievers on negation, but only slightly above random on NevIR. NLI catches explicit negation but misses pragmatic contradiction. I found no direct study showing that "decompose criteria into atomic hypotheses and score each with NLI" beats rerankers on exclusions. It is a plausible design, not a proven one.

### Cited Findings
- NevIR: modern IR models do poorly on negation. Cross-encoders perform best but only slightly above random, and all other architectures are worse than random. Adding negation to fine-tuning helps a lot. — [arXiv 2305.07614](https://arxiv.org/pdf/2305.07614)
- E-SENS (arXiv, Aug 2026) describes the failure: because "the excluded concept still appears in the query text, dense retrievers may assign high similarity to documents about that concept". Its fix is training-free. It extracts a "trap query" for the excluded side and subtracts that similarity from the main retrieval score. On ExcluIR, across 4 embedding models, it reduced retrieval of excluded content with a recall/violation trade-off. — [arXiv 2608.30130](https://arxiv.org/abs/2608.30130)
- Negation blindness in universal text embeddings is documented and addressed with a semantic adapter. — [arXiv 2504.00584](https://arxiv.org/pdf/2504.00584)
- A practitioner test found that NLI cross-encoders caught contradictions only when they contained explicit negation, and struggled with pragmatic contradiction. — [DEV Community (secondary)](https://dev.to/midnightgrep/a-110m-parameter-model-instead-of-an-llm-testing-japanese-nli-cross-encoders-on-real-conversation-4k1p) (via search snippet)
- GLiClass reports weakness on "logical and semantic constraints". — [arXiv 2508.07662](https://arxiv.org/html/2508.07662)

### Inferences
- The E-SENS pattern maps directly onto criteria screening, and I think it is the most practical option. Split the description into positive hypotheses and exclusion hypotheses. Score each one *positively*, e.g. "This post is about crypto trading" as an exclusion hypothesis, not "This post is not about crypto". Then compute pass = max(positive) high AND max(exclusion) low. This avoids asking any model to process "not". The same approach works with embeddings (subtract trap similarity), NLI (entailment of the exclusion hypothesis) or a reranker.
- Because an LLM reviews the output, the pre-filter should be tuned for recall on positives. Only drop items where an exclusion hypothesis is strongly entailed.

### Gaps
- I found no head-to-head study of atomic-hypothesis NLI against rerankers or embeddings on exclusion-heavy screening.

## Embeddings + tiny classifier (logistic regression / SetFit) as a near-zero-cost option

### Takeaway
A frozen embedding plus a small head is well supported. BTZSC finds embedding models give the best accuracy/latency trade-off zero-shot. FineWeb-Edu's frozen-encoder-plus-head reaches 82% binary F1. SetFit at 8 examples per class rivals full fine-tuning. The product already stores page embeddings and Jev labels, so this path costs almost nothing extra.

### Cited Findings
- BTZSC: GTE-large-en-v1.5 embeddings give "the best trade-off between accuracy and latency" for zero-shot classification. — [arXiv 2603.11991](https://arxiv.org/abs/2603.11991)
- FineWeb-Edu: encoder frozen, only the classification head trained on 450k LLM labels → 82% binary F1, 71% six-way accuracy. — [HF card](https://huggingface.co/HuggingFaceFW/fineweb-edu-classifier)
- SetFit: at N=8 per class, +19.3 points over standard fine-tuning on average; competitive with RoBERTa-Large trained on 3k examples. — [SetFit GitHub](https://github.com/huggingface/setfit), [arXiv 2209.11055](https://arxiv.org/pdf/2209.11055)
- GLiClass few-shot (8 per label) gives about 50% relative F1 gain for small variants. — [arXiv 2508.07662](https://arxiv.org/html/2508.07662)

### Inferences
- The cheapest pipeline is to reuse the existing page embeddings and fit a logistic regression on pages Jev has already labelled. Send to Jev only the pages where the classifier is not confident (margin below a threshold). This is a standard active-learning/cascade pattern.
- For social and lead screening, per-project criteria change, so a head per criteria set needs labels. Zero-shot NLI or GLiClass with the positive/exclusion split fits better until some reviewed labels exist, and then SetFit can take over.

### Gaps
- I found no published accuracy for logistic regression on frozen embeddings for web page-type labels specifically.
- I found no numbers on how many labels are needed per class for a 7-way page_type at any given accuracy.

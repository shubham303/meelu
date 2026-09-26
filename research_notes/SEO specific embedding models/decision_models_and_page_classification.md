# Small decision / classification models and web page-type classification (as of 2026-09-26)

Repo context (read from code, not the web): the api calls Jev through `api/src/providers/json_data_extractor/openrouter_jev.py`, `POST {openrouter_base_url}/alpha/decisions` with `{"model": "~typesafe/jev-latest", "state": ..., "questions": ...}`, priced locally at `INPUT_USD_PER_MILLION = 0.042`. Page classification (`api/src/site_pages/llm_extraction/questions.py`) asks one `choice` question, `page_type`, over 7 labels (money, hub, informational, support, company, legal, utility), with state = url + title + meta_description + body_text truncated to 8000 chars (roughly 2k tokens), and discards answers below `MIN_CONFIDENCE = 0.7`. The same facade is also called from `site_structure/links/screening.py`, `site_structure/pillars/screening.py` and `seo/screening.py` (the candidate-pipeline middle filter).

## Q1. What exactly are Jev, the "diffusion Gemma decision model", and Laya? Open weights? Licenses?

### Takeaway
Jev is TypeSafe's closed, hosted, non-generative "System One" decision model (v1.13, 32k context, $0.042/M input tokens, output free, no weights or paper). The "diffusion Gemma decision model" is not a Google product but a community pattern ("DiffusionGemma as Jev": OpenJev, djev, a vLLM PR) that runs Google's open Apache-2.0 DiffusionGemma 26B-A4B as a Jev-compatible decision server. Laya is Convai Innovations' open Apache-2.0 421M ModernBERT-large decision model (plus a 322M mmBERT multilingual variant), explicitly pitched as an open Jev alternative. It is weak zero-shot and needs fine-tuning.

### Cited Findings

**Jev (TypeSafe, via OpenRouter)**
- Jev is "a decision model made by TypeSafe", an AI lab founded by Diogo Almeida, Erik Gafni and Sasha Sheng. It launched in early access on 2026-09-15. — [OpenRouter blog: What is Jev?](https://openrouter.ai/blog/insights/what-is-jev/)
- It is non-generative: it "reads your natural language like LLMs do, but then generates no text, no tokens". It is the first of TypeSafe's "System One" models, named after Kahneman's fast thinking. — [OpenRouter blog](https://openrouter.ai/blog/insights/what-is-jev/); [Jev docs](https://openrouter.ai/docs/guides/community/jev)
- It is not open: "TypeSafe hasn't published Jev's weights or a paper on Jev". Everyone calls the same hosted model. No fine-tuning or custom-Jev offering is mentioned. — [OpenRouter blog](https://openrouter.ai/blog/insights/what-is-jev/)
- Primitives:
  - **choice**: pick one option; returns a probability per option plus a confidence.
  - **noul**: yes/no; returns P(yes).
  - **score**: ordered scale, max 10 levels; returns a probability-weighted position.
  - Confidence measures how concentrated the distribution is, and the docs describe the probabilities as calibrated.
  — [Jev docs](https://openrouter.ai/docs/guides/community/jev); [OpenRouter blog](https://openrouter.ai/blog/insights/what-is-jev/)
- Endpoints: `POST https://openrouter.ai/api/alpha/decisions` and `POST https://openrouter.ai/api/v1/systemone`. Context is 32,000 tokens. Model IDs are `typesafe/jev-1.13` and the alias `~typesafe/jev-latest`. Responses include `usage.cost` in USD. — [Jev docs](https://openrouter.ai/docs/guides/community/jev)
- Pricing is $0.042 per million input tokens, and output is free. — [Jev 1.13 model page](https://openrouter.ai/typesafe/jev-1.13); [OpenRouter blog](https://openrouter.ai/blog/insights/what-is-jev/)
- OpenRouter lists 3 TypeSafe models: Jev 1.13, Jev Latest, and Jev Router. Jev Router, listed 2026-09-25, is a cache-aware model router built on Jev with up to 1M context. — [TypeSafe provider page](https://openrouter.ai/provider/typesafe) (via search snippet); [OpenRouter on X](https://x.com/OpenRouter/status/2103610898690855161) (snippet)
- The Jev Lab demo shows batch timings, not per-call latency. Examples: "475 answers in 1.2 s" (message triage), "40 posts in 0.5 s" (feed filtering), "8 answers in 300 ms". It publishes no benchmark or calibration numbers. — [Jev Lab](https://openrouter.ai/labs/jev)
- A third-party write-up measured Jev latency at 236–276 ms per call. — [AI Weekly on Laya](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at); [eesel](https://www.eesel.ai/blog/laya-ai)
- Jev 1.13.0 scored 86.6% (200/231) on the public "JevBench" questions. — [OpenJev README](https://github.com/razorback16/openjev); search snippet from [awesome-jev issue #15](https://github.com/heyjunpenn/awesome-jev/issues/15)
- Architecture and parameter count are undisclosed. I found no source for either.

**"Diffusion Gemma decision model" = DiffusionGemma run in the Jev paradigm**
- DiffusionGemma is a Google DeepMind open-weights model built on the Gemma 4 26B-A4B MoE (26B total, 4B active). It generates by discrete text diffusion with "block-autoregressive multi-canvas sampling" (256-token blocks). Details:
  - Inputs are text, images and video; output is text only.
  - License is Apache 2.0.
  - It fits in about 18 GB of VRAM when quantized.
  - At most 48 denoising steps are recommended.
  - It is described as optimized for single-user local deployment over high-concurrency cloud serving.
  - Google's overview does not mention decision or classification use.
  — [Google AI for Developers: DiffusionGemma overview](https://ai.google.dev/gemma/docs/diffusiongemma); [HF: google/diffusiongemma-26B-A4B-it](https://huggingface.co/google/diffusiongemma-26B-A4B-it); [DeepMind page](https://deepmind.google/models/gemma/diffusiongemma/)
- Google's claimed throughput is "up to 4x faster" token output and ">1,000 tokens/s on a single H100". — search snippet summarizing [DeepMind](https://deepmind.google/models/gemma/diffusiongemma/) / [MindStudio](https://www.mindstudio.ai/blog/diffusion-language-models-google-diffusion-gemma-explained). I did not verify this on the primary page.
- The @googlegemma account amplified "DiffusionGemma as Jev". Its claims: it evaluates structured choices "in a single parallel pass", and bidirectional attention lets every option attend to the full context, "yielding well-calibrated decision distributions". This is a marketing claim with no numbers. — [Google Gemma on X](https://x.com/googlegemma/status/2101069861598482817) (search snippet only; the page returned 402)
- **OpenJev** (razorback16) is an Apache-2.0 server compatible with Jev's wire protocol (`POST /v1/systemone`; `/alpha/decisions` is not mentioned).
  - Method: it builds a canvas in which only the answer slots are masked, one token per question. It runs one denoising pass and reads the logits of the label tokens (yes/no, A/B/C, 0/1/2).
  - Confidence = 1 − H(p)/ln K. When entropy is above 0.1 it re-reads with other noise seeds and averages.
  - Hardware: 24 GB+ VRAM, tested on an RTX PRO 6000 Blackwell. It also runs on Apple Silicon via MLX (about 16 GB; 0.2–0.4 s per 3-question request on an M3 Ultra).
  - Speed: about 31 ms for one 3-question request, and 57.4 req/s at 64 concurrency with 760 ms median latency.
  - The README also mentions a "JevK5" model, a LoRA distilled from Qwen3.6-27B and merged, that matched Jev's top answer on all 231 JevBench items (86.6%).
  - Its license list covers weights for DiffusionGemma, Laya (Convai) and "Verdict" (Heman10x), so it appears to support several backends.
  - No fine-tuning or LoRA workflow for DiffusionGemma itself is documented.
  — [OpenJev GitHub](https://github.com/razorback16/openjev)
- Other implementations:
  - **djev** (mmastrac) is the example server from vLLM PR 57250.
  - **ThakiCloud** describes "fix answer positions in the diffusion canvas, then one parallel denoise pass" on vLLM and says "no independent benchmark yet" exists. Its hardware numbers (about 18 GB, about 1k tok/s on an H100) are flagged as unverified.
  — [djev GitHub](https://github.com/mmastrac/djev); [ThakiCloud blog](https://thakicloud.com/tech-blog/en/dev/diffusiongemma-jev-vllm/)
- A local DiffusionGemma run scored 84.8% (196/231) on public JevBench vs 86.6% (200/231) for Jev 1.13.0. — search snippet attributed to [awesome-jev issue #15 "Diffusion Jev"](https://github.com/heyjunpenn/awesome-jev/issues/15) (not fetched). Another snippet (MindStudio/X) says DiffusionGemma-as-Jev "comes out ahead", but that is self-reported.
- A free hosted demo endpoint exists: [HF Space victor/DiffusionGemma-free-endpoint](https://huggingface.co/spaces/victor/DiffusionGemma-free-endpoint).
- Fine-tuning: the Google overview links [google/hackable_diffusion](https://github.com/google/hackable_diffusion) as the repository but does not detail LoRA or fine-tuning frameworks. — [Google overview](https://ai.google.dev/gemma/docs/diffusiongemma)

**Laya (Convai Innovations)**
- Maker and license: Convai Innovations (founder Nandakishor Mukkunnoth) released it on 2026-09-19 under Apache 2.0. There are three checkpoints on HF (`convaiinnovations/laya`, `laya-multilingual`, ...), also on ModelScope. It installs with `pip install laya`. — [AI Weekly](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at); [eesel](https://www.eesel.ai/blog/laya-ai); [ModelScope](https://www.modelscope.cn/models/convaiinnovations/laya)
- Architecture:
  - English: 421M parameters on a ModernBERT-large encoder (about 395M), with **512-token context**, a two-layer decision head, option-marker / `[MASK]` scoring, and an act/escalate component.
  - Multilingual: 322M on mmBERT-base, with 1024 context and 100+ languages.
  - It uses the same choice / score (0–3) / noul primitives as Jev.
  — [AI Weekly](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at); [eesel](https://www.eesel.ai/blog/laya-ai)
- Latency on a Tesla T4: 39.5 ms (English) and 32.8 ms (multilingual). The vendor claims this is "7.8x faster" than Jev's 236–276 ms. — [AI Weekly](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at)
- Accuracy (author's own benchmarks):
  - Typed-decisions zero-shot is **0.362** (random is 0.318); the multilingual model scores 0.352.
  - After fine-tuning on that benchmark's own training split, it reaches **0.766** vs Jev 1.13.0 at 0.727 (and above a 0.735 teacher ceiling).
  - Spam 0.993, phishing 0.980, jailbreak 0.755–0.762, 10-way ticket routing 0.522, RAG relevance 0.657.
  - It degrades past about 20 options: Banking77 scored 0.425 vs Jev's 0.870.
  — [eesel](https://www.eesel.ai/blog/laya-ai); [AI Weekly](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at)
- Calibration: raw ECE is 0.466, falling to 0.081 after refitting temperature per question type. The claimed "3x better calibration than Jev" (0.081 vs 0.246) compares Laya after recalibration. It is trained with "RLCD" (RL against strictly proper scoring rules). — [AI Weekly](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at); [eesel](https://www.eesel.ai/blog/laya-ai)
- Community tooling: a browser build ([layaForWeb](https://vishalmysore.github.io/layaForWeb/)) and a GPU-VPS self-host tutorial ([LumaDock](https://lumadock.com/tutorials/run-laya-jev-alternative-gpu-vps)) exist.

### Inferences
- Both "alternatives" share Jev's interface (state + typed questions → probabilities), so the existing `JsonDataExtractorAdapter` abstraction can host either as a fallback or replacement adapter with little change. OpenJev already speaks the Jev wire protocol.
- Laya English's 512-token context is below the ~2k tokens the page classifier currently sends (8000-char body). Either the input gets truncated, or the multilingual 1024-context variant or a long-context ModernBERT (8k native) fine-tune is needed.
- Laya's near-random zero-shot score means it is not a drop-in replacement. It is a fine-tuning starting point. Its reported strength on binary tasks (spam/phishing ≥0.98) and weakness past ~20 options fit our shape well: one 7-way choice plus binary yes/no screens.
- DiffusionGemma-as-Jev is the closest open match to Jev's zero-shot generality (84.8% vs 86.6% on JevBench). The cost is a 26B-A4B model on a 24 GB+ GPU, which is much heavier than an encoder.

### Gaps
- Jev's architecture, parameter count, training data and full JevBench results are unpublished. The JevBench dataset itself was not located.
- The Laya numbers are vendor-reported or come from secondary blogs. I did not fetch the HF model card directly. I found no independent replication.
- The DiffusionGemma release date and the primary throughput benchmark were not captured. I did not open the awesome-jev "Diffusion Jev" issue, so the 84.8% figure rests on a search snippet.
- No source documents LoRA fine-tuning of DiffusionGemma for decisions.

## Q2. For binary or multi-choice decisions over ~1–2k tokens, fine-tuned encoders vs fine-tuned small LLMs vs zero-shot big LLMs?

### Takeaway
With a few hundred to a few thousand labels, fine-tuned encoders (ModernBERT / Ettin / DeBERTa-v3 class) match or beat zero-shot frontier LLMs on classification. They do so at 1–10x lower latency and 100–400x lower cost, and the gap is largest on domain-specific label definitions like ours. Decoder LLMs with LoRA add flexibility, not accuracy. Diffusion LMs are an interesting zero-shot option but have no published fine-tuning evidence. Whatever the model, raw scores need temperature calibration on held-out data before a confidence threshold (like our 0.7) means anything.

### Cited Findings
- **Cost-aware study (2026).** Setup: fine-tuned BERT/RoBERTa/DistilBERT vs GPT-4o and Claude Sonnet 4.5 zero- and few-shot. Macro-F1 results:
  - AG News: RoBERTa 94.63 vs Claude ZS 91.35.
  - DBPedia: 99.40 vs 98.83.
  - SST-2: tie.
  - IMDB: Claude few-shot wins by 1.64.
  - Encoders were 1–10x faster at p50.
  - Encoders were 100–400x cheaper per 1M predictions (e.g. DistilBERT $5–12 vs Claude FS $600–2,700).
  - The authors conclude encoders should be the "decision engines" and LLMs complementary. — [arXiv 2602.06370](https://arxiv.org/html/2602.06370v1)
- **Specialized tasks.** Fine-tuned RoBERTa/DeBERTa-v3/ELECTRA (125–435M) beat zero-shot GPT-4 and Claude 3 Opus on all four tasks:
  - Stance: DeBERTa-v3 0.94 F1 vs GPT-4 0.51.
  - EU positions: 0.91 vs 0.45.
  - Sentiment: 0.92 vs 0.87.
  - Performance "begins to saturate after around 200 labels"; the optimum is 200–500 labels. — [arXiv 2406.08660](https://arxiv.org/html/2406.08660v1)
- **Encoder vs decoder at equal training.** Ettin trained paired encoders and decoders (17M–1B) on identical data (2T tokens) and recipes. A 150M encoder beats a 400M decoder on MNLI (89.2 vs 88.2). Converting one architecture into the other underperforms native models. — [HF blog: Ettin](https://huggingface.co/blog/ettin); [arXiv 2507.11412](https://arxiv.org/pdf/2507.11412); [GitHub](https://github.com/jhu-clsp/ettin-encoder-vs-decoder)
- **ModernBERT-Large-Instruct** (a generative classifier through the MLM head) is a strong zero-shot classifier. It reaches 93% of Llama-3.2-1B's MMLU with 60% fewer parameters. When fine-tuned, MLM-head classification matches or beats a classification head. — [Answer.AI](https://www.answer.ai/posts/2025-02-10-modernbert-instruct.html); [arXiv 2502.03793](https://arxiv.org/html/2502.03793v1)
- **Zero-shot encoder option.** GLiClass (Knowledgator) is a zero-shot classifier that scores text plus arbitrary labels in a single forward pass on a BERT-like encoder. There are ModernBERT-based v2/v3 checkpoints. It is presented as cheaper than per-label cross-encoders and LLMs. Cost is flat up to about 8–16 labels. — [GLiClass docs](https://docs.knowledgator.com/docs/frameworks/gliclass/); [HF gliclass-modern-base-v3.0](https://huggingface.co/knowledgator/gliclass-modern-base-v3.0); [gliclass-infer](https://github.com/srimon12/gliclass-infer)
- **Zero-shot benchmark.** BTZSC compares cross-encoders, embedding models, rerankers and LLMs for zero-shot text classification. — [arXiv 2603.11991](https://arxiv.org/html/2603.11991) (not fetched; I have no numbers)
- **Calibration.** Laya's raw ECE was 0.466 before per-question-type temperature refit (0.081 after). This shows even purpose-built decision heads need post-hoc calibration. — [AI Weekly](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at)
- **Distillation recipe.** WebOrganizer distilled Llama-3.1-8B labels (1M docs), then Llama-3.1-405B labels (100K docs), into a 140M gte-base encoder for page-format classification. This is the "LLM teacher → small encoder student" recipe at web scale. — [HF WebOrganizer/FormatClassifier](https://huggingface.co/WebOrganizer/FormatClassifier); [arXiv 2502.10341](https://arxiv.org/abs/2502.10341)

### Comparison of candidate architectures for a self-trained decision model (synthesis)
| | Encoder classifier (ModernBERT-base/large, Ettin 150–400M, DeBERTa-v3, mmBERT) | Small decoder LLM + LoRA (Qwen3 0.6–4B, Gemma 3, SmolLM3, Llama 3.2 1–3B, LFM2), read logprob of one label token | Diffusion LM (DiffusionGemma 26B-A4B via OpenJev/djev; LLaDA/Dream) |
|---|---|---|---|
| Accuracy evidence | Matches or beats zero-shot frontier LLMs after 200–500+ labels ([2406.08660](https://arxiv.org/html/2406.08660v1), [2602.06370](https://arxiv.org/html/2602.06370v1)). Encoder > decoder at equal size ([Ettin](https://huggingface.co/blog/ettin)) | No direct source fetched this session | 84.8% vs Jev 86.6% zero-shot on JevBench ([snippet](https://github.com/heyjunpenn/awesome-jev/issues/15)) |
| Latency / throughput | ~33–40 ms per call on a T4 at 421M ([Laya](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at)) | Not measured here; one prefill pass plus one token | ~31 ms single request; 57 req/s at 64 concurrency on an RTX PRO 6000 ([OpenJev](https://github.com/razorback16/openjev)) |
| Hardware | CPU or T4-class | Consumer GPU | 24 GB+ GPU or 16 GB on MLX ([OpenJev](https://github.com/razorback16/openjev)) |
| Zero-shot | Poor unless instruct/GLiClass-style ([Laya 0.362](https://www.eesel.ai/blog/laya-ai)) | Moderate | Strongest open option found |
| Fine-tuning | Cheapest; standard HF recipe | LoRA; moderate cost | Not documented |
| Context | 512 (Laya EN) to 8k (ModernBERT) | Long | Long |
| Calibration | Needs temperature refit ([Laya ECE 0.466→0.081](https://aiweekly.co/alerts/convai-ships-laya-a-non-autoregressive-multilingual-system-1-decision-model-at)) | Needs temperature refit | Entropy-based confidence plus re-read ([OpenJev](https://github.com/razorback16/openjev)) |

### Inferences
- For our fixed question set (a 7-way page_type plus a few binary screens), the evidence favors distilling Jev's (or a frontier LLM's) answers on our own crawled pages into a ModernBERT-base/large or Ettin-400M classifier, following the WebOrganizer recipe. Use one head per question, or an option-marker head like Laya's. Pros: CPU-cheap, calibratable, fast.
- The candidate-pipeline yes/no filter differs, because the question text changes per pipeline. Its best fit is a cross-encoder / reranker-style binary head trained on (candidate, criterion) pairs, or a GLiClass/Laya-style model that takes the question as input.
- For high recall, set the threshold on P(yes) from a calibrated held-out recall target instead of reusing a fixed 0.7 confidence. Note that Jev "confidence" is distribution concentration, not P(correct).
- Keep Jev (or OpenJev on DiffusionGemma) as the teacher and fallback for questions with no training data.

### Gaps
- I fetched no primary sources this session for Qwen3 0.6–4B, Gemma 3/3n, SmolLM3, Phi-4-mini, Llama 3.2, LFM2, NeoBERT, DeBERTa-v3 model cards, SetFit, LLaDA, Dream, Mercury or Gemini Diffusion. Their sizes, licenses and benchmarks should be verified before citing.
- I found no head-to-head study of LoRA-tuned 1–4B decoders vs fine-tuned encoders on ~2k-token web pages.
- I found no published fine-tuning results for diffusion LMs used as classifiers.
- There are no GPU-hour or cost figures for fine-tuning each option.

## Q3. What datasets and models exist for web page type / genre / format classification?

### Takeaway
The closest ready-made asset is WebOrganizer's FormatClassifier: 24 page-format labels, a 140M gte-base encoder, input = URL line plus text, and Llama-distilled training labels. Its taxonomy covers "Product Page", "About (Org.)", "Legal Notices", "Documentation", "FAQ", "Customer Support", "Content Listing", "Knowledge Article", "Tutorial" and more. It maps onto most of our 7 page types but has no explicit pricing, landing or utility (cart/login/search) class. Classic web-genre corpora (KI-04, 7-Genre, CORE/X-GENRE) are small or old but include "shop" and "help" genres. Product-category datasets classify what a site sells, not the page's role.

### Cited Findings
- **WebOrganizer** (Wettig, Lo, Min, Hajishirzi, Chen, Soldaini) organizes web pages by topic and format. Its classifiers are distilled from LLM annotations into efficient models. — [arXiv 2502.10341](https://arxiv.org/abs/2502.10341); project page weborganizer.allen.ai
  - FormatClassifier details: base model Alibaba-NLP/gte-base-en-v1.5 (140M). Input is `{url}\n{text}`. Training was two-stage, first on FormatAnnotations-Llama-3.1-8B (1M docs), then on FormatAnnotations-Llama-3.1-405B-FP8 (100K docs), and both annotation sets are on HF. The card gives no accuracy or license. — [HF WebOrganizer/FormatClassifier](https://huggingface.co/WebOrganizer/FormatClassifier)
  - The 24 formats: Academic Writing, Content Listing, Creative Writing, Customer Support, Comment Section, FAQ, Truncated, Knowledge Article, Legal Notices, Listicle, News Article, Nonfiction Writing, About (Org.), News (Org.), About (Pers.), Personal Blog, Product Page, Q&A Forum, Spam/Ads, Structured Data, Documentation, Audio Transcript, Tutorial, User Review. — [HF FormatClassifier](https://huggingface.co/WebOrganizer/FormatClassifier)
- **KI-04 (Webis):** 1,239 pages in 8 genres: article, download, link collection, private portrayal, non-private portrayal, discussion, help, shop. — [Webis Genre-KI-04](https://webis.de/data/genre-ki-04.html)
- **7-Web-Genre:** 1,400 pages collected in 2005, 7 balanced genres. — search snippet via [genre identification survey](https://d-nb.info/1317885295/34)
- **CORE and X-GENRE:** CORE (Egbert et al. 2015) is the basis of most modern genre datasets. X-GENRE merges FTD and CORE into a 9-label multilingual classifier used to annotate web corpora. — [CLASSLA-web arXiv 2403.12721](https://arxiv.org/pdf/2403.12721); [ACL nlp4dh 2024](https://aclanthology.org/2024.nlp4dh-1.38/)
- **URL-only genre classification** is an established line of work (segment-weighted URL features). — [SciELO: URL-based genre classification](https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S1870-90442016000100043)
- **Site-topic datasets**, which are not page-role datasets:
  - Kaggle, 1.5M URLs × 15 categories. — [Kaggle](https://www.kaggle.com/datasets/shaurov/website-classification-using-url)
  - Zenodo, 2,648 sites × 7 topical categories. — [Zenodo 15828693](https://zenodo.org/records/15828693)
  - E-commerce-or-not plus product-type subsets. — [ceur-ws Vol-1710](https://ceur-ws.org/Vol-1710/paper23.pdf)
  - A "comprehensive webpage classification dataset". — [ca-roll PDF](https://ca-roll.github.io/downloads/A_Comprehensive_Dataset_for_Webpage_Classification.pdf)
- **Graph and structure features:** GROWN+UP pre-trains a graph representation of a webpage network. This is relevant to using link-graph and DOM structure beyond text. — [arXiv 2208.02252](https://arxiv.org/pdf/2208.02252)

### Inferences
- Suggested mapping from WebOrganizer formats to our types:
  - Product Page → money.
  - Content Listing → hub.
  - Knowledge Article / Tutorial / Listicle / News / Personal Blog → informational.
  - FAQ / Documentation / Customer Support → support.
  - About (Org./Pers.) / News (Org.) → company.
  - Legal Notices → legal.
  - Missing classes: pricing, landing/home, and utility (login, cart, search, pagination). These must come from our own labels or from rules.
- Its `url\ntext` input convention supports adding URL as a feature. Cheap non-text signals worth feeding as prefixed text or side features:
  - URL path tokens (`/pricing`, `/product/`, `/category/`, `/blog/`, `/docs/`, `/privacy`, `/cart`, `?page=`).
  - schema.org `@type` (Product, Offer, CollectionPage, BlogPosting/Article, FAQPage, AboutPage, ContactPage).
  - Link-density or outlink-to-text ratio (hub pages).
  - Presence of forms, price patterns and CTAs.
  - Crawl-graph features such as internal PageRank, which the repo already computes in `site_pages/pagerank.py`.
  - These feature ideas are mine and not validated by a fetched source.
- Practical bootstrap: label a few thousand crawled pages with Jev (keeping only high-confidence answers), plus a small hand-checked set. Fine-tune an encoder on `url + title + meta + schema types + body` and calibrate on the hand-checked set.

### Gaps
- I found no public dataset labelled with SEO page roles (money / category / pricing / landing / utility).
- I did not fetch or verify the DCLM fastText classifier, the FineWeb-Edu classifier, Curlie/DMOZ, or the Web Data Commons schema.org extraction.
- WebOrganizer FormatClassifier accuracy and license were not on the model card; check the paper's appendix.

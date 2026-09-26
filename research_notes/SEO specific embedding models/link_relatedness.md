# Link-worthiness / asymmetric relatedness between documents ("should page A link to page B")

Framing used throughout: the task is directed link prediction on a document graph. It has three parts that the literature treats separately:
(a) **anchor-level entity linking / wikification**: a phrase in A should point to B. Wikimedia "Add a link" and InLinks work this way.
(b) **document-level relatedness learned from links or citations**: A and B are "linked-kind-of-related", which is not the same as "similar". SPECTER/SPECTER2, SciNCL, LinkBERT, HLP, Anchor-DR and the "see also" work belong here.
(c) **graph link prediction**: node2vec/DeepWalk/GNN over the existing link graph, optionally with text features.

## Q1. What is the best open model/approach today for directional document relatedness, and what supervision signal was it trained on?

### Takeaway
No single open model is trained directly for "should A link to B" on general websites. The strongest open building blocks are (1) citation- or hyperlink-supervised embedders (SPECTER2 proximity adapter, SciNCL, LinkBERT, HLP, Anchor-DR), whose supervision signal is "A cited or linked B", and (2) instruction-tuned embedders and rerankers (Qwen3-Embedding / Qwen3-Reranker, Apache-2.0), which let you state the directional relation in the query instruction. The one production system with published precision and recall, Wikimedia's Add-a-link, is not a neural embedder. It is an anchor dictionary plus a 7-feature XGBoost classifier.

### Cited Findings
- **SPECTER2** (AllenAI): Apache 2.0. The base model was trained on "over 6M triplets of scientific paper citations" (query, positive, negative). Adapters were then trained on 8 SciRepEval tasks with 600K more citation triplets. Adapters: Proximity (retrieval and link prediction), Adhoc Query, Classification, Regression. It is built on SciBERT, and SPECTER2-Adapters score 71.1 average on SciRepEval. — [HF allenai/specter2_base](https://huggingface.co/allenai/specter2_base)
- The supervision signal is citations: a paper and a paper it cites form a positive pair. Other SPECTER2 variants: `allenai/specter2`, `specter2_classification`, `specter2_regression`. — [HF allenai/specter2](https://huggingface.co/allenai/specter2); [GitHub allenai/specter](https://github.com/allenai/specter)
- **SciNCL** (EMNLP 2022): it samples contrastive positives and negatives by nearest neighbours in a *citation-graph embedding* space rather than using raw citations. This gives "continuous similarity", hard negatives, and a controlled margin that prevents positive/negative collisions. It scores 81.8 avg on SciDocs, +1.8 over SPECTER, and still +1.7 when trained without leakage. It is best on all user-activity and citation tasks. Even a general-domain LM trained this way beats in-domain pretrained baselines. — [arXiv 2202.06671](https://arxiv.org/abs/2202.06671); [GitHub malteos/scincl](https://github.com/malteos/scincl)
- SciRepEval comparison: SciNCL scores 55.6 in-train, 57.8 out-of-train and 69.0 avg, below SPECTER2 variants. — [HF specter2_classification card](https://huggingface.co/allenai/specter2_classification)
- **LinkBERT** (ACL 2022, Yasunaga et al.): it treats the corpus as a graph of documents and puts linked documents in the same LM context. Objectives: MLM plus *document relation prediction*, a classification of whether segment B is contiguous with, random to, or linked from segment A. Pretrained on Wikipedia hyperlinks (general) and PubMed citations (BioLinkBERT). Reported gains: +5% absolute on HotpotQA and TriviaQA, and +7% on BioASQ and USMLE. Code is Apache-2.0. Models: LinkBERT-base/large and BioLinkBERT-base/large. — [arXiv 2203.15827](https://arxiv.org/abs/2203.15827); [GitHub michiyasunaga/LinkBERT](https://github.com/michiyasunaga/LinkBERT)
- **HLP, Hyperlink-induced Pre-training** (ACL 2022, Zhou et al.): it builds pseudo query-passage pairs from Wikipedia hyperlink topology using "dual-link" (A links B and B links A) and "co-mention" structures. It trains a BERT bi-encoder with in-batch negatives. Zero-shot, it beats BM25 by up to 7 points and other pretraining methods by more than 10 points in top-20 retrieval accuracy. — [arXiv 2203.06942](https://arxiv.org/abs/2203.06942); [ACL Anthology](https://aclanthology.org/2022.acl-long.493/)
- **PHP, Progressive Hyperlink Prediction**: it sorts document pairs into four levels: no link, unidirectional link, symmetric link, and "highly relevant symmetric link". It trains by contrasting adjacent levels, and beats earlier pretraining methods on 2 ad-hoc retrieval and 6 QA datasets. The graded levels are directly usable as graded link-worthiness labels. — [arXiv 2209.06583](https://arxiv.org/abs/2209.06583)
- **Qwen3-Embedding**: Apache 2.0. The query side takes a one-sentence instruction, `Instruct: {task}\nQuery:{query}`, and leaving it out lowers performance. The companion Qwen3-Reranker also takes user-defined instructions. — [Qwen blog](https://qwenlm.github.io/blog/qwen3-embedding/); [arXiv 2506.05176](https://arxiv.org/html/2506.05176v1); [HF Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)

### Inferences
- SPECTER2 and SciNCL are trained on scientific titles and abstracts. On commercial or blog web pages they will likely transfer poorly. Their *recipe* is what transfers: triplets from a link graph, and hard negatives sampled via graph-embedding neighbourhoods (SciNCL). You could apply that recipe to a site's own internal link graph or to Common Crawl.
- Neither citation nor hyperlink supervision is fully directional in these models. SPECTER, SciNCL and HLP use symmetric bi-encoder scores. LinkBERT's relation-prediction head and PHP's unidirectional-versus-symmetric levels are the closest to modelling direction. True directionality ("A should link to B", not the reverse) is easiest to get from a cross-encoder or reranker on the ordered pair (source passage, target page), or from an instruction-conditioned query embedding.
- Qwen3-Embedding instruction prompting is a cheap, untested way to encode asymmetric relations. Examples: "Given an article, retrieve the pages a reader would need as background (prerequisite)", and "Given a how-to article, retrieve the product or service page it should link to". Each relation type becomes a separate query embedding of the source page against one shared document index. That multiplies recall paths at no extra indexing cost.

### Gaps
- I found no public benchmark that measures whether instruction prompts make Qwen3-Embedding, gte-Qwen or e5-instruct retrieve *link-worthy but dissimilar* pages. This needs an internal eval.
- I did not verify the exact licences of the SciNCL or HLP checkpoints. The HLP code and model licence also still need checking.
- I found no open model trained specifically on general-web *internal* links. Anchor-DR (below) uses *cross-domain* anchors only.

## Q2. Can hyperlinks from the open web (Common Crawl) be free supervision for a "should link" model? How were navigational links filtered?

### Takeaway
Yes, with caveats. Anchor-DR (SIGIR 2023) trained an unsupervised dense retriever on web anchor-to-document pairs. It filtered out navigational and functional anchors and beat prior unsupervised retrievers. However, it deliberately **dropped in-domain (same-site) anchors**, which are exactly the internal links this product cares about. Internal-link supervision from the web therefore needs its own boilerplate filtering.

### Cited Findings
- **Anchor-DR**: a contrastive task that matches anchor text to the linked document. Its filters: (1) remove in-domain anchors, where source and target share a domain; (2) remove header and footer anchors, detected by HTML tags; (3) remove anchors containing functional keywords (for example "homepage"); (4) train a lightweight query classifier to keep only anchors that resemble search queries. Result: +5.3% NDCG@10 on MS MARCO over the prior unsupervised dense retrieval state of the art. — [arXiv 2305.05834](https://arxiv.org/abs/2305.05834); [ACM DL](https://dl.acm.org/doi/10.1145/3539618.3592080)
- Anchor text has long been used to simulate queries and build query-document pairs for IR pretraining. — [PHP, arXiv 2209.06583](https://arxiv.org/abs/2209.06583)
- HLP only uses the structurally strongest link patterns (dual links and co-mentions) rather than every link, which is itself a noise filter. — [arXiv 2203.06942](https://arxiv.org/abs/2203.06942)

### Inferences
- A practical recipe for internal-link supervision from Common Crawl WAT/WARC:
  1. Keep only links inside the main-content region. Use a boilerplate remover such as trafilatura or readability, or DOM `<nav>/<header>/<footer>/<aside>` tags as Anchor-DR did.
  2. Drop links that appear on more than about 30–50% of a site's pages; these are template links.
  3. Drop functional anchors ("read more", "click here", "home", pagination).
  4. Keep in-body contextual links as positives, and use the surrounding sentence as the "source passage".
  5. Use as hard negatives pages from the same site that are semantically similar to the target but *not* linked, following SciNCL's margin idea.
- Links on the web are noisy positives, and a missing link is only a weak negative: most link-worthy pairs are simply never linked. Treat labels as positive-unlabeled. PHP's graded levels suggest weighting reciprocal links higher.
- The in-domain restriction in Anchor-DR means its released checkpoint (if any) is tuned for external query-like anchors, not internal navigation. It is still a useful anchor-to-page scorer.

### Gaps
- I did not find a published dataset of cleaned *internal* contextual links from Common Crawl, and I did not verify numbers for ClueWeb22 anchor text or MS MARCO Web Search anchor data in this pass.
- I did not verify whether an Anchor-DR checkpoint or code was released, or under which licence.

## Q3. How does Wikimedia's Add-a-link model work and what precision/recall did it get?

### Takeaway
It is a lightweight, per-language pipeline. An anchor dictionary built from existing links generates (mention, candidate target) pairs. An XGBoost classifier with 7 simple features scores each pair, and hard-coded filters remove bad target classes. English Wikipedia got about 81% precision and 45% recall at threshold 0.5. Most wikis reach 70–80% precision with recall around 40% or more, and the deployment bar is 75% precision. Code is open (research-mwaddlink). Newer "V2" models are language-agnostic.

### Cited Findings
- **Candidate generation**: an anchor dictionary maps every existing link's anchor to its targets across all articles. Preprocessing: title normalisation, redirect resolution, main namespace only, and lowercased anchors. Anchors whose *link probability* is below 6.5% are dropped, which removes words like "and". — [Meta research page](https://meta.wikimedia.org/wiki/Research:Link_recommendation_model_for_add-a-link_structured_task)
- **Features (XGBoost, default params)**: n-gram length of the anchor; frequency of the anchor-target pair; ambiguity (number of candidate targets); kurtosis of the candidate distribution; Levenshtein distance between anchor and target title; Wikipedia2Vec (50-d) embedding distance between source and target; and navigation distance from reader co-occurrence, later removed as negligible. — [Meta research page](https://meta.wikimedia.org/wiki/Research:Link_recommendation_model_for_add-a-link_structured_task)
- **Training data**: a "gold" set built from sentences that already contain links, yielding positive and negative anchor-link pairs. — same source
- **Backtest (2021-06, threshold 0.5)**:

  | Wiki | Precision | Recall |
  |---|---|---|
  | enwiki | 81.3% | 45.0% |
  | arwiki | 75.4% | 30.2% |
  | bnwiki | 73.6% | 28.0% |
  | cswiki | 76.4% | 43.5% |
  | viwiki | 88.8% | 63.3% |

  Others (ru, fr, pl, …) reach about 80% precision with recall above 40%. — same source
- **Hard-coded filters**: no links to disambiguation pages, lists, years or decades, or units of measurement. Later tickets add "do not link" rules for country names (Q6256) and for country and continent names. — [Meta](https://meta.wikimedia.org/wiki/Research:Link_recommendation_model_for_add-a-link_structured_task); [T386867](https://phabricator.wikimedia.org/T386867); [T414297](https://phabricator.wikimedia.org/T414297)
- **Paper**: Gerlach, Miller, Ho, Harlan, Difallah, "A Multilingual Entity Linking System for Wikipedia with a Machine-in-the-Loop Approach", CIKM 2021. — [arXiv 2105.15110](https://arxiv.org/abs/2105.15110)
- **Code**: [github.com/wikimedia/research-mwaddlink](https://github.com/wikimedia/research-mwaddlink). The meta page is CC BY-SA; I did not verify the licence of the code itself.
- **V2**: a language-agnostic model, with supported wikis listed at analytics.wikimedia.org/published/wmf-ml-models/addalink/v2/. The deployment threshold is 0.75 precision, and most wikis reach 70–80% precision at about 40% or more recall. — [T404460](https://phabricator.wikimedia.org/T404460); [T410469](https://phabricator.wikimedia.org/T410469)
- **Product impact (enwiki A/B test, rolled out from Nov 2024; 2% to 20% by Mar 2025)**: on mobile web, constructive activation +33.7%, constructive retention +3.7%, revert rate −19.6%. — [Wikimedia A/B report](https://analytics.wikimedia.org/published/reports/growth/add_a_link_enwiki_ab_test_report.html); [T382603](https://phabricator.wikimedia.org/T382603)

### Inferences
- Wikimedia chose to **trade recall for precision**: about 45% recall is accepted so that suggestions shown to humans are about 80% correct. That fits the user's final "LLM review on a small set" stage.
- The architecture maps cleanly onto a site. The anchor dictionary is built from the site's own existing internal-link anchors plus each page's title, H1 and target keywords (from GSC queries). The candidate target is the page those anchors point to. Cheap features: anchor frequency, ambiguity, Levenshtein distance to title, and embedding distance. This yields **anchor-level** candidates that cosine similarity between whole pages cannot produce. It catches "definition page for a term used in the article" and "product page mentioned in a how-to" even when the two documents are topically dissimilar.
- The hard-coded target-class filters (lists, dates, disambiguation) map to SEO equivalents: tag and category archives, pagination, legal and utility pages, and near-duplicate pages.

### Gaps
- I did not retrieve published precision/recall for the V2 model per wiki, or details of its features.

## Q4. What role should graph features (current link graph, depth, orphan status) play vs text?

### Takeaway
The evidence says text dominates for *predicting which link an editor adds*. Graph-only and text-only baselines perform similarly on Wikipedia, naive hybrids did not help, and Wikimedia dropped its one behavioural graph feature as negligible. Graph features are therefore best used for **prioritisation and constraints** (orphans, click depth, pillar-to-cluster structure, existing-link dedup) and as a source of **training signal** (SciNCL, HLP), not as the main relevance scorer.

### Cited Findings
- On 4 topical Wikipedia subsets (1,000 articles each), DeepWalk (graph) and LSA (text) "perform similarly … with a small advantage for LSA". Hybrid text-plus-graph methods (TADW, Graph2Gauss, IDNE) did *not* improve on either. The anchor-aware model ATILP reached only about 54–55% AUC on the inductive task. Document semantic similarity had the largest coefficient (about 1.06), and anchor-target similarity added some (about 0.36). The authors conclude that editorial linking norms are hard to learn from text or graph alone. — [arXiv 2105.11734](https://arxiv.org/html/2105.11734v1)
- In Wikimedia's model the navigation-distance (reader co-occurrence) feature was removed as negligible, while the anchor-statistics features carried the model. — [Meta research page](https://meta.wikimedia.org/wiki/Research:Link_recommendation_model_for_add-a-link_structured_task)
- Temporal node embeddings from GNNs performed best in a student study predicting future WikiLinkGraphs edges. This is not peer-reviewed. — [CS224W project](https://snap.stanford.edu/class/cs224w-2019/project/26425112.pdf)
- SciNCL shows graph embeddings are valuable as a *sampler of training pairs* for a text model rather than as an inference-time feature. — [arXiv 2202.06671](https://arxiv.org/abs/2202.06671)
- Co-citation proximity analysis (CPA), a link-structure-only method, was evaluated against Lucene MoreLikeThis (text) on 779,716 and 2.57M Wikipedia articles. Quasi-gold standards were Wikipedia "See also" links and clickstream data. — [Schwarzer et al., JCDL 2016](https://dl.acm.org/doi/10.1145/2910896.2910908); code in [wikimedia/citolytics](https://github.com/wikimedia/citolytics)

### Inferences
- A per-site graph is small, often a few hundred to a few thousand pages, and is heavily templated. Node2vec or GNN features learned there will mostly encode the navigation template. Text plus anchor features should drive relevance. Graph features should drive *which* suggestions matter:
  - inlinks-to-target (boost orphans and low-inlink targets);
  - click depth of the target;
  - whether A already links to B (dedup);
  - whether B links back to A (the reciprocal pattern that HLP and PHP treat as a stronger relation);
  - co-citation (pages linked from the same source pages as B are "see also" candidates for B's neighbours; CPA-style). This last one is a cheap candidate generator that finds related-but-dissimilar pages.
- For **link deletion**, graph and template features are the main signal: a link repeated sitewide, a link with low textual relatedness between anchor context and target, or a target that is redirected or thin.

### Gaps
- I did not find a study measuring graph versus text features on *commercial site internal links* rather than Wikipedia.

## Q5. How do SEO tools (Link Whisper, InLinks, Screaming Frog, Ahrefs) do it?

### Takeaway
Commercial tools are mostly keyword or entity matching plus cosine similarity. Link Whisper matches target keywords (from title, slug, Yoast/RankMath and GSC queries) with "NLP". InLinks links entity mentions to pages the user assigned to that entity. Screaming Frog offers cosine similarity between page embeddings. Ahrefs matches a target page's ranking keywords as text mentions in other pages. None publish accuracy numbers.

### Cited Findings
- **Link Whisper**: it takes target keywords from page title and slug, from Yoast/RankMath focus keywords, and from GSC ranking queries when connected. It shows "linkable keyword opportunities" in source posts that point to target posts. Its marketing claims suggestions come from "topics, keywords, and meaning", via NLP. — [Link Whisper review page](https://linkwhisper.com/link-whisper-review/); [WordPress.org plugin](https://wordpress.org/plugins/link-whisper/); [GreenGeeks tutorial](https://www.greengeeks.com/tutorials/internal-linking-wordpress-link-whisper/)
- **InLinks**: it builds a knowledge graph of entities (mapped to Wikipedia and Wikidata) mentioned across the site. The user assigns at least one target entity to each target page. Links are then created automatically from other pages that mention that entity, and a "context" entity can be set so links only appear on source pages that also contain it. Anchor text therefore varies naturally. — [InLinks help: automate internal linking](https://inlinks.com/help/how-to-automate-your-internal-linking/); [InLinks technology](https://inlinks.com/inlinks-technology-architecture-and-methodology/)
- **Screaming Frog** (v22+): Config > Content > Embeddings, with OpenAI, Gemini or Ollama (local). Semantic-similarity default threshold is 0.95 (adjustable down to 0.5). "Semantic search" finds related pages for internal linking. — [SF v22 release](https://www.screamingfrog.co.uk/blog/seo-spider-22/); [SF semantic similarity tutorial](https://www.screamingfrog.co.uk/seo-spider/tutorials/how-to-identify-semantically-similar-pages-outliers/); [SF blog: map related pages](https://www.screamingfrog.co.uk/blog/map-related-pages-at-scale/)

### Inferences
- InLinks' "entity to target page, plus optional context entity" is essentially Wikimedia's anchor dictionary with user-curated targets. It is the SEO-native way to capture "definition page for a term" and "product page for a how-to". The user's pipeline could get the same effect by extracting each page's primary entity or keyphrase and building an anchor dictionary from it. This is complementary to embedding similarity.
- Screaming Frog's 0.95 default similarity threshold is meant for *near-duplicates*. Cosine similarity at that level signals cannibalisation, not a link opportunity. That matches the user's observation that cosine over-suggests near-duplicates.

### Gaps
- The Ahrefs help-centre article on "Internal link opportunities" returned 404, so I have no primary source for its mechanism. It is commonly described as matching each page's top ranking keywords as text mentions elsewhere on the site, but this is unverified here.
- None of these vendors publish precision or recall.

## Q6. Evaluation: how to measure recall of link suggestions?

### Takeaway
Use held-out existing links as a (noisy) gold standard, as Wikimedia's backtest and the "See also" and clickstream studies do. Remove a sample of real in-content links, regenerate, and measure Recall@K per source page and precision at the operating threshold. Add a human or LLM-judged sample to estimate precision on novel suggestions, because unlinked does not mean wrong.

### Cited Findings
- Wikimedia backtests on held-out linked sentences and reports precision and recall per wiki at a threshold of 0.5, with a deployment bar of 0.75 precision. — [Meta research page](https://meta.wikimedia.org/wiki/Research:Link_recommendation_model_for_add-a-link_structured_task); [T404460](https://phabricator.wikimedia.org/T404460)
- "See also" links and clickstream co-visits served as quasi-gold standards for evaluating related-article recommendations. — [Schwarzer et al. 2016](https://dl.acm.org/doi/10.1145/2910896.2910908)
- SciDocs and SciRepEval evaluate citation-informed embedders with citation prediction, co-view and co-read tasks: MAP and nDCG over held-out citation or co-view pairs. — [arXiv 2202.06671](https://arxiv.org/abs/2202.06671); [HF specter2](https://huggingface.co/allenai/specter2)
- A downstream outcome measure was also used: Wikimedia measured revert rate and activation in an A/B test. — [A/B report](https://analytics.wikimedia.org/published/reports/growth/add_a_link_enwiki_ab_test_report.html)

### Inferences
- Suggested protocol for the site-structure pipeline:
  1. Per crawled site, take in-body (non-template) internal links as positives.
  2. Hold out about 20% per source page and strip them from the source text.
  3. Measure **candidate-generator Recall@K**, meaning the share of held-out targets that appear in the top-K candidates, separately for each generator (cosine, anchor dictionary, co-citation, instruction-prompted relation queries). The union recall shows what each generator adds.
  4. Measure precision and recall of the yes/no decision model at its threshold on held-out positives versus sampled hard negatives (similar but unlinked).
  5. Have the final LLM review, or humans, judge a random sample of *novel* suggestions for true precision.
  6. Track a **near-duplicate rate**: the share of suggestions whose target has cosine above about 0.9 to the source, which approximates the over-suggestion failure.
- Stratify recall by relation type (prerequisite, deeper dive, product/transactional, definition, hub/spoke) to see where cosine fails. Labelling a few hundred pairs by relation type with an LLM is cheap.
- Existing site links are biased toward what the site owner already did. Recall against them underestimates quality for good novel links, and precision against them is pessimistic.

### Gaps
- I found no standard public benchmark for *internal-link* recommendation on commercial websites.
- I did not verify MS MARCO Web Search or ClueWeb22 anchor datasets as evaluation sources in this pass.

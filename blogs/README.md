# AI for Digital Marketing

A practical book, written as a blog series, on using AI well in digital marketing. It covers two toolkits side by side: LLM methods (Claude-style agents, extraction, judging, writing) and classical ML (embeddings, clustering, forecasting, regression, graph methods). One stance runs through every chapter: AI observes, points at what it found and shows the evidence; the human decides. Each chapter is grounded in something Meelu already does, so the series doubles as the reasoning behind the product.

## Parts

1. [Part 0 — Foundations](00-foundations/README.md) — The ideas every later chapter leans on: what LLMs and classical ML are each good at, how to keep AI output honest, and the pipeline shape that makes AI suggestions cheap and trustworthy.
2. [Part 1 — Know Your Site: Turning a Website into Data](01-know-your-site/README.md) — Before any AI can help with marketing it has to see the site as data. This part covers crawling, profiling, classifying and searching your own pages.
3. [Part 2 — AI for SEO](02-ai-for-seo/README.md) — The largest part of the book. SEO has rich data (crawl, Search Console, keyword vendors, SERPs) and clear levers (titles, content, links), so it is where AI helps most today. It is split into five sections.
4. [Part 3 — AI for Content](03-ai-for-content/README.md) — Using AI to write and check web pages for your own site, while the human keeps the voice, the facts and the final say.
5. [Part 4 — AI for Social Listening](04-ai-for-social-listening/README.md) — Finding the conversations where your product is relevant, with a pipeline that filters thousands of posts down to a handful worth a human reply.
6. [Part 5 — AI for Lead Generation](05-ai-for-lead-generation/README.md) — Finding the right people from a plain-language brief, with evidence for every lead and no guessed data.
7. [Part 6 — AI for Marketing Analytics](06-ai-for-marketing-analytics/README.md) — Classical ML done deterministically, with an LLM as the analyst who picks the method, reads the result and states the caveats.
8. [Part 7 — Agentic Marketing Operations](07-agentic-marketing-operations/README.md) — Running Claude-based agents as part of the marketing team: planning, memory, recipes, cost and model choice.
9. [Part 8 — Beyond: Where AI Marketing Goes Next](08-beyond/README.md) — Channels and methods Meelu does not cover yet. These chapters complete the book and double as a roadmap.

## How each chapter brief is laid out

Every chapter file holds a topic suggestion, a summary of what to write, the approach (LLM, classical ML, or both) and the Meelu feature it is grounded in. The chapters are briefs, not drafts.

## Existing series and books to read first

These are the series, courses and books already covering parts of this ground, as of September 2026. Read them to see what is already said well, so this book adds to it instead of repeating it.

### Classical ML for SEO
The closest overlap with this book. These go deep on method, but cover SEO only and don't use LLM agents.

- [MLforSEO: What ML clustering is and where it fits in SEO](https://www.mlforseo.com/machine-learning-tutorials/topic-modeling-clustering/what-ml-clustering-is-and-where-it-fits-in-seo/)
- [MLforSEO Academy: Introduction to Machine Learning for SEO](https://academy.mlforseo.com/course/introduction-to-machine-learning-for-seo/)
- [Lazarina Stoy: Internal link audits and topic clustering with ML](https://lazarinastoy.com/how-to-incorporate-machine-learning-in-internal-linking-audits/)
- [Screaming Frog: Mapping related pages at scale with embeddings](https://www.screamingfrog.co.uk/blog/map-related-pages-at-scale/)
- [Search Engine Journal: Introduction to LLMs and embeddings for SEO](https://www.searchenginejournal.com/llm-embeddings-seo/518297/)
- [WordLift: Keyword clustering for SEO using embeddings](https://wordlift.io/blog/en/keyword-clustering-for-seo-using-ai/)
- [ImportSEM: Interlinking opportunities with k-means and Python](https://importsem.com/discover-interlinking-opportunities-using-k-means-and-python/)
- [Informed Marketers: Keyword clustering by intent with Python](https://www.informedmarketers.com/automating-seo-keyword-clustering-by-intent-using-python/)
- [ContentGecko: Semantic keyword clustering at scale](https://contentgecko.io/blog/semantic-keyword-clustering/)

### Claude and agents for marketing
These focus on prompts and automation. They don't cover classical ML, and they lean toward autopilot rather than human review.

- [Claude Code for Marketers (free course)](https://cc4.marketing/)
- [The Agentic Marketer (book)](https://www.agentic-series.com/the-agentic-marketer-book/)
- [Claude for Marketing, P.Z. Murphy (book)](https://www.amazon.com/Claude-Marketing-AI-Powered-Campaigns-Business/dp/B0GXXSR2J9)
- [coreyhaines31/marketingskills (Claude skills library)](https://github.com/coreyhaines31/marketingskills)
- [Marketing Skills for AI Agents](https://marketing-skills.com/)
- [WebFX: How to use Claude AI for marketing](https://www.webfx.com/blog/ai/claude-ai/)
- [Adspirer: Setting up an AI marketing agent with Claude Code](https://www.adspirer.com/blog/setup-ai-marketing-agent-claude-code)

### Courses on AI for marketers
These hold page one for "ai for marketers" and "ai marketing course".

- [HubSpot Academy: AI for Marketing](https://academy.hubspot.com/)
- [Harvard DCE: AI Marketing Course](https://professional.dce.harvard.edu/)
- [Salesforce Trailhead: AI for Marketers](https://www.salesforce.com/)
- [Coursera: AI for Marketing Specialization](https://www.coursera.org/)
- [CXL: 10 best AI marketing courses](https://cxl.com/)
- [Marketing AI Institute](https://www.marketingaiinstitute.com/)

### LLM SEO (being cited by AI answer engines)
Relevant to Part 2, section 5.

- [Yoast: What is LLM SEO?](https://yoast.com/)
- [Vercel: How we're adapting SEO for LLMs and AI search](https://vercel.com/)
- [Marketer Milk: LLM SEO guide](https://www.marketermilk.com/)
- [Wellows: LLM SEO, how to get cited by AI](https://wellows.com/blog/llm-seo/)

### General introductions
- [Factors.ai: A marketer's guide to how LLMs work](https://www.factors.ai/blog/how-llms-work)
- [Ziplines: Leveraging AI for digital marketing](https://www.ziplines.com/blog/leveraging-ai-for-digital-marketing-success)
- [LLMProGen: Digital marketing and SEO guides](https://llmprogen.com/blog/category/digital-marketing-seo)
- [Adobe: SEO in 2026, how AI is reshaping search](https://business.adobe.com/blog/seo-in-2026-fundamentals)

### Where this book differs
None of the above combines LLM agents with classical ML across SEO, content, social listening, leads and analytics. None of them makes "AI suggests, the human decides, with evidence" the organising principle either. That gap is this book's reason to exist.

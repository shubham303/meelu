---
title: "Keyword Clustering With AI: Why SERP Similarity Is Not Search Intent"
description: "Two keywords can return almost identical Google results and still mean completely different things. Why SERP-overlap keyword clustering breaks on low-volume queries, what AI search and query fan-out change, three real word-order cases from DataForSEO, and a layered workflow that uses an LLM for intent and the SERP for validation."
date: "2026-10-02"
metaTitle: "Keyword Clustering: SERP Similarity vs Search Intent"
metaDescription: "Why SERP-overlap keyword clustering can merge different search intents, real examples from DataForSEO, and a workflow that adds LLM intent clustering."
tags: ["seo", "keyword-clustering", "search-intent", "ai-search"]
---
## Quick answer

What is [keyword clustering](/tools/keyword-clustering-tool)? It is grouping keywords so that one page can serve each group. The usual method puts two keywords in the same cluster when Google returns similar results for them. That works most of the time. But SERP similarity is not the same as search intent. A small query can get the results of a bigger one that uses the same words. **Light blue glasses** gets results for **blue light glasses**, and **wine red** gets results for **red wine**. Use SERP overlap as evidence, not as the definition of intent. Then add an LLM step that asks what the searcher wants.

For years,keyword clustering rule was simple:

> **If two keywords return similar search results, they probably belong to the same keyword cluster.**

That rule still works well. But I think AI search shows a weak spot in it.

Two keywords can get almost the same Google SERPs and still have **different user intents**. Search intent is what the person wants to get done when they type the query. This matters more now that search engines use LLMs to read queries and find answers.

The classic example I came across is:

* **blue light glasses**
* **light blue glasses**

They have the same words. But they mean different things. **Blue light glasses** are glasses designed to filter or reduce blue light. **Light blue glasses** can mean glasses with a light-blue frame. A person sees the difference at once. A keyword clustering tool may not see that..

---

## How keyword clustering traditionally worked

Before AI came into search, SEO was built around the pages that already ranked. Google ranked its results by relevance, links, domain authority, page authority and other ranking signals. This led to a common SEO workflow:

1. Find keywords.
2. Look at search volume and competition.
3. Pick the keywords that matter.
4. Group similar keywords.
5. Create a page targeting the cluster.
6. Study the pages ranking for that cluster.
7. Create something better.

Keyword clustering grew around two methods.

### 1. Text-based clustering

The simplest approach looks at the words themselves. For example:

* buy running shoes
* buying running shoes
* best running shoes
* running shoes to buy

A text tool can see that these queries are close. It can account for things such as:

* plurals
* stemming
* word order
* small changes
* synonyms
* extra words

DataForSEO, for example, gives each keyword a `core_keyword` from its clustering method. Its docs also describe grouping by synonyms. ([DataForSEO Docs][1]) This is useful, but it has a clear limit:

**the same words don't always mean the same intent.**

### 2. SERP-based clustering

The second method looks at what Google ranks. Suppose we have:

**Keyword A**

> best espresso beans

and

**Keyword B**

> best coffee beans for espresso

Say Google returns many of the same pages for both searches. That is evidence that Google thinks one page can serve both. This is the basis of SERP-overlap clustering.

Ahrefs describes keyword clustering this way: put keywords with similar results in one group, because similar results point to similar intent. ([Ahrefs][2]) Semrush does the same. It compares the top results for each keyword and groups terms when their URLs overlap. ([Semrush][3]) So an SEO might set a threshold:

> If 60%+ of the ranking URLs overlap, put the keywords into the same cluster.

This is much better than comparing words. But there is a hidden problem.

---

## What if Google is showing the wrong results?

This is where the **blue light glasses / light blue glasses** example becomes interesting. Imagine that:

> **blue light glasses**

has huge search volume. People have searched it millions of times. There are hundreds or thousands of pages targeting it. The query has an established SERP. Now someone searches:

> **light blue glasses**

The words are almost identical. But the intent is different. The person may be looking for:

> glasses with a light-blue frame.

Yet the SERP can still look a lot like the SERP for **blue light glasses**.

Why? Because the search engine has much more data about the popular query. There are many strong pages about blue-light-filtering glasses. There may be very few pages built for the smaller meaning of "light blue glasses." So the search engine falls back on the meaning it has more evidence for. And that creates a strange situation:

**The SERPs look alike because of how Google ranks pages, not because the two intents are the same.**

That difference matters a lot.

---

## The long-tail keyword problem

This causes a real problem for long-tail keywords. Suppose:

| Keyword            |   Volume | Actual intent                           |
| ------------------ | -------: | --------------------------------------- |
| blue light glasses |     High | Glasses related to blue-light filtering |
| light blue glasses | Very low | Glasses with a light-blue frame         |

A traditional keyword clustering system might see:

> Same words → same core keyword → similar SERP → same cluster

But a human sees:

> These are two different products.

And that means the usual conclusion:

> "These keywords belong on the same page."

could be wrong. The clustering method is not the problem. The problem is that **the tool treats the SERP as the truth about intent.** And the SERP may not show the intent of a low-volume query.

---

## AI search and query fan-out introduce another signal

This is where things get interesting. LLMs can reason about what a query means instead of only asking:

> “What pages rank for this exact phrase?”

For example, an LLM can understand the difference between **“light blue glasses”** and **“blue-light glasses”** from the meaning of the query itself.

This enables a different retrieval model:

**Query → understand intent → find relevant information → write answer**

AI search can also use **query fan-out**: breaking a query into several related searches, retrieving results for each, and combining the sources.

The exact implementation varies across AI search systems, but the key difference is:

> **AI search can use the meaning and intent behind a query to find relevant pages, rather than relying only on what already ranks for the exact words.**

For SEO, this means a page can be relevant to an AI-generated query even when it doesn't contain the exact phrase the user typed.

---

## A real-world example

I saw this with **Binary Optics**. They have a page about **light blue glasses**:

[Binary Optics — Light Blue Glasses](https://binaryoptics.in/)

I tested the query in AI search tools. The page showed up as a source, because its content matched what "light blue glasses" means. The page does not need a top Google ranking for "light blue glasses" to be useful to an LLM. So the two systems ask different questions:

**Traditional SERP:**

> "Which pages have built up enough ranking signals to show for this query? "

**LLM-based retrieval:**

> "Which information answers what this user is asking?"

That difference can matter a lot for SEO. You can also see the example I tested here:

[My ChatGPT search example](https://chatgpt.com/s/t_6abfa2334a1081919e99a192171cb832)

---

## The SEO lesson is not "ignore the SERP"

I don't think the answer is to throw away SERP analysis. Quite the opposite. SERP data is still very useful. The problem is treating it as **the definition of intent**. Instead, I think we should treat it as **one piece of evidence about intent**. The difference is small but important. The old way of thinking:

> These keywords have 70% SERP overlap, therefore they have the same intent.

A better way to read it:

> These keywords have 70% SERP overlap, so Google treats them alike in its results today. Now let's check if the user intent is the same.

That second way is much more useful.

---

## Don't blindly copy the top 10

There is another consequence. For years, SEO advice has often been:

> Look at the top 10 results and figure out what they are doing.

That's still useful. But the top 10 results may lean toward the high-volume meaning. If they do, copying them makes the problem worse. Say you search:

> light blue glasses

and see ten pages, most of them about blue-light glasses. If you build your page by analyzing those ten competitors, you might conclude:

* They talk about blue-light filtering.
* They have certain headings.
* They use "blue light glasses" repeatedly.
* They have certain related keywords.
* They have certain backlinks.
* They have certain content length.

So you create another page about blue-light glasses. Your page now fits the **existing SERP**. But it may miss the **user's real intent**.

---

## Three more real cases: search intent examples from DataForSEO

The glasses example is not a one-off. I checked word-order pairs in DataForSEO (United States, English, October 2026) and found the same pattern elsewhere. These are the keyword clustering examples I keep coming back to. For each pair I looked at three things:

* **Google Ads volume and CPC**: what most keyword tools show.
* **Clickstream volume**: how often people type each exact phrase.
* **Top 10 Google results**: what the searcher gets.

| Keyword            | Google Ads volume | CPC   | Clickstream volume |
| ------------------ | ----------------: | ----: | -----------------: |
| blue light glasses |           201,000 | $2.13 |            190,589 |
| light blue glasses |           201,000 | $2.13 |                432 |
| red wine           |            90,500 | $0.76 |             68,692 |
| wine red           |            90,500 | $0.76 |             22,193 |
| table lamp         |             5,400 | $0.94 |             31,431 |
| lamp table         |             5,400 | $0.94 |              2,475 |
| desk chair         |             1,900 | $1.22 |             75,401 |
| chair desk         |             1,900 | $1.22 |              1,894 |

In every pair, Google Ads gives both phrases the same volume and the same CPC. It treats them as one keyword. Clickstream shows they are two different queries, and the smaller one still has real demand.

### 1. Red wine vs wine red

**Red wine** is a drink. **Wine red** is a color: the deep red people search for when they want a wine-red dress, wine-red hair or a wine-red paint.

About 22,000 searches a month type "wine red". That is not noise. But 8 of the top 9 results for "wine red" are about the drink. They are wine shops, red blends and guides to red wine. Only one result, the Wikipedia page for the color, answers what the searcher asked.

### 2. Table lamp vs lamp table

A **table lamp** is a lamp that sits on a table. A **lamp table** is a small side table you put a lamp on. It is furniture, not lighting. About 2,500 searches a month type "lamp table". Only 3 of the top 8 results for "lamp table" sell lamp tables. The other 5 are table-lamp pages from lighting stores and retailers. A lighting page ranks for a furniture query.

### 3. Desk chair vs chair desk

A **desk chair** is a chair you use at a desk. A **chair desk** is one piece of furniture: a chair with a writing surface attached, the kind used in classrooms. About 1,900 searches a month type "chair desk". Every one of the top 9 results for "chair desk" is a desk-chair or office-chair page. Six of them are the same URLs that rank for "desk chair". Not one result shows a chair with a desk attached.

### What the three cases share

* The tools merge both phrases into one keyword, with one volume and one CPC.
* The smaller phrase has its own measurable demand.
* Pages for the bigger phrase fill most of the SERP for the smaller one.
* An LLM, or any human, can see in one second that the two phrases mean different things.

These are the queries where SERP clustering and keyword tools both say "same cluster". Both are wrong.

Not every word-order pair behaves this way. **Sugar cane** and **cane sugar** also get the same Google Ads volume and CPC, but Google keeps their results apart. None of the top 10 results overlap. So check the SERP for each pair. Don't assume the pattern holds.

---

## My proposed keyword clustering workflow

This leads me to a different approach to keyword clustering. I would use several layers, not one clustering method.

### Step 1: Start with seed keywords

Start with a small set of seed keywords you care about. Don't try to find every keyword your business could ever target. No tool can, and a giant list buries the few clusters that matter. Keep the work focused on the seeds you give it. For example, for an eyewear website:

* blue light glasses
* prescription glasses
* reading glasses
* light blue glasses
* computer glasses

### Step 2: Expand the keywords

Expand each seed into the searches built around it. Use sources such as:

* Semrush
* Ahrefs
* DataForSEO
* Google Search Console
* Google autocomplete
* other keyword databases

DataForSEO, for example, has a keyword suggestions API. It returns long-tail queries and their search volume. ([DataForSEO Docs][1]) At this stage, don't worry about perfect clusters. The goal is to see every way people search for each seed, not to map the whole market.

### Step 3: Remove obvious noise

Now remove keywords that aren't useful. For example:

* queries with almost no volume
* queries in the wrong language
* typos that don't matter
* names of things you don't sell
* queries that drift away from the seed
* navigational queries you don't serve

You might use something like:

> Remove keywords with volume < 100

as a first filter. But 100 is not a fixed rule. For some businesses, a keyword with 20 searches a month can be worth a lot. The threshold should depend on the business.

### Step 4: Drop keywords that look different from the seed and aren't about it

This is a different job from clustering. Some expanded keywords contain every word of the seed. Keep all of those, even when the meaning flips. For the seed:

> blue light glasses

the keyword

> light blue glasses

has the same words. It is the kind of keyword the intent step needs to see, so it is not dropped here. Other keywords look different: they are missing some of the seed's words. For those, give an LLM the seed and the keyword and ask:

> Is this keyword about the same subject as the seed?

> blue light blocking eyewear

is about the seed. Keep it.

> blue glasses

could be about anything blue. If the model says it is not about the seed, drop it. So drop a keyword only when it looks different from the seed and is not about it. This gives you a cleaner keyword list, focused on the seed, before clustering.

### Step 5: Create initial clusters using core keywords

Now use something like DataForSEO's core-keyword grouping. The idea is:

> Put keywords with the same core concept into an initial group.

This helps because it cuts the number of comparisons you need to make. For example:

**Core keyword: blue light glasses**

could contain:

* blue light glasses
* best blue light glasses
* blue light blocking glasses
* blue light glasses for computer
* blue light glasses for work
* blue light filter glasses

DataForSEO's `core_keyword` field names the main keyword of each group its method finds. ([DataForSEO Docs][1]) At this stage, you keep the groups broad on purpose.

### Step 6: Semantic keyword clustering: use an LLM to split the clusters by intent

I think many clustering workflows miss this part. It is semantic keyword grouping: sorting keywords by what they mean rather than by the words they share or the URLs they rank. Take:

> **blue light glasses**

and ask an LLM to divide the group into **distinct user intents**. For example:

**Cluster A — Blue-light filtering glasses**

* blue light glasses
* blue light blocking glasses
* blue light glasses for computer
* best blue light glasses

**Cluster B — Light-blue colored glasses**

* light blue glasses
* light blue frame glasses
* glasses with light blue frames

The important thing is that these may share many words. They may even share SERP results. But you ask the LLM a different question:

> **What is the user trying to accomplish?**

rather than:

> **What pages does Google currently rank?**

That's a new kind of clustering signal.

### Step 7: Verify the clusters against actual SERPs

This is where SERP data comes back. For each cluster, check the SERP overlap. If the keywords overlap a lot, that's useful evidence. If they overlap very little, that's a sign you should split them. But now SERP overlap is **validation**, not the sole source of truth.

## The full pipeline

So I would think about keyword clustering as a pipeline:

```text
Seed Keywords
      ↓
Keyword Expansion
      ↓
Noise Removal
      ↓
Seed Relevance Filtering
      ↓
Core Keyword Clustering
      ↓
LLM Intent Clustering
      ↓
SERP Overlap Validation
      ↓
Final Page-Level Keyword Clusters
```

The last step is keyword mapping: you give each checked cluster one page, and each page serves one intent. The important part is that each layer answers a different question.

| Layer                | Question                                             |
| -------------------- | ---------------------------------------------------- |
| Keyword expansion    | What could people search for?                        |
| Volume filtering     | Which queries have enough measurable demand?         |
| Seed relevance       | Is this keyword still about the seed?                |
| Core keyword         | Which terms are related in words or meaning?         |
| LLM intent           | What does the user actually want?                    |
| SERP overlap         | Does Google treat them the same today?               |
| AI answer similarity | Does an AI system read them the same way?            |
| Keyword mapping      | Which page should serve this cluster?                |

That's much stronger than asking one method to solve everything.

---

## The paradox—and opportunity—of modern SEO

This leads to a paradox. Traditional SEO says: **look at the SERP and understand what Google wants.** AI search increasingly says: **understand what the user wants, then find information that meets that need.**

These usually agree, but the interesting opportunities are where they don't.

A high-volume query can dominate the SERP of a lower-volume query, creating a feedback loop: more pages target that meaning, stronger ranking signals reinforce it, and SEO tools eventually say, "same intent." Everyone keeps producing more of the same content.

AI search can potentially break this loop by understanding meaning rather than simply following the existing SERP.

So if keyword research says **"these keywords rank together"**, but intent analysis says **"users want different things,"** don't automatically combine them. Sometimes the better strategy is to **not run the same race**.

For **light blue glasses**, that means creating a page for glasses with light-blue frames—not another page about blue-light glasses simply because that's what the current SERP suggests.

The opportunity may be in serving the intent that everyone else

---

## My rule going forward

If I were building an SEO content strategy today, my rule would be:

> **Don't create a page because a keyword tool says two keywords belong together. Create one page when that page meets the intent behind both queries.**

Sometimes SERP clustering and intent analysis disagree. When they do, **don't assume the SERP is right**. Look into why they disagree.

Sometimes Google is right, and the intents are the same. Sometimes you've found a different intent that the SERP doesn't show well yet.

That second case matters most in the age of AI search. An AI system may see the difference before the SERP does. If it does, **the page that meets the missed intent has a new way to reach people.**

That may be one of the biggest changes AI brings to SEO:

> **The goal is moving from knowing what ranks today to knowing why a user is searching at all.**

That's a much better problem to work on than finding the right keyword density.

[1]: https://docs.dataforseo.com/v3/dataforseo_labs-google-keyword_suggestions-live/ "dataforseo_labs/google/keyword_suggestions/live – DataForSEO API v.3"
[2]: https://ahrefs.com/blog/keyword-clustering/ "How To Do Keyword Clustering the Easy Way"
[3]: https://www.semrush.com/blog/keyword-manager-clustering-tool/ "Use Semrush‘s keyword clustering tool to build your strategy"
[4]: https://ranknexus.ai/blog/query-fan-out-ai-search-seo-aeo-geo "Query fan-out: how AI search picks its sources (SEO, AEO and GEO guide) | RankNexus"

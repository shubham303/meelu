# Generate, Screen, Review, Rank: The Pipeline Pattern Behind Good AI Suggestions

**Topic suggestion:** Generate, Screen, Review, Rank: The Pipeline Pattern Behind Good AI Suggestions

**Summary:** The book's core design pattern. Cheap deterministic generators produce many candidates. A fast screen (embedding or small model) drops the obvious misses. An LLM reviewer judges and rewrites the survivors. A ranker applies budgets so the human sees a short list. Explain the cost curve and why each stage reads only what the previous stage approved.

**Approach:** Both

**Grounded in Meelu:** SEO page suggestions and internal link suggestions both run generate → screen → review → rank.

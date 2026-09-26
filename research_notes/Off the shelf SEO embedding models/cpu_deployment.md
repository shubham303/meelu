# CPU deployment of open embedding and reranker models (as of 2026-09-26)

Scope: what it takes to run each candidate in the embed worker's current setup (huggingface_hub download of `onnx/model_quantized.onnx` + `tokenizer.json`, onnxruntime CPUExecutionProvider, no torch), how fast it is, and what else is available.

Method note: besides web sources, I (a) listed every candidate repo's `onnx/` folder through the Hugging Face API (`https://huggingface.co/api/models/<repo>/tree/main/onnx`) on 2026-09-26, (b) opened the graph headers of two exports with the `onnx` package to read their real inputs and outputs, and (c) ran a small throughput benchmark of the int8 exports inside a throwaway container built from the project's own `meelu-embed-worker` image (onnxruntime 1.23.2, tokenizers 0.23.2). The benchmark hardware is an Apple M1 under Docker Desktop (linux/arm64, 4 vCPU, 4 GB container limit), NOT a server x86 CPU; treat those numbers as relative, not absolute. Script: `scratchpad/bench/bench.py` (not in the repo).

## 1. Ready-made ONNX exports, quantized variants, and what a plain onnxruntime loop must implement

### Takeaway
Every candidate except mxbai-rerank-v2 has an `onnx/model_quantized.onnx` in a well-known repo, so the existing downloader works by repo id. But three of them are not drop-in: EmbeddingGemma and bge-m3/Qwen3 ship weights in a separate `model_quantized.onnx_data` (or `.onnx_data`) file the downloader must also fetch; Qwen3-Embedding's onnx-community export expects `position_ids` plus 56 empty KV-cache inputs, left padding and last-token pooling; Qwen3-Reranker's export is a causal LM that returns full-vocabulary logits and needs a chat-style prompt and yes/no logit extraction.

### Cited Findings

File lists (sizes from the HF tree API, 2026-09-26) — [HF API, e.g. onnx-community/Qwen3-Embedding-0.6B-ONNX](https://huggingface.co/api/models/onnx-community/Qwen3-Embedding-0.6B-ONNX/tree/main/onnx):

| Model | Repo with ONNX | `model_quantized.onnx` (int8) | Other variants present | External data file? |
|---|---|---|---|---|
| multilingual-e5-small (current) | `Xenova/multilingual-e5-small` | 118 MB | fp32 470, fp16 235, int8/uint8 118, q4 399, q4f16 205, bnb4 397 | no |
| bge-reranker-base (current) | `Xenova/bge-reranker-base` | 279 MB | fp32 1113, fp16 557, q4 826, q4f16 434, bnb4 821 | no |
| Qwen3-Embedding-0.6B | `onnx-community/Qwen3-Embedding-0.6B-ONNX` | 614 MB | fp32 (307 MB + 2093 MB `.onnx_data`), fp16 (+1200 MB data), int8/uint8 614, q4 914, q4f16 568, bnb4 887 | only fp32/fp16 |
| Qwen3-Embedding-0.6B | `Qdrant/Qwen3-Embedding-0.6B-onnx` (FastEmbed) | 1.12 GB, int8 `MatMulNBits` weight-only, needs onnxruntime >= 1.23 | fp32 2.38 GB | fp32 only |
| EmbeddingGemma-300M | `onnx-community/embeddinggemma-300m-ONNX` (the official Google repo has no `onnx/`) | 0.6 MB graph + **309 MB `model_quantized.onnx_data`** | fp32 (1235 MB data), fp16 (617 MB data), q4 (197 MB data), q4f16 (175 MB data), no_gather_q4 (195 MB data) | **yes, every variant** |
| gte-modernbert-base | `Alibaba-NLP/gte-modernbert-base` (official) | 150 MB | fp32 596, fp16 298, q4 224, q4f16 140, bnb4 217 | no |
| snowflake-arctic-embed-m-v2.0 | `Snowflake/snowflake-arctic-embed-m-v2.0` (official) | 311 MB | fp32 1226, fp16 613, q4 844, q4f16 451, bnb4 837 | no |
| bge-m3 | `Xenova/bge-m3` | 570 MB | fp32 (2267 MB data), fp16 1134, q4 1248, q4f16 700, plus `sentence_transformers_*.onnx` variants | fp32 only |
| bge-m3 | `BAAI/bge-m3` (official) | none (fp32 only, 2267 MB `.onnx_data`) | — | yes |
| Qwen3-Reranker-0.6B | `onnx-community/Qwen3-Reranker-0.6B-ONNX` | 1219 MB (dynamic int8 on MatMul/Gemm) | q4 995 MB (`MatMulNBits`, block 32); no fp32/fp16 | no |
| Qwen3-Reranker-0.6B (seq-cls) | `shawnw3i/Qwen3-Reranker-0.6B-seq-cls-ONNX` (community, ~34 downloads) | not verified | — | not verified |
| gte-reranker-modernbert-base | `Alibaba-NLP/gte-reranker-modernbert-base` (official) | 151 MB | fp32 599, fp16 300, q4 225, q4f16 140, bnb4 218 | no |
| jina-reranker-v2-base-multilingual | `jinaai/jina-reranker-v2-base-multilingual` (official) | 280 MB | fp32 1114, fp16 557, q4 827, bnb4 822 | no |
| ms-marco-MiniLM-L6 | `Xenova/ms-marco-MiniLM-L-6-v2` | 23 MB | fp32 91, fp16 46, q4 55, q4f16 30 | no |
| ms-marco-MiniLM-L6 | `cross-encoder/ms-marco-MiniLM-L6-v2` (official) | no `model_quantized`; has `model_qint8_arm64/avx512/avx512_vnni`, `model_quint8_avx2` (23 MB each), `model_O1..O4` | — | no |
| mxbai-rerank-base-v2 | `mixedbread-ai/mxbai-rerank-base-v2` | **no `onnx/` folder** (HF API: "onnx does not exist on main") | community only: `keisuke-miyako/mxbai-rerank-base-v2-onnx-int8` (13 downloads), `tss-deposium/mxbai-rerank-base-v2-onnx-fp16` | — |

- The `intfloat/multilingual-e5-small` official repo only has `model.onnx`, `model_O4.onnx` and `model_qint8_avx512_vnni.onnx`; the `model_quantized.onnx` naming the worker relies on is a Xenova/onnx-community convention. — [HF API](https://huggingface.co/api/models/intfloat/multilingual-e5-small/tree/main/onnx)
- Graph inputs, read from the export headers (`onnx.load(..., load_external_data=False)`):
  - `onnx-community/Qwen3-Embedding-0.6B-ONNX`: inputs `input_ids`, `attention_mask` [batch, total_sequence_length], `position_ids`, and `past_key_values.{0..27}.key/value` [batch, 8, past_len, 128] (56 tensors); outputs `last_hidden_state` [batch, seq, 1024] plus 56 `present.*` tensors. A one-shot embedding call must pass zero-length KV tensors (shape [b, 8, 0, 128]) and compute `position_ids` itself. — [file](https://huggingface.co/onnx-community/Qwen3-Embedding-0.6B-ONNX/tree/main/onnx) (inspected locally)
  - `onnx-community/embeddinggemma-300m-ONNX`: inputs `input_ids`, `attention_mask`; outputs `last_hidden_state` [b, seq, 768] and **`sentence_embedding` [b, 768]** — pooling and the dense projection are inside the graph, so the loop just reads `sentence_embedding` (then truncates/normalizes for MRL). — [file](https://huggingface.co/onnx-community/embeddinggemma-300m-ONNX/tree/main/onnx) (inspected locally)
- Qwen3-Embedding usage rules: last-token pooling, left padding recommended, 28 layers, 32K context, 1024 dims, MRL "custom dimensions from 32-1024", instruction-aware (queries get `Instruct: {task}\nQuery:{query}`; documents get no instruction). — [Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B); [onnx-community README](https://huggingface.co/onnx-community/Qwen3-Embedding-0.6B-ONNX)
- Qdrant's export notes "Pooling and normalization are not part of the ONNX graph", embeddings are "the hidden state of the last non-padding token" L2-normalized, and omitting the query instruction "costs roughly 1% to 5% of retrieval quality". Its int8 build measured cosine 0.9997 mean / 0.9996 worst vs fp32 SentenceTransformer, largest similarity shift 0.006 (small sample). — [Qdrant/Qwen3-Embedding-0.6B-onnx](https://huggingface.co/Qdrant/Qwen3-Embedding-0.6B-onnx)
- Qwen3-Reranker is "a CausalLM-based reranker — not a classifier": format query + document into a chat prompt (system: `Judge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be "yes" or "no".`; user: `<Instruct>: ...\n\n<Query>: ...\n\n<Document>: ...`; assistant prefix `<think>\n\n</think>\n`), read the `yes`/`no` logits at the last position, `score = softmax([yes, no])[0]`. Left padding; 32K context, recommended max_length 8192. — [onnx-community/Qwen3-Reranker-0.6B-ONNX](https://huggingface.co/onnx-community/Qwen3-Reranker-0.6B-ONNX); [Qwen/Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
- A sequence-classification conversion `tomaarsen/Qwen3-Reranker-0.6B-seq-cls` (197k downloads) exposes Qwen3-Reranker as a normal CrossEncoder with one output logit (safetensors only, no ONNX in that repo). — [HF](https://huggingface.co/tomaarsen/Qwen3-Reranker-0.6B-seq-cls)
- EmbeddingGemma prompts: query `task: search result | query: {content}`, document `title: {title | "none"} | text: {content}`; other tasks e.g. `task: clustering | query:`. Max input 2048 tokens; 768 dims with MRL 512/256/128. Use float32 or bfloat16 — "float16 is unsupported" (so avoid the `fp16`/`q4f16` ONNX variants). Gemma licence terms apply. — [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m)
- snowflake-arctic-embed-m-v2.0: CLS pooling, query prefix `query: ` (queries only), max_length 8192 (built on gte-multilingual-base with RoPE), "113m non-embedding parameters", MRL to 256 dims ("decrease vector size by 3x with about 3% degradation"), `trust_remote_code=True` for the torch path, Apache-2.0, 74 languages. — [Snowflake/snowflake-arctic-embed-m-v2.0](https://huggingface.co/Snowflake/snowflake-arctic-embed-m-v2.0)
- gte-modernbert-base: English only, 149M params, 8192 max input, 768 dims, MTEB-en 64.38, BEIR 55.33, LoCo 87.57, CoIR 79.31; gte-reranker-modernbert-base: 149M, 8192, BEIR 56.19, LoCo 90.68. Both list Transformers.js usage (CLS pooling for the embedder). — [gte-modernbert-base](https://huggingface.co/Alibaba-NLP/gte-modernbert-base); [gte-reranker-modernbert-base](https://huggingface.co/Alibaba-NLP/gte-reranker-modernbert-base)
- mxbai-rerank-base-v2: 0.5B params (Qwen2.5-based per Mixedbread), run through sentence-transformers `CrossEncoder` or the `mxbai-rerank` package; Apache-2.0; BEIR avg 55.57; latency "0.67 seconds" on A100. No official ONNX. — [mixedbread-ai/mxbai-rerank-base-v2](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2)
- Reranker quality context from Qwen's card (0.6B class): Qwen3-Reranker-0.6B MTEB-R 65.80 / CMTEB-R 71.31 / MMTEB-R 66.36 / MLDR 67.28 / MTEB-Code 73.42 vs bge-reranker-v2-m3 57.03/72.16/58.36/59.51/41.38, gte-multilingual-reranker-base 59.51/74.08/59.44/66.33/54.18, jina-multilingual-reranker-v2-base 58.22/63.37/63.73/39.66/58.98. — [Qwen/Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) (vendor-reported)

### Inferences
- Drop-in (same loop as today: tokenizer.json, right padding, pool, normalize): gte-modernbert-base (CLS), arctic-embed-m-v2.0 (CLS, `query: ` prefix), bge-m3 (CLS, dense only), gte-reranker-modernbert-base, jina-reranker-v2, ms-marco-MiniLM (all single-logit cross-encoders like bge-reranker-base).
- Needs a small loader change: EmbeddingGemma (download `model_quantized.onnx_data` next to the graph; read `sentence_embedding`; add the two prompt templates).
- Needs a model-specific code path: Qwen3-Embedding (left pad, `position_ids`, 56 empty KV inputs, last-token pooling, EOS token, query instruction) and Qwen3-Reranker (prompt template, last-position yes/no logits). The Qwen3-Reranker ONNX computes logits over the full ~151k vocabulary at every position, which is a large memory cost per batch (see section 4).
- mxbai-rerank-v2 has no trustworthy ONNX; it would need a self-export (Optimum) or torch.

### Gaps
- Did not verify whether `onnx-community/Qwen3-Embedding-0.6B-ONNX`'s tokenizer appends the `<|endoftext|>` EOS token automatically (Qwen's reference code appends it before last-token pooling).
- Did not verify the community seq-cls ONNX export of Qwen3-Reranker for correctness.
- No published int8-vs-fp32 retrieval-quality numbers for the onnx-community quantized files of EmbeddingGemma, gte-modernbert, arctic-m-v2 or the rerankers.

## 2. Alternatives to a hand-written onnxruntime loop

### Takeaway
FastEmbed (v0.8.1, 2026-09-22) now covers Qwen3-Embedding-0.6B and EmbeddingGemma natively on onnxruntime, and its reranker list includes bge-reranker-base, jina-reranker-v2 and ms-marco-MiniLM but not Qwen3-Reranker, gte-reranker-modernbert or mxbai-v2. TEI 1.9 (CPU image) serves Qwen3, Gemma3, ModernBERT, GTE and XLM-R embedders and XLM-R/GTE/ModernBERT rerankers, but not Qwen3-Reranker. llama.cpp is the one runtime with a native Qwen3-Reranker path (`--reranking --pooling rank`), with conversion pitfalls. Ollama has no rerank API.

### Cited Findings
- FastEmbed v0.8.1 (released 2026-09-22) adds `google/embeddinggemma-300m`, `Qwen/Qwen3-Embedding-0.6B` and `Qwen/Qwen3-Embedding-0.6B-Q` ("the quantized model requires onnxruntime>=1.23"), plus `PoolingType.LAST_TOKEN` for custom models. v0.8.0 (2026-03-23) uses CUDA automatically if available. v0.6.1 added custom rerankers; v0.6.0 added dense custom models. — [fastembed releases](https://github.com/qdrant/fastembed/releases)
- FastEmbed's published supported-models page lists 6 rerankers: `Xenova/ms-marco-MiniLM-L-6-v2` (0.08 GB), `Xenova/ms-marco-MiniLM-L-12-v2` (0.12 GB), `jinaai/jina-reranker-v1-tiny-en`, `jinaai/jina-reranker-v1-turbo-en`, `BAAI/bge-reranker-base` (1.04 GB), `jinaai/jina-reranker-v2-base-multilingual` (1.11 GB, CC-BY-NC-4.0). Text models listed there include `intfloat/multilingual-e5-large` but the page (possibly stale vs v0.8.1) did not list Qwen3, EmbeddingGemma, gte-modernbert, arctic-m-v2 or bge-m3. — [FastEmbed supported models](https://qdrant.github.io/fastembed/examples/Supported_Models/)
- Note the jina-reranker-v2 licence: CC-BY-NC-4.0 (non-commercial). — same source
- TEI supports embedders of type "Nomic, BERT, CamemBERT, XLM-RoBERTa ... JinaBERT ... Mistral, Alibaba GTE, Qwen2 ... MPNet, ModernBERT, Qwen3, and Gemma3"; examples include Qwen/Qwen3-Embedding-0.6B, google/embeddinggemma-300m (gated), Snowflake/snowflake-arctic-embed-m-v2.0. Rerankers: "CamemBERT, and XLM-RoBERTa Sequence Classification models", examples BAAI/bge-reranker-base/large, Alibaba-NLP/gte-multilingual-reranker-base (GTE), Alibaba-NLP/gte-reranker-modernbert-base (ModernBert). No Qwen3 reranker listed. CPU images: `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9` (x86_64) and `cpu-arm64-1.9`. — [TEI supported models](https://huggingface.co/docs/text-embeddings-inference/supported_models)
- Latest TEI release v1.9.4 on 2026-09-15 (ARM64 Dockerfile, ROCm, harrier-oss-v1). — [TEI releases](https://github.com/huggingface/text-embeddings-inference/releases)
- Infinity serves embeddings and rerankers with PyTorch, Optimum (ONNX) or CTranslate2 engines; CPU image `michaelf34/infinity:latest-cpu --engine optimum` requires an ONNX file ("Models from https://huggingface.co/Xenova are recommended"). Latest release 0.0.77 on 2025-08-22 — no release in over a year. — [Infinity README](https://github.com/michaelfeil/infinity); [releases API](https://api.github.com/repos/michaelfeil/infinity/releases)
- sentence-transformers supports `backend="onnx"` and `backend="openvino"`, with `export_optimized_onnx_model` (O1–O4) and `export_dynamic_quantized_onnx_model(..., "avx512_vnni"|...)`, `export_static_quantized_openvino_model`. It still depends on torch at import. — [ST efficiency docs](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)
- llama.cpp: `llama-server -m Qwen3-Reranker-0.6B-f16.gguf --reranking --pooling rank --embedding`, call `/v1/rerank` (the embeddings endpoint returns zeros for rerankers). "Most community GGUF conversions of Qwen3-Reranker are broken" because they lack `cls.output.weight` (scores like 4.5e-23); the official `convert_hf_to_gguf.py` extracts it from `lm_head`. — [gist](https://gist.github.com/VooDisss/42bce4eb5c76d3c325633886c5e348ee); [HF discussion](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B/discussions/22)
- llama.cpp issue #16407 (opened 2025-10-03, "bug-unconfirmed") reports wrong `/rerank` scores for Qwen3-Reranker, bge-reranker and mxbai models; status unresolved at time of fetch. — [ggml-org/llama.cpp#16407](https://github.com/ggml-org/llama.cpp/issues/16407)
- GGUF repos (HF API): `Qwen/Qwen3-Embedding-0.6B-GGUF` (Q8_0 639 MB, f16 1198 MB); `ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF` (639 MB); `ggml-org/embeddinggemma-300M-GGUF` (Q8_0 334 MB); `unsloth/embeddinggemma-300m-GGUF` (Q4_0 278 MB, Q8_0 329 MB, BF16 612 MB). — [HF API](https://huggingface.co/api/models/ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/tree/main)
- Ollama: "Standard Ollama doesn't have a direct rerank API"; Qwen3-Reranker models on Ollama are community uploads (e.g. `dengcao/Qwen3-Reranker-0.6B`). The official `docs/api.md` contains no rerank endpoint (grep, 2026-09-26). — [glukhov.org](https://www.glukhov.org/rag/embeddings/qwen3-embedding-qwen3-reranker-on-ollama/); [ollama docs/api.md](https://github.com/ollama/ollama/blob/main/docs/api.md)
- Qwen3-Embedding card lists vLLM (>= 0.8.5) and TEI as deployment options. — [Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)

### Inferences
- If the worker wants to stop owning pooling/prompt code for Qwen3-Embedding and EmbeddingGemma, FastEmbed is the closest fit (same onnxruntime + huggingface_hub stack, no torch). It does not help with Qwen3-Reranker.
- TEI is a separate Rust service (another compose container) that would cover most embedders and the ModernBERT/XLM-R rerankers over HTTP; it does not do Qwen3-Reranker.
- For Qwen3-Reranker, the realistic options are: our own onnxruntime path over the onnx-community causal-LM export, a seq-cls export, or llama-server with the ggml-org GGUF. Each carries correctness risk; validate scores against the reference implementation.
- Infinity looks unmaintained (no release since 2025-08); Ollama is not a reranking option.

### Gaps
- Did not confirm whether the FastEmbed docs page has been regenerated for v0.8.1, or the exact FastEmbed model names for the int8 EmbeddingGemma.
- Did not find whether TEI's CPU backend can run Qwen3-Reranker via a seq-cls conversion.

## 3. Measured CPU throughput / latency and int8 accuracy loss

### Takeaway
BENCH_TAKEAWAY

### Cited Findings
BENCH_TABLE

Published numbers:
- sentence-transformers backend benchmark on an i7-13700K (MiniLM-L6, bge-base, mxbai-large; median speedup over torch fp32 and quality ratio on NanoBEIR NDCG@10 + STSb): onnx fp32 0.90x (100.00%), openvino fp32 1.06x, **onnx-qint8 1.92x (99.58%)**, **openvino-qint8 2.84x (99.37%)**, llama.cpp q8_0 1.01x (99.92%), llama.cpp q4_k_m 1.23x (99.40%), torch fp16 on CPU 0.25x, bf16 0.28x. On HF Jobs cloud `cpu-upgrade` instances the ranking changes: onnx-qint8 1.32x, openvino-qint8 0.86x, llama.cpp f16 1.88x, q4_k_m 1.75x, openvino fp32 1.40x. "benchmark on your deployment hardware." — [ST efficiency docs](https://sbert.net/docs/sentence_transformer/usage/efficiency.html) (charts `backends_benchmark_cpu.png`, `backends_benchmark_cpu_cloud.png` in the [docs source](https://github.com/UKPLab/sentence-transformers/tree/master/docs/img))
- Ettin reranker blog, CPU (i7-13700K, torch SDPA): ettin-reranker-17m 267.4 pairs/s, ms-marco-MiniLM-L4-v2 206.2 pairs/s, ettin-32m 92.5 pairs/s; the blog also states ms-marco-MiniLM-L6-v2 at 143.9 pairs/s on CPU (from search snippet). GPU (H100, bf16, NQ docs, max_length 512): MiniLM-L6 3817, bge-reranker-base 2858, bge-reranker-v2-m3 1569, gte-reranker-modernbert-base 1418, mxbai-rerank-large-v2 387 pairs/s. — [HF blog: Ettin rerankers](https://huggingface.co/blog/ettin-reranker)
- EmbeddingGemma quantization quality (multilingual MTEB mean, 768d): full precision 61.15, Q8_0 60.93, Q4_0 60.62. MRL: 512d 60.71, 256d 59.68, 128d 58.23. — [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m)
- Qwen3-Embedding int8 (Qdrant export): cosine 0.9997 vs fp32. — [Qdrant/Qwen3-Embedding-0.6B-onnx](https://huggingface.co/Qdrant/Qwen3-Embedding-0.6B-onnx)
- A community int8 Qwen3-Embedding TEI-ONNX export claims "2-4x faster inference on CPU compared to float32" (unverified claim, no measurement shown). — [janni-t/qwen3-embedding-0.6b-int8-tei-onnx](https://huggingface.co/janni-t/qwen3-embedding-0.6b-int8-tei-onnx)
- sentence-transformers notes BGE-M3 Q4 GGUF "failed the agreement check against FP32" and was excluded — 4-bit is not always safe. — [ST efficiency docs](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)

### Inferences
BENCH_INFERENCES

### Gaps
- No published x86 server CPU (e.g. AVX-512 VNNI Xeon) docs/sec numbers found for Qwen3-Embedding-0.6B, EmbeddingGemma, arctic-m-v2 or Qwen3-Reranker; my own numbers are ARM (M1 via Docker) and small-sample.
- No int8 retrieval-quality (NDCG) numbers for the specific onnx-community quantized files.

## 4. Memory footprint per model

### Takeaway
MEM_TAKEAWAY

### Cited Findings
MEM_TABLE

### Inferences
MEM_INFERENCES

### Gaps
- Peak RSS depends heavily on batch size x sequence length (attention and, for Qwen3-Reranker, vocab-sized logits); I measured only the workloads listed.

## 5. Changing the embedding dimension in pgvector, and re-embedding cost

### Takeaway
pgvector indexes (HNSW/IVFFlat) accept up to 2,000 dims for `vector` and 4,000 for `halfvec`, so every candidate fits natively (max is 1024). MRL models (Qwen3-Embedding 32–1024, EmbeddingGemma 768/512/256/128, arctic-m-v2 256) can be truncated and re-normalized to keep a smaller column; non-MRL models (gte-modernbert 768, bge-m3 1024) should not be truncated. Any model change means re-embedding every row, because vectors from different models are not comparable.

### Cited Findings
- `vector` stores up to 16,000 dims at `4 * dims + 8` bytes; `halfvec` up to 16,000 at `2 * dims + 8`; HNSW/IVFFlat index limits: vector 2,000, halfvec 4,000, bit 64,000, sparsevec 1,000 non-zero. — [pgvector README](https://github.com/pgvector/pgvector)
- Expression indexes: half-precision index via `(embedding::halfvec(n))`, binary quantization via `binary_quantize(embedding)::bit(n)` with re-ranking on the full vectors, and `subvector(embedding, 1, n)::vector(n)` for Matryoshka-style prefix search. — [pgvector README](https://github.com/pgvector/pgvector)
- HNSW builds "significantly faster when the graph fits into `maintenance_work_mem`"; raise `max_parallel_maintenance_workers`; build the index after loading data. — [pgvector README](https://github.com/pgvector/pgvector)
- MRL support: Qwen3-Embedding-0.6B "custom dimensions from 32-1024" ([card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)); Qdrant's export "always returns 1024 dimensions; to use a shorter vector, truncate it and re-normalize" ([Qdrant](https://huggingface.co/Qdrant/Qwen3-Embedding-0.6B-onnx)); EmbeddingGemma 768 → 512/256/128 costs 61.15 → 60.71/59.68/58.23 multilingual MTEB ([card](https://huggingface.co/google/embeddinggemma-300m)); arctic-m-v2 MRL "is 256 dimensions", ~3% degradation for 3x smaller ([card](https://huggingface.co/Snowflake/snowflake-arctic-embed-m-v2.0)). gte-modernbert-base (768) and bge-m3 (1024) are not described as MRL-trained on their cards.

### Inferences
- Storage per row: 384-d vector 1,544 B; 768-d 3,080 B; 1024-d 4,104 B; 1024-d halfvec 2,056 B. Moving from 384 to 1024 roughly 2.7x the vector bytes and HNSW size; halfvec halves that.
- Keeping `Vector(384)` is possible with Qwen3-Embedding (truncate 1024 → 384 and re-normalize, within its 32–1024 MRL range) — no schema change, but quality at 384 was not published by Qwen. EmbeddingGemma's nearest MRL points are 512 or 256 (384 is not a trained point). Arctic-m-v2 goes to 256.
- Because nothing is in production here, changing `Vector(384)` to another size is an Alembic revision plus a full re-embed; re-embed wall time = rows / measured items-per-second (section 3). E.g. at the measured rate, 100k chunks of ~128 tokens costs RE_EMBED_EXAMPLE.
- Store L2-normalized vectors and use cosine or inner-product ops consistently; truncated MRL vectors must be re-normalized after truncation.

### Gaps
- No source found giving Qwen3-Embedding-0.6B quality at exactly 384 or 256 dims.

## 6. Long inputs: max sequence lengths and cost of 8k-token inputs on CPU

### Takeaway
LONG_TAKEAWAY

### Cited Findings
- Max lengths: multilingual-e5-small 512; bge-reranker-base 512; ms-marco-MiniLM 512; EmbeddingGemma 2048 ([card](https://huggingface.co/google/embeddinggemma-300m)); gte-modernbert-base and gte-reranker-modernbert-base 8192 ([card](https://huggingface.co/Alibaba-NLP/gte-modernbert-base)); arctic-m-v2 8192 ([card](https://huggingface.co/Snowflake/snowflake-arctic-embed-m-v2.0)); Qwen3-Embedding / Qwen3-Reranker 32K (reranker recommended max_length 8192) ([Qwen3-Embedding](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [onnx-community reranker](https://huggingface.co/onnx-community/Qwen3-Reranker-0.6B-ONNX)); jina-reranker-v2 1024 per its card (not re-verified here); bge-m3 8192.
- The ST benchmark's long workload (IMDB x4, ~9.6k characters) is where backend rankings diverge most, and it advises benchmarking with representative input lengths. — [ST efficiency docs](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)
LONG_FINDINGS

### Inferences
LONG_INFERENCES

### Gaps
- Did not measure 8k inputs for Qwen3-Embedding/Qwen3-Reranker (memory limit of the test container); no published CPU numbers for 8k inputs found.

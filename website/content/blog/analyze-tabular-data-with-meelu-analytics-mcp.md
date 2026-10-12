---
title: "How to Analyze Tabular Data with AI Using meelu-analytics-mcp"
description: "A practical guide to analyzing CSV exports with Claude, Cursor or any MCP-capable assistant: why pasting a spreadsheet into a chatbot goes wrong, how to set up the free meelu-analytics-mcp server, the workflow from first question to trusted answer, and the kinds of data it works on."
date: "2026-09-26"
metaTitle: "Analyze Tabular Data with AI Using meelu-analytics-mcp"
metaDescription: "How to analyze CSV and spreadsheet data with Claude or any MCP assistant using the free meelu-analytics-mcp server: setup, workflow, trust levels and examples."
tags: ["meelu-analytics", "data-analysis", "mcp"]
---
## Quick answer

Export your data as CSV, install the free and open source [meelu-analytics-mcp](https://github.com/shubham303/meelu-analytics-mcp) server, and ask your AI assistant questions in plain English. The server loads the file into a local DuckDB database and runs the statistics itself. Your assistant only sees the results. Every answer comes with a trust level and caveats, and when the data cannot support a question, the server declines instead of giving you a number.

Most business questions are sitting in a table somewhere: an orders export, a CRM download, a GA4 report, a list of bank transactions. The hard part is not getting the file. It is getting a correct answer out of it without spending a day in pivot tables.

## Why pasting a CSV into a chatbot goes wrong

You can drop a CSV into ChatGPT or Claude and ask about it. For a few hundred rows and a simple question, that works. Past that, two things break.

**The file does not fit.** A 3,000-row CSV is roughly 60,000 tokens. The model reads part of it, or reads all of it once and then has to read it again for every follow-up question. Ten questions about one small file can cost more than half a million input tokens. At 30,000 rows it stops fitting at all, and the model answers from whatever slice it managed to read.

**The model guesses at math.** When a language model reads rows and reports "conversion is about 23% for referrals", it produced that number the same way it produces a sentence. It is often close. Sometimes it is wrong, and it sounds exactly as confident either way. Anything that needs a real statistical test, such as whether a drop is significant, cannot be done by reading. The model can only describe a test it did not run.

Both problems come from asking the AI to be the calculator. The fix is to let it operate a calculator instead.

## How meelu-analytics-mcp works

MCP (Model Context Protocol) is an open standard that lets an AI assistant call external tools. meelu-analytics-mcp is one of those tools: a server with 45 analysis functions that runs on your own machine.

The flow looks like this:

1. You point it at one or more CSV files. It loads them into a local DuckDB database once.
2. Your assistant sends small commands, such as "profile this table" or "compare the four weeks before and after March 5".
3. The server runs real code on every row and sends back a short, structured result.
4. Your assistant turns that result into an answer for you.

Three design choices do most of the work:

- **The method is picked from your data.** If you ask whether two columns are related, the server chooses the test from the column types and data shape, and records which one it used. Same data, same question, same answer.
- **Every result has a trust block.** Each answer carries a confidence level (high, moderate, low, none or unassessed) and written caveats like "small sample" or "association is not causation".
- **It can refuse.** When the data cannot support the question, the result comes back declined, with the reason. A tool that can say "I can't tell" is the only kind whose confident answers mean anything.

Your rows stay on your machine. The assistant sees aggregates and test results, not your customer list.

## Set it up

Setup takes about ten minutes. One command from the [README](https://github.com/shubham303/meelu-analytics-mcp) installs the server, asks which assistant you use and writes the config for you. It supports Claude Code, Claude Desktop, OpenAI Codex, Cursor, Windsurf, VS Code (Copilot), Gemini CLI, Grok CLI, OpenCode and Zed. Any other assistant that reads a standard MCP config also works.

It is MIT licensed. There is no account, no API key and no paid tier.

Use a desktop assistant for local files. Cloud assistants such as Claude on the web cannot start a program on your laptop, so connecting them means exposing the server over the network, and then your data does leave your machine.

## Prepare your data

The server reads CSV. Almost every business tool can export one.

- **One row per thing.** One row per order, per customer, per lead or per day. If a row mixes several things, split it into separate files.
- **Clear column names.** `order_date` and `total` are better than `Column F`.
- **Several files are fine.** Name them together, for example orders and line items, and the server detects how they join.
- **Keep what the question needs.** Drop personal fields you do not need, like emails and phone numbers.

## The workflow, from first question to trusted answer

You do not call the tools yourself. You ask your assistant a question and it picks the tools. It still helps to know what happens underneath, because that is how you check the answer.

**1. Load and profile.** Start with something like *"Load orders.csv and tell me what's in it."* The assistant calls `create_session`, then `profile`. You get the columns, their types, blanks and ranges. Read this before you ask anything else. Many wrong answers start with a date column read as text or a total stored with a currency symbol.

**2. Ask descriptive questions first.** *"Revenue by month and channel."* *"Average order value by country."* These run as `group_aggregate` or plain SQL through `run_sql`. They are exact, and they answer more questions than people expect.

**3. Test before you believe a difference.** Raw averages often suggest a finding that is not there. Ask *"Is that difference real?"* and the assistant calls `analyze_association` or `compare_periods`, which run a proper significance test. For example, on a demo Shopify file, marketplace orders averaged $89.36 against $74.70 for the online store. The test said the gap was within what chance alone would produce. A few very large bulk orders made the average look higher.

**4. Go deeper when the question needs it.** The same conversation can move into:

| You ask | What runs underneath |
|---|---|
| "Who are my best customers?" | `rfm` scores every customer on recency, frequency and spend, and names the segments |
| "What sells together?" | `market_basket` finds product pairs that appear together far more often than chance |
| "When did traffic change?" | `detect_changepoints` finds the date a series shifted |
| "Which rows look wrong?" | `detect_outliers` flags records that do not fit, for you to check |
| "Will this lead close? Will this customer churn?" | `train_classifier` trains a model and scores it on rows it never saw, then `explain_prediction` shows what drove each score |
| "What does next quarter look like?" | `forecast` projects forward with a confidence band that widens the further out it goes |
| "How do monthly cohorts retain?" | `retention_cohorts` builds the retention grid by signup period |
| "Does X actually cause Y?" | `causal_effect` adjusts for other variables and caps its own confidence on observational data |

**5. Read the trust level, not just the number.** A "low" result with a short-history caveat is a direction, not a fact. A declined result is the answer: the data cannot tell you. Do not ask the assistant to guess anyway.

A useful habit: first ask a question you already know the answer to. If the result matches, you know the data loaded correctly. Then ask the one you don't know.

## What people use it for

Each of these started as a full walkthrough on a realistic demo dataset. Every number came from a recorded tool result.

- **Shopify orders:** on 3,305 orders from 900 customers, 24% of customers produced 58.7% of revenue, and customers whose first order used a discount came back at 60.3% against 78.8% for full-price buyers.
- **GA4 and Search Console:** a significance test confirmed a 31.7% organic traffic drop after a core update was real, traced it to one page, and found 37 queries ranking just off page one.
- **Google and Meta ads:** across 3,496 campaign-days, click-through held for about five weeks per creative and then fell 31–38%, and an outlier check caught four days of broken conversion tracking.
- **CRM leads:** on 3,000 closed leads, whether a demo happened mattered far more than anything else (45.4% conversion with one, 12.3% without), and replying within 24 hours doubled the win rate.
- **SaaS churn:** accounts under one login a week churned at 44.1% against 1.1% above six, and the causal check cut the apparent effect of onboarding from 25.4 points to about 12.5.
- **Hotel bookings:** OTA bookings cancelled at 61.3% against 5.1% for direct bookings, and non-refundable deposits cut cancellations to 2.4%.
- **Real estate sales:** on 3,497 home sales, the model separated features that move price from ones that only correlate with it, and flagged the sales that looked mispriced.
- **Email campaigns:** across 455 campaigns, subject lines of 26–39 characters opened best, and abandoned-cart emails earned $0.82 per recipient against about a penny for newsletters.
- **Business expenses:** on 4,692 transactions from an accounting export, it found about $18,000 in duplicate payments and a 45% vendor price rise nobody had noticed.
- **Chatbot upload against the engine:** the same five questions on a 3,000-row file, asked both ways. Reading the raw file drifted by up to 9 points on group rates and could not run a real test. The engine returned exact, repeatable numbers for a fraction of the tokens.

## Honest limits

- **One table per analysis.** Related files can be joined into one table first with `join`, but it is a careful spreadsheet analyst, not a data warehouse.
- **CSV only, for now.** Excel, Parquet and JSON are on the roadmap. Save as CSV first.
- **Short histories give humble forecasts.** Eighteen months of monthly revenue produced a low-trust forecast with a wide band. That is the correct answer. More history makes the band narrower.
- **Correlation is labelled as correlation.** The server will tell you retargeting has a lower cost per acquisition. It will also say that does not prove retargeting caused it. If you need proof, it will point you to an experiment.

## FAQ

### Do I need to know statistics?

No. You ask in plain English and the assistant picks the tools. You do need to read the caveats. If a result has a small-sample warning, that warning is part of the answer.

### How much data do I need?

Descriptive questions work from a few hundred rows. Prediction models get much better past a couple of thousand. Forecasts need at least two full seasonal cycles, so two or more years of monthly data.

### How big a file can it handle?

Hundreds of thousands of rows on a normal laptop. Very large files may be refused rather than sampled.

### Is my data private?

Yes, when you use a desktop assistant. The server runs locally and reads files from your disk. The assistant sees totals and test results, and the specific rows it asks for, not the whole file.

### Is it really free?

Yes. It is MIT licensed and built on free libraries: DuckDB, scikit-learn, statsmodels, SHAP and DoWhy. There is no paid version.

## Try it on your own data

Pick one export you already look at every month. Install the server from the [meelu-analytics-mcp README](https://github.com/shubham303/meelu-analytics-mcp), load the file, and ask the question you usually answer with a pivot table. Then ask whether the difference is real.

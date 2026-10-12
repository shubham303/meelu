---
title: "Why we're building Meelu in the open"
description: "What Meelu is, who it's for, and why we build it in the open, starting with an open source analytics MCP server."
date: "2026-09-03"
tags: ["meelu", "open-source", "building-in-public"]
---

## Quick answer

**Update, October 2026:** the desktop app is out for macOS and Windows and needs a Meelu account. It audits your site, clusters and tracks keywords, drafts web pages and finds conversations to join, and it suggests while you decide. Outreach was dropped. Crawling and the agent run on your computer, while site data and third-party data lookups live on Meelu's server. meelu-analytics-mcp is the open source piece; the app itself is not open source. The post below is the original from September.

Meelu is an upcoming desktop app where an AI marketing agent runs your marketing — site crawls and SEO audits, data analysis, outreach drafts, and social listening — locally on your machine, with your approval on every action that leaves it. It's built as a set of MCP servers that are released as open source while the app is developed; meelu-analytics-mcp is available now, and the app itself is a few months out.

Meelu is a desktop app where an AI agent runs your marketing: it crawls and audits your site, answers analytical questions about your data, manages outreach campaigns, and listens for mentions of your product across Reddit, Hacker News, Bluesky and YouTube. It runs locally, your data stays on your machine, and nothing is published or sent without your approval.

It is not ready yet. It will be in a few months. This site exists in the meantime, and here's why.

## Who it's for

Meelu is for teams that want marketing capacity without adding headcount or an agency retainer for it. Most of that work is legible and repeatable: crawl the site, find the issues, write the briefs, watch the mentions, send the follow-ups. That's exactly the kind of work an agent harness is good at, if you give it the right tools — and it leaves you and your team the part that actually needs you: the judgment calls.

## Why the tools ship first

Meelu is built as a set of MCP servers — one per capability. The site crawler is a server. The analytics engine is a server. Listening is a server. The app is a harness that wires them to an agent and a UI.

That architecture has a nice consequence: each server is useful on its own, with any MCP-capable agent, before the app exists. So instead of building for months in silence, we're releasing the servers as they mature. [meelu-analytics-mcp](https://github.com/shubham303/meelu-analytics-mcp) is out now, and more will follow.

If you use the tools, you're already using Meelu — just without the desk they'll eventually sit on.

## What to expect here

This blog is where we write about what we learn along the way: technical SEO from the perspective of someone building a crawler, what deterministic analysis over MCP looks like, how to make an agent that drafts outreach without being spammy. If any of that sounds useful, [download the app](/download) and the posts land here as we go.

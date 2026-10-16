"use client";

import { useState } from "react";
import { RefreshCw, Square } from "lucide-react";
import { Button, Input } from "@demo/components/ui";
import type { Crawl } from "./tracked";

export function CrawlButton({ crawl }: { crawl: Crawl }) {
  const { status, running, stopping, canCrawl, start, stop } = crawl;
  const everCrawled = !!status?.lastCrawledAt;

  return (
    <Button
      onClick={() => void (running ? stop() : start())}
      disabled={running ? stopping : !canCrawl}
      title={!running && !canCrawl ? "Crawling runs in the Meelu app, from your own machine." : undefined}
    >
      {running ? (
        <>
          <Square className="mr-2 h-4 w-4" />
          {stopping ? "Stopping…" : "Stop crawl"}
        </>
      ) : (
        <>
          <RefreshCw className="mr-2 h-4 w-4" />
          {everCrawled ? "Crawl again" : "Crawl website"}
        </>
      )}
    </Button>
  );
}

export function CrawlNotes({ crawl }: { crawl: Crawl }) {
  const { note, running, canCrawl, needsSitemap, start } = crawl;
  const [sitemapUrl, setSitemapUrl] = useState("");

  if (running || !canCrawl || (!note && !needsSitemap)) return null;

  return (
    <div className="space-y-2">
      {note && <p className="text-xs text-sub">{note}</p>}

      {needsSitemap && (
        <form
          className="flex flex-col gap-1"
          onSubmit={(e) => {
            e.preventDefault();
            const url = sitemapUrl.trim();
            if (!url) return;
            setSitemapUrl("");
            void start({ sitemapUrls: [url] });
          }}
        >
          <div className="flex items-center gap-2">
            <Input
              className="w-72"
              value={sitemapUrl}
              onChange={(e) => setSitemapUrl(e.target.value)}
              placeholder="https://example.com/sitemap.xml"
              aria-label="Sitemap URL"
            />
            <Button type="submit" disabled={!sitemapUrl.trim()}>
              Use this sitemap
            </Button>
          </div>
          <span className="text-xs text-faint">
            No sitemap was found. Point at one and it is remembered for later crawls.
          </span>
        </form>
      )}
    </div>
  );
}

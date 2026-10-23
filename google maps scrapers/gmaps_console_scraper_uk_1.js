/* =====================================================================
   GOOGLE MAPS LEAD SCRAPER  -  Firefox DevTools Console edition
   =====================================================================
   WHAT IT DOES
   - Runs one Google Maps search per entry in SEARCHES (no page reloads,
     so the console script keeps running).
   - Auto-scrolls the results list until "You've reached the end".
   - Opens every listing and captures: name, address, phone, website.
   - Emails are ONLY captured when they appear on the Google Maps page
     itself (mailto links / visible text in the place panel).
     No external websites are visited.
   - Saves everything to window.__GMAPS_RESULTS__ and downloads
     gmaps_leads_uk_1.csv + gmaps_leads_uk_1.json when finished (or stopped).

   HOW TO RUN
   1. Open https://www.google.com/maps in Firefox (accept the consent
      screen once if it appears).
   2. Press F12 -> Console. Paste this ENTIRE script, press Enter.
   3. Progress box appears bottom-right. "Stop" aborts early and still
      lets you download what was collected.
   4. Tip: set MAX_RESULTS_PER_SEARCH = 10 first for a quick dry run.
   ===================================================================== */
(() => {
  'use strict';

  /* ---------- guards ---------- */
  if (window.__GMAPS_SCRAPER_RUNNING__) {
    console.warn('[gmaps] Already running. Reload the Maps tab to reset.');
    return;
  }
  if (!/(^|\.)google\.[a-z.]+$/i.test(location.hostname) || !location.pathname.startsWith('/maps')) {
    console.error('[gmaps] Open https://www.google.com/maps first, then paste this script.');
    return;
  }
  window.__GMAPS_SCRAPER_RUNNING__ = true;

  /* =========================  CONFIG  ========================= */
  // Top 50 UK cities and large towns by population.
  const TOP_50_CITIES = [
    'London, UK', 'Birmingham, UK', 'Manchester, UK', 'Glasgow, UK', 'Liverpool, UK',
    'Leeds, UK', 'Sheffield, UK', 'Edinburgh, UK', 'Bristol, UK', 'Leicester, UK',
    'Coventry, UK', 'Bradford, UK', 'Cardiff, UK', 'Belfast, UK', 'Nottingham, UK',
    'Kingston upon Hull, UK', 'Newcastle upon Tyne, UK', 'Stoke-on-Trent, UK', 'Southampton, UK', 'Derby, UK',
    'Portsmouth, UK', 'Brighton, UK', 'Plymouth, UK', 'Northampton, UK', 'Reading, UK',
    'Luton, UK', 'Wolverhampton, UK', 'Bolton, UK', 'Aberdeen, UK', 'Bournemouth, UK',
    'Norwich, UK', 'Swindon, UK', 'Swansea, UK', 'Milton Keynes, UK', 'Southend-on-Sea, UK',
    'Middlesbrough, UK', 'Sunderland, UK', 'Peterborough, UK', 'Warrington, UK', 'Oxford, UK',
    'Huddersfield, UK', 'Slough, UK', 'York, UK', 'Poole, UK', 'Ipswich, UK',
    'Telford, UK', 'Cambridge, UK', 'Dundee, UK', 'Gloucester, UK', 'Blackpool, UK',
  ];
  const SEARCH_TEMPLATE = 'Internet marketing service in {city}';
  const SEARCHES = TOP_50_CITIES.map(c => SEARCH_TEMPLATE.replace('{city}', c));

  const MAX_RESULTS_PER_SEARCH = 15;   // only the top N results per search
  const GRAB_EMAILS     = true;        // capture emails shown on the Maps page itself
  const SCROLL_PAUSE_MS = 1100;        // pause between list scrolls
  const MAX_NO_GROWTH   = 5;           // stop scrolling after N checks with no new results
  const ACTION_DELAY_MS = [600, 1400]; // random human-ish delay between UI actions

  /* =========================  STATE  ========================= */
  const ROWS = [];
  let STOP = false;
  let finished = false;
  let uiStatus = null, uiCount = null, uiCsv = null, uiJson = null;

  window.__GMAPS_RESULTS__ = ROWS;                 // live results array
  window.__GMAPS_STOP__ = () => { STOP = true; };  // stop from console too

  /* =========================  HELPERS  ========================= */
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const rand = ([a, b]) => Math.round(a + Math.random() * (b - a));
  const uniq = arr => [...new Set(arr)];
  const log = (...args) => console.log('%c[gmaps]', 'color:#16a34a;font-weight:700', ...args);

  const FEED_LINK = 'div[role="feed"] a[href*="/maps/place"]';
  const placeLinks = () => [...document.querySelectorAll(FEED_LINK)];
  const collect = () => uniq(placeLinks().map(a => a.href));
  const endOfList = feed => /reached the end of the list/i.test(feed.textContent || '');

  function wait(fn, timeout = 15000, interval = 250) {
    return new Promise(resolve => {
      const t0 = Date.now();
      const tick = () => {
        let v = null;
        try { v = fn(); } catch (e) { /* ignore */ }
        if (v) return resolve(v);
        if (Date.now() - t0 >= timeout) return resolve(null);
        setTimeout(tick, interval);
      };
      tick();
    });
  }

  /* =========================  UI OVERLAY  ========================= */
  function buildUI() {
    const box = document.createElement('div');
    box.style.cssText =
      'position:fixed;bottom:18px;right:18px;z-index:2147483647;' +
      'background:rgba(15,23,42,0.92);color:#e2e8f0;' +
      'font:12px/1.6 ui-monospace,Menlo,Consolas,monospace;' +
      'padding:14px 16px;border-radius:12px;width:330px;' +
      'box-shadow:0 10px 40px rgba(0,0,0,0.45);border:1px solid #334155';
    box.innerHTML =
      '<div style="font-weight:700;font-size:13px;margin-bottom:8px">Google Maps lead scraper</div>' +
      '<div id="gm-status">starting...</div>' +
      '<div id="gm-count" style="margin-top:6px;color:#94a3b8"></div>' +
      '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">' +
        '<button id="gm-stop">Stop</button>' +
        '<button id="gm-csv" style="display:none">Download CSV</button>' +
        '<button id="gm-json" style="display:none">Download JSON</button>' +
      '</div>';
    document.body.appendChild(box);

    const bstyle =
      'cursor:pointer;background:#1e293b;color:#e2e8f0;border:1px solid #334155;' +
      'border-radius:6px;padding:5px 10px;font:12px ui-monospace,monospace';
    box.querySelectorAll('button').forEach(b => { b.style.cssText = bstyle; });

    uiStatus = box.querySelector('#gm-status');
    uiCount  = box.querySelector('#gm-count');
    uiCsv    = box.querySelector('#gm-csv');
    uiJson   = box.querySelector('#gm-json');

    box.querySelector('#gm-stop').onclick = () => {
      STOP = true;
      setStatus('Stopping after the current step...');
    };
    uiCsv.onclick  = () => download('gmaps_leads_uk_1.csv', toCSV(ROWS), 'text/csv');
    uiJson.onclick = () => download('gmaps_leads_uk_1.json', JSON.stringify(ROWS, null, 2), 'application/json');
  }

  function setStatus(t) { if (uiStatus) uiStatus.textContent = t; }
  function bumpCount()  { if (uiCount) uiCount.textContent = 'Saved rows: ' + ROWS.length; }

  /* =========================  SEARCH + LIST  ========================= */
  function spaNav(path) {
    try {
      history.pushState({}, '', 'https://www.google.com' + path);
      window.dispatchEvent(new PopStateEvent('popstate'));
    } catch (e) {
      console.warn('[gmaps] URL navigation failed:', e);
    }
  }

  async function runSearch(query) {
    log('Search:', query);
    const firstBefore = collect()[0] || '';

    const input = document.querySelector('#searchboxinput');
    const btn = document.querySelector('#searchbox-searchbutton');
    if (input && btn) {
      input.focus();
      input.value = query;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      btn.click();
    } else {
      spaNav('/maps/search/' + encodeURIComponent(query));
    }

    // Wait until the results list actually changes to the new search.
    const sawNew = await wait(() => {
      const h = collect();
      return (h.length && h[0] !== firstBefore) ? true : null;
    }, 20000, 300);

    if (!sawNew) {
      log('Search box method may have failed, retrying via URL navigation...');
      spaNav('/maps/search/' + encodeURIComponent(query));
      await wait(() => document.querySelector(FEED_LINK), 20000, 300);
    }

    await sleep(1200);
    const hrefs = await loadAllResults(MAX_RESULTS_PER_SEARCH);
    log('Places found:', hrefs.length);
    return hrefs;
  }

  async function loadAllResults(max) {
    const first = await wait(() => document.querySelector(FEED_LINK), 25000, 250);
    if (!first) return [];

    let hrefs = collect();
    let last = -1;
    let noGrowth = 0;

    for (let i = 0; i < 250; i++) {
      const feed = document.querySelector('div[role="feed"]');
      if (!feed) break;
      hrefs = collect();
      if (max && hrefs.length >= max) return hrefs.slice(0, max);
      if (endOfList(feed)) return hrefs;
      if (hrefs.length === last) {
        noGrowth++;
        if (noGrowth >= MAX_NO_GROWTH) return hrefs;
      } else {
        noGrowth = 0;
        last = hrefs.length;
      }
      feed.scrollBy(0, 2000);
      await sleep(SCROLL_PAUSE_MS);
    }
    return hrefs;
  }

  /* =========================  PLACE DETAILS  ========================= */
  function findLink(href) {
    const base = href.split('?')[0];
    const links = placeLinks();
    return links.find(a => a.href === href) ||
           links.find(a => a.href.split('?')[0] === base) ||
           null;
  }

  async function openPlace(href) {
    let link = findLink(href);
    if (!link) { await backToList(); link = findLink(href); }
    if (!link) return false;

    const before = location.href;
    link.click();
    const ok = await wait(() => {
      return (location.href !== before &&
              /\/maps\/place\//.test(location.href) &&
              document.querySelector('h1')) ? true : null;
    }, 12000, 250);
    return !!ok;
  }

  async function backToList() {
    if (document.querySelector(FEED_LINK)) return; // list still visible, nothing to do
    let guard = 0;
    while (!document.querySelector(FEED_LINK) && guard++ < 8) {
      const back = document.querySelector('button[aria-label="Back"], button[data-tooltip="Back"]');
      if (back) back.click();
      else history.back();
      await sleep(900);
    }
    await wait(() => document.querySelector(FEED_LINK), 10000, 250);
    await sleep(500);
  }

  function extractPlace(href) {
    const h1 = document.querySelector('h1');
    const link = findLink(href);
    const name = (h1 && h1.textContent.trim()) ||
                 (link && link.getAttribute('aria-label')) || '';

    const phoneBtn = document.querySelector('button[data-item-id^="phone:tel:"]');
    const phone = phoneBtn
      ? ((phoneBtn.getAttribute('data-item-id') || '').replace('phone:tel:', '') ||
         phoneBtn.textContent.trim())
      : '';

    const siteA = document.querySelector('a[data-item-id="authority"]');
    const website = siteA ? siteA.href : '';

    const addrBtn = document.querySelector('button[data-item-id="address"]');
    let address = '';
    if (addrBtn) {
      const t = addrBtn.querySelector('.Io6YTe');
      address = (t && t.textContent
        ? t.textContent
        : addrBtn.textContent.replace(/^\s*Address\s*/i, '')).trim();
    }

    return { name: name, phone: phone, website: website, address: address, mapsUrl: href.split('?')[0] };
  }

  /* =================  EMAIL FROM MAPS PAGE ONLY  ================= */
  const BAD_EMAIL =
    /(\.png|\.jpe?g|\.gif|\.webp|\.svg|\.css|\.js$|example\.com|example\.org|yourdomain|your-?domain|domain\.com|email\.com|sentry|wixpress|wix\.com|godaddy|no-?reply|donotreply|postmaster|abuse@|spam@|@2x|@3x|u003|schema|cloudflare|sitelock|test@|user@)/i;

  // Scans ONLY what Google Maps itself renders for the open place:
  // mailto: links + email-like text in the place panel (reviews removed).
  function extractEmailFromPage() {
    const out = [];
    const seen = new Set();
    const push = raw => {
      const e = String(raw || '').toLowerCase().replace(/^[-._]+|[-._]+$/g, '');
      if (e && !seen.has(e) && e.length <= 96 && !BAD_EMAIL.test(e)) {
        seen.add(e);
        out.push(e);
      }
    };

    // 1) mailto: links anywhere on the page (safest signal)
    document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
      const raw = (a.getAttribute('href') || '').replace(/^mailto:/i, '').split('?')[0];
      try { push(decodeURIComponent(raw)); } catch (e) { push(raw); }
    });

    // 2) email-like text inside the place detail panel
    const h1 = document.querySelector('h1');
    const panel = (h1 && h1.closest('div[role="main"]')) || document.querySelector('div[role="main"]');
    if (panel) {
      const clone = panel.cloneNode(true);
      clone.querySelectorAll('[data-review-id], [data-facet-id]').forEach(el => el.remove());
      const text = clone.innerText || clone.textContent || '';
      let m;
      const plain = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
      while ((m = plain.exec(text))) push(m[0]);
    }

    return out;
  }

  /* =========================  EXPORT  ========================= */
  function toCSV(rows) {
    const esc = v => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const head = 'search,name,address,phone,website,email,maps_url';
    const body = rows
      .map(r => [r.search, r.name, r.address, r.phone, r.website, r.email, r.maps_url].map(esc).join(','))
      .join('\n');
    return '\uFEFF' + head + '\n' + body; // BOM so Excel opens UTF-8 correctly
  }

  function download(name, content, mime) {
    try {
      const blob = new Blob([content], { type: mime + ';charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 10000);
    } catch (e) {
      console.warn('[gmaps] download failed for', name, e);
    }
  }

  function finish() {
    if (finished) return;
    finished = true;
    setStatus(STOP ? 'Stopped - downloads ready.' : 'Done - downloading files.');
    bumpCount();
    if (uiCsv) { uiCsv.style.display = ''; uiJson.style.display = ''; }
    console.log('[gmaps] Finished. Rows:', ROWS.length, '(also available as window.__GMAPS_RESULTS__)');
    if (ROWS.length) console.table(ROWS.slice(0, 25));
    download('gmaps_leads_uk_1.csv', toCSV(ROWS), 'text/csv');
    download('gmaps_leads_uk_1.json', JSON.stringify(ROWS, null, 2), 'application/json');
    window.__GMAPS_SCRAPER_RUNNING__ = false;
  }

  /* =========================  MAIN  ========================= */
  async function main() {
    buildUI();
    setStatus('Starting (' + SEARCHES.length + ' searches)...');

    for (let si = 0; si < SEARCHES.length; si++) {
      if (STOP) break;
      const q = SEARCHES[si];

      let hrefs = [];
      try {
        hrefs = await runSearch(q);
      } catch (e) {
        console.error('[gmaps] search error for', q, e);
        continue;
      }

      for (let i = 0; i < hrefs.length; i++) {
        if (STOP) break;
        const href = hrefs[i];
        setStatus('Search ' + (si + 1) + '/' + SEARCHES.length + ': "' + q + '"\n' +
                  'Place ' + (i + 1) + '/' + hrefs.length);

        try {
          const opened = await openPlace(href);
          if (!opened) {
            console.warn('[gmaps] could not open, skipping:', href);
            continue;
          }
          await sleep(800);

          const d = extractPlace(href);
          let email = '';
          if (GRAB_EMAILS) {
            const emails = extractEmailFromPage();
            if (emails.length) email = emails.join('; ');
          }

          ROWS.push({
            search: q,
            name: d.name,
            address: d.address,
            phone: d.phone,
            website: d.website,
            email: email,
            maps_url: d.mapsUrl,
          });
          bumpCount();
          log('Saved:', d.name || href, email ? ('| ' + email) : '');
        } catch (e) {
          console.warn('[gmaps] place error', e);
        }

        await backToList();
        await sleep(rand(ACTION_DELAY_MS));
      }
    }
    finish();
  }

  main().catch(e => {
    console.error('[gmaps] fatal:', e);
    finish();
  });
})();

import type { AnalyticsReport, AnalyticsSession, AnalyticsSource } from "@demo/lib/types";
import { ago, DAY, HOUR } from "../rand";
import { SITE_ID } from "./site";

export const SESSIONS: AnalyticsSession[] = [
  {
    id: "as_1",
    createdAt: ago(5 * DAY),
    updatedAt: ago(4 * HOUR),
    siteId: SITE_ID,
    title: "Why did churn spike in August?",
    about: "Stripe subscription export plus the support ticket log. Looking for what the churned accounts had in common.",
    sessionKey: "sess_9f2a71",
  },
  {
    id: "as_2",
    createdAt: ago(12 * DAY),
    updatedAt: ago(9 * DAY),
    siteId: SITE_ID,
    title: "Template downloads → signups",
    about: "Do people who download an invoice template convert better than blog readers? GA4 export joined to signups.",
    sessionKey: "sess_1c04be",
  },
];

export const SOURCES: AnalyticsSource[] = [
  { id: "src_1", createdAt: ago(5 * DAY), updatedAt: ago(5 * DAY), siteId: SITE_ID, sessionId: "as_1", name: "stripe_subscriptions_2026.csv", filePath: "analytics/as_1/stripe_subscriptions_2026.csv" },
  { id: "src_2", createdAt: ago(5 * DAY), updatedAt: ago(5 * DAY), siteId: SITE_ID, sessionId: "as_1", name: "support_tickets.csv", filePath: "analytics/as_1/support_tickets.csv" },
  { id: "src_3", createdAt: ago(12 * DAY), updatedAt: ago(12 * DAY), siteId: SITE_ID, sessionId: "as_2", name: "ga4_landing_pages_180d.csv", filePath: "analytics/as_2/ga4_landing_pages_180d.csv" },
  { id: "src_4", createdAt: ago(12 * DAY), updatedAt: ago(12 * DAY), siteId: SITE_ID, sessionId: "as_2", name: "signups.csv", filePath: "analytics/as_2/signups.csv" },
];

export const CSV: Record<string, string> = {
  "analytics/as_1/stripe_subscriptions_2026.csv": [
    "customer_id,plan,mrr_usd,started_at,cancelled_at,cancel_reason,bank_connected,invoices_sent_90d,country",
    "cus_A1F3,solo,12,2025-11-04,,,true,14,US",
    "cus_B7Q2,solo,12,2026-01-19,2026-08-12,too_expensive,false,2,US",
    "cus_C9M8,team,29,2025-09-30,,,true,41,UK",
    "cus_D4K1,solo,12,2026-03-02,2026-08-03,missing_feature,false,0,CA",
    "cus_E2P6,solo,12,2026-02-11,2026-08-21,switched,false,3,US",
    "cus_F8L5,studio,59,2025-06-14,,,true,88,US",
    "cus_G3N9,solo,12,2026-04-25,,,true,9,AU",
    "cus_H6R4,solo,12,2026-05-30,2026-08-09,too_expensive,false,1,US",
    "cus_J1T7,team,29,2026-01-08,,,true,27,DE",
    "cus_K5V2,solo,12,2026-06-17,2026-08-28,other,true,6,UK",
    "cus_L9W3,solo,12,2025-12-01,,,true,18,US",
    "cus_M2X8,solo,12,2026-07-03,2026-08-15,missing_feature,false,0,US",
  ].join("\n"),
  "analytics/as_1/support_tickets.csv": [
    "ticket_id,customer_id,opened_at,category,resolved_hours,sentiment",
    "T-1041,cus_B7Q2,2026-07-29,bank_feed,52,negative",
    "T-1042,cus_D4K1,2026-07-30,mobile_app,120,negative",
    "T-1050,cus_C9M8,2026-08-01,invoice,4,neutral",
    "T-1058,cus_H6R4,2026-08-04,bank_feed,71,negative",
    "T-1061,cus_E2P6,2026-08-06,billing,9,neutral",
    "T-1077,cus_M2X8,2026-08-10,mobile_app,96,negative",
    "T-1080,cus_F8L5,2026-08-11,reports,6,positive",
    "T-1093,cus_K5V2,2026-08-20,bank_feed,38,negative",
  ].join("\n"),
  "analytics/as_2/ga4_landing_pages_180d.csv": [
    "landing_page,sessions,engaged_sessions,signups_started,signups_completed",
    "/templates/invoice,41230,19811,1104,612",
    "/,64110,38122,2911,1988",
    "/blog/how-to-invoice-as-a-freelancer,21873,10401,398,171",
    "/blog/quarterly-estimated-taxes-explained,19022,9012,301,140",
    "/compare/quickbooks,16554,9877,712,433",
    "/tools/invoice-generator,15211,8812,644,287",
    "/pricing,23890,17102,2210,1602",
    "/templates/late-payment-reminder,10440,5102,231,118",
    "/blog/deductible-expenses-freelancers,13320,6011,187,71",
  ].join("\n"),
  "analytics/as_2/signups.csv": [
    "signup_id,date,first_landing_page,plan,converted_to_paid",
    "su_1,2026-03-02,/templates/invoice,solo,true",
    "su_2,2026-03-02,/,solo,false",
    "su_3,2026-03-03,/pricing,team,true",
    "su_4,2026-03-03,/blog/quarterly-estimated-taxes-explained,solo,true",
    "su_5,2026-03-04,/compare/quickbooks,solo,true",
    "su_6,2026-03-04,/templates/invoice,solo,false",
    "su_7,2026-03-05,/tools/invoice-generator,solo,false",
    "su_8,2026-03-05,/,team,true",
  ].join("\n"),
};

function reportHtml(title: string, body: string): string {
  return `<!doctype html><html><head><meta charset="utf-8"><style>
body{font-family:ui-sans-serif,system-ui,sans-serif;color:#1f2d3d;background:#fffdf7;margin:0;padding:24px;line-height:1.55}
h1{font-size:22px;margin:0 0 6px}h2{font-size:15px;margin:22px 0 8px;text-transform:uppercase;letter-spacing:.04em;color:#5b6b7f}
p{margin:0 0 10px;font-size:14px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #e6e1d1}th{color:#5b6b7f;font-weight:500}
.bar{display:flex;align-items:center;gap:8px;font-size:13px;margin:4px 0}.bar span:first-child{width:170px;color:#5b6b7f}.bar i{display:block;height:10px;background:#2563eb;border-radius:3px}
.note{font-size:12px;color:#8fa0b3;margin-top:18px}
</style></head><body><h1>${title}</h1>${body}</body></html>`;
}

export const REPORTS: AnalyticsReport[] = [
  {
    id: "rp_1",
    createdAt: ago(4 * HOUR),
    updatedAt: ago(4 * HOUR),
    siteId: SITE_ID,
    sessionId: "as_1",
    title: "August churn: what the cancelled accounts share",
    createdBy: "agent",
    html: reportHtml(
      "August churn: what the cancelled accounts share",
      `<p>Six of the twelve Solo accounts in the export cancelled in August. Five of the six never connected a bank; the one that did had opened a bank-feed ticket ten days before cancelling. Among accounts that kept going, every one has a bank connected.</p>
<h2>Bank connected vs churn</h2>
<div class="bar"><span>Bank connected · churned</span><i style="width:8%"></i> 1 of 7</div>
<div class="bar"><span>No bank · churned</span><i style="width:100%"></i> 5 of 5</div>
<h2>Cancel reason</h2>
<table><tr><th>Reason</th><th>Accounts</th><th>Median invoices in 90d</th></tr>
<tr><td>too_expensive</td><td>2</td><td>1.5</td></tr><tr><td>missing_feature</td><td>2</td><td>0</td></tr><tr><td>switched</td><td>1</td><td>3</td></tr><tr><td>other</td><td>1</td><td>6</td></tr></table>
<h2>Support tickets before cancelling</h2>
<p>Four of the six churned accounts opened a ticket in the three weeks before cancelling: three about bank feeds, one about the mobile app. Median resolution time on those tickets was 71 hours, against 6 hours for tickets from retained accounts.</p>
<p class="note">Trust: moderate. Twelve rows is a small sample; the bank-connection pattern is strong enough to act on, the reason breakdown is not.</p>`,
    ),
  },
  {
    id: "rp_2",
    createdAt: ago(9 * DAY),
    updatedAt: ago(9 * DAY),
    siteId: SITE_ID,
    sessionId: "as_2",
    title: "Template pages convert 2.4× better than blog posts",
    createdBy: "agent",
    html: reportHtml(
      "Template pages convert 2.4× better than blog posts",
      `<p>Sessions landing on a template page complete signup at 1.4%, against 0.6% for sessions landing on a blog post. The comparison pages are the strongest of all at 2.6%, but they receive a quarter of the traffic.</p>
<h2>Signup completion by landing page type</h2>
<div class="bar"><span>Comparison pages</span><i style="width:100%"></i> 2.6%</div>
<div class="bar"><span>Pricing</span><i style="width:96%"></i> 2.5%</div>
<div class="bar"><span>Template pages</span><i style="width:54%"></i> 1.4%</div>
<div class="bar"><span>Tools</span><i style="width:73%"></i> 1.9%</div>
<div class="bar"><span>Blog posts</span><i style="width:23%"></i> 0.6%</div>
<h2>What to do with it</h2>
<p>The blog posts are where the traffic is; the templates are where the conversion is. The cheapest move is to put the relevant template inside the three biggest posts, above the fold, rather than writing more posts.</p>
<p class="note">Trust: high for the ranking, moderate for the exact rates — GA4 sampled two of the nine rows.</p>`,
    ),
  },
];

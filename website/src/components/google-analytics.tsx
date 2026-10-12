import Script from "next/script";

// Loads gtag.js when the browser is idle rather than right after hydration,
// so the 170 KB tag never competes with the first paint on slow phones.
export function GoogleAnalytics({ gaId }: { gaId: string }) {
  return (
    <>
      <Script id="ga-init" strategy="lazyOnload">
        {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '${gaId}');`}
      </Script>
      <Script
        id="ga"
        strategy="lazyOnload"
        src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`}
      />
    </>
  );
}

import { site } from "@/lib/site";

export const softwareApplicationSchema = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "@id": `${site.url}/#software`,
  name: site.name,
  description: site.description,
  url: site.url,
  downloadUrl: `${site.url}/download`,
  applicationCategory: "BusinessApplication",
  operatingSystem: "macOS, Windows",
  publisher: { "@id": `${site.url}/#organization` },
  offers: {
    "@type": "Offer",
    url: `${site.url}/pricing`,
    priceCurrency: "USD",
    price: 0.4,
    priceSpecification: {
      "@type": "UnitPriceSpecification",
      price: 0.4,
      priceCurrency: "USD",
      unitText: "website per day",
    },
  },
};

export const softwareApplicationJson = JSON.stringify(softwareApplicationSchema);

import "../globals.css";
import { RootDocument, rootMetadata } from "@/components/root-document";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

export const metadata = rootMetadata;

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <RootDocument>
      <SiteHeader />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </RootDocument>
  );
}

import "../globals.css";
import { RootDocument, rootMetadata } from "@/components/root-document";

export const metadata = rootMetadata;

export default function DemoRootLayout({ children }: { children: React.ReactNode }) {
  return <RootDocument>{children}</RootDocument>;
}

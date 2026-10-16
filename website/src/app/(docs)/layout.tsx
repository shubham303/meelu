import "./docs.css";
import { RootProvider } from "fumadocs-ui/provider/next";
import { RootDocument, rootMetadata } from "@/components/root-document";

export const metadata = rootMetadata;

export default function DocsRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <RootDocument>
      <RootProvider theme={{ enabled: false }}>{children}</RootProvider>
    </RootDocument>
  );
}

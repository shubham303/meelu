import { DocsLayout } from "fumadocs-ui/layouts/docs";
import { Logo } from "@/components/logo";
import { docsSource } from "@/lib/docs-source";

export default function DocsSectionLayout({ children }: { children: React.ReactNode }) {
  return (
    <DocsLayout
      tree={docsSource.getPageTree()}
      nav={{ title: <Logo size={20} />, url: "/" }}
      themeSwitch={{ enabled: false }}
      links={[
        { text: "Pricing", url: "/pricing" },
        { text: "Blog", url: "/blog" },
        { text: "Download", url: "/download" },
      ]}
    >
      {children}
    </DocsLayout>
  );
}

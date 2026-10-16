import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { RootDocument, rootMetadata } from "@/components/root-document";

export const metadata: Metadata = {
  ...rootMetadata,
  title: "Page not found · Meelu",
  robots: { index: false },
};

export default function GlobalNotFound() {
  return (
    <RootDocument>
      <main className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
        <p className="text-sm text-sub">404</p>
        <h1 className="font-display text-3xl text-ink">This page does not exist</h1>
        <div className="flex gap-3 text-sm">
          <Link href="/" className="rounded-lg bg-accent px-3.5 py-2 font-medium text-white hover:bg-accent-hi">
            Go home
          </Link>
          <Link href="/docs" className="rounded-lg border border-edge px-3.5 py-2 text-ink hover:bg-panel2">
            Read the docs
          </Link>
        </div>
      </main>
    </RootDocument>
  );
}

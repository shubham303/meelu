import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Demo sign-in",
  robots: { index: false, follow: false },
};

export default async function DemoSignIn({ searchParams }: { searchParams: Promise<{ app?: string }> }) {
  const { app } = await searchParams;
  const name = app?.slice(0, 40) || "the app";
  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-6">
      <div className="max-w-md rounded-2xl border border-edge bg-panel p-8 text-center">
        <h1 className="font-display text-2xl text-ink">{name} is connected in the demo</h1>
        <p className="mt-3 text-sm text-sub text-pretty">
          In Meelu this tab is {name}&apos;s own sign-in page, run by Composio. You sign in there, Composio keeps the
          login, and Meelu asks before every write. Close this tab and press Check again on the Connections screen.
        </p>
        <Link href="/download" className="mt-6 inline-flex text-sm font-medium text-accent hover:underline">
          Download the app →
        </Link>
      </div>
    </main>
  );
}

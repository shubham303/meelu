import { Recovery } from "@/components/recovery";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-1 bg-bg px-4">
      <Recovery title="This page doesn't exist." hint="It may have moved or been removed. Go back, or head home." />
    </main>
  );
}

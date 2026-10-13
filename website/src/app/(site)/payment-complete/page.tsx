import type { Metadata } from "next";
import { CircleCheck, CircleX } from "lucide-react";

export const metadata: Metadata = {
  title: "Payment received",
  robots: { index: false, follow: false },
};

export default async function PaymentCompletePage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status } = await searchParams;
  const failed = status === "failed" || status === "cancelled";

  return (
    <section className="mx-auto flex w-full max-w-xl flex-col items-center px-6 py-24 text-center">
      {failed ? (
        <CircleX size={40} className="text-bad" />
      ) : (
        <CircleCheck size={40} className="text-accent" />
      )}
      <h1 className="mt-6 font-display text-3xl tracking-tight text-ink">
        {failed ? "The payment did not go through" : "Payment received"}
      </h1>
      <p className="mt-4 text-base text-sub text-pretty">
        {failed
          ? "Nothing was charged. Go back to the Meelu app and try again from the Credits page."
          : "You can close this tab and go back to the Meelu app. Your credits appear on the Credits page within a few seconds."}
      </p>
    </section>
  );
}

"use client";

import { useParams } from "next/navigation";
import { PageEnter } from "@/components/animate";
import { AnalyticsChatView } from "@/features/analytics/analytics-chat";
import { useIsApp } from "@/lib/use-app-mode";

export default function AnalyticsChatPage() {
  const { chatId } = useParams<{ chatId: string }>();
  const isApp = useIsApp();
  return (
    <PageEnter>
      <AnalyticsChatView key={chatId} chatId={chatId} canChat={isApp} />
    </PageEnter>
  );
}

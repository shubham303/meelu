"use client";

import { useParams } from "next/navigation";
import { PageEnter } from "@demo/components/animate";
import { AnalyticsChatView } from "@demo/features/analytics/analytics-chat";
import { useIsApp } from "@demo/lib/use-app-mode";

export default function AnalyticsChatPage() {
  const { chatId } = useParams<{ chatId: string }>();
  const isApp = useIsApp();
  return (
    <PageEnter>
      <AnalyticsChatView key={chatId} chatId={chatId} canChat={isApp} />
    </PageEnter>
  );
}

"use client";

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { PageEnter } from "@/components/animate";
import { AnalyticsChatView } from "@/features/analytics/analytics-chat";
import { onNewChat } from "@/features/analytics/chats";
import { useIsApp } from "@/lib/use-app-mode";

export default function AnalyticsPage() {
  const isApp = useIsApp();
  const [fresh, setFresh] = useState(0);

  useEffect(() => onNewChat(() => setFresh((n) => n + 1)), []);

  return (
    <PageEnter>
      {isApp ? (
        <AnalyticsChatView key={fresh} canChat />
      ) : (
        <EmptyState
          icon={BarChart3}
          title="The analyst runs in the Meelu app"
          hint="Open Meelu on your computer to ask questions. Past chats and saved reports are listed here on the web too."
        />
      )}
    </PageEnter>
  );
}

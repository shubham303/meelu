"use client";

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { EmptyState } from "@demo/components/ui";
import { PageEnter } from "@demo/components/animate";
import { AnalyticsChatView } from "@demo/features/analytics/analytics-chat";
import { onNewChat } from "@demo/features/analytics/chats";
import { useIsApp } from "@demo/lib/use-app-mode";

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
          hint="Open Meelu on your computer to ask questions. Past chats are listed here on the web too, and saved reports are on the Reports desk."
        />
      )}
    </PageEnter>
  );
}

import { Sidebar } from "@demo/components/sidebar";
import { BillingBanner } from "@demo/components/billing-banner";
import { AgentTasksProvider } from "./agent-tasks";
import { AgentRunsProvider } from "@demo/components/agent/run-rail";
import { MainFrame } from "./main-frame";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AgentRunsProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <AgentTasksProvider>
          <div className="flex min-w-0 flex-1 flex-col">
            <BillingBanner />
            <MainFrame>{children}</MainFrame>
          </div>
        </AgentTasksProvider>
      </div>
    </AgentRunsProvider>
  );
}

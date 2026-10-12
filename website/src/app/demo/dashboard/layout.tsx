import { Sidebar } from "@demo/components/sidebar";
import { AgentTasksProvider } from "./agent-tasks";
import { AgentRunsProvider } from "@demo/components/agent/run-rail";
import { MainFrame } from "./main-frame";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AgentRunsProvider>
      <div className="flex min-h-screen">
        <Sidebar />
        <AgentTasksProvider>
          <MainFrame>{children}</MainFrame>
        </AgentTasksProvider>
      </div>
    </AgentRunsProvider>
  );
}

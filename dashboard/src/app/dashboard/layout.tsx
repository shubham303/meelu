import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { sessionUserId } from "@/lib/server-session";
import { Sidebar } from "@/components/sidebar";
import { AgentTasksProvider } from "./agent-tasks";
import { AgentRunsProvider } from "@/components/agent/run-rail";
import { MainFrame } from "./main-frame";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const token = (await cookies()).get("meelu_session")?.value;
  if (!(await sessionUserId(token))) redirect("/login");

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

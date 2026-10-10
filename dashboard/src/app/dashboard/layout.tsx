import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { sessionUserId } from "@/lib/server-session";
import { Sidebar } from "@/components/sidebar";
import { BillingBanner } from "@/components/billing-banner";
import { UpdateBanner } from "@/components/update-banner";
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
          <div className="flex min-w-0 flex-1 flex-col">
            <UpdateBanner />
            <BillingBanner />
            <MainFrame>{children}</MainFrame>
          </div>
        </AgentTasksProvider>
      </div>
    </AgentRunsProvider>
  );
}

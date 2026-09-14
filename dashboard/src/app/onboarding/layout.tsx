import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { sessionUserId } from "@/lib/server-session";

export default async function OnboardingLayout({ children }: { children: React.ReactNode }) {
  const token = (await cookies()).get("meelu_session")?.value;
  if (!(await sessionUserId(token))) redirect("/login");
  return <>{children}</>;
}

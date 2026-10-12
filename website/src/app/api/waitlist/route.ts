import { joinWaitlist, normalizeEmail } from "@/lib/waitlist/store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PLATFORMS = new Set(["mac", "windows", "other"]);

export async function POST(request: Request) {
  let body: { email?: unknown; platform?: unknown; company?: unknown };
  try {
    body = await request.json();
  } catch {
    return Response.json({ message: "Send the email as JSON." }, { status: 400 });
  }

  if (typeof body.company === "string" && body.company.trim()) {
    return Response.json({ ok: true });
  }

  const email = normalizeEmail(body.email);
  if (!email) {
    return Response.json({ message: "That does not look like an email address." }, { status: 400 });
  }
  const platform =
    typeof body.platform === "string" && PLATFORMS.has(body.platform) ? body.platform : null;

  const result = await joinWaitlist(email, platform);
  if (!result.ok) {
    console.error("waitlist join failed:", result.detail);
    return Response.json(
      { message: "We could not save your email just now. Please try again in a minute." },
      { status: 503 },
    );
  }
  return Response.json({ ok: true });
}

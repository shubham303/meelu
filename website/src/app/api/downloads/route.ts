import { isCountryCode } from "@/lib/downloads/countries";
import { normalizeEmail, recordDownload } from "@/lib/downloads/store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BUILDS = new Set(["mac-arm64", "mac-x64", "windows-x64"]);

export async function POST(request: Request) {
  let body: { email?: unknown; country?: unknown; build?: unknown; company?: unknown };
  try {
    body = await request.json();
  } catch {
    return Response.json({ message: "Send the details as JSON." }, { status: 400 });
  }

  if (typeof body.company === "string" && body.company.trim()) {
    return Response.json({ ok: true });
  }

  const email = normalizeEmail(body.email);
  if (!email) {
    return Response.json({ message: "That does not look like an email address." }, { status: 400 });
  }
  if (!isCountryCode(body.country)) {
    return Response.json({ message: "Choose your country." }, { status: 400 });
  }
  if (typeof body.build !== "string" || !BUILDS.has(body.build)) {
    return Response.json({ message: "Unknown download." }, { status: 400 });
  }

  const result = await recordDownload(email, body.country, body.build);
  if (!result.ok) {
    console.error("download record failed:", result.detail);
    return Response.json({ message: "We could not save your details." }, { status: 503 });
  }
  return Response.json({ ok: true });
}

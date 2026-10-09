import { NextResponse, type NextRequest } from "next/server";
import { supabaseServer } from "@/lib/supabase/server";

const API = process.env.MEELU_API_URL ?? "http://localhost:8100";

function safeNext(value: string | null): string | null {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : null;
}

export async function GET(request: NextRequest) {
  const url = request.nextUrl;
  const code = url.searchParams.get("code");
  const failed = new URL("/login?error=auth", url.origin);
  if (!code) return NextResponse.redirect(failed);

  const supabase = await supabaseServer();
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);
  if (error || !data.session) return NextResponse.redirect(failed);

  const res = await fetch(`${API}/api/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accessToken: data.session.access_token }),
    cache: "no-store",
  });
  if (!res.ok) return NextResponse.redirect(failed);

  const body = (await res.json()) as { data?: { created?: boolean } };
  const fallback = body.data?.created ? "/onboarding" : "/dashboard";
  const response = NextResponse.redirect(
    new URL(safeNext(url.searchParams.get("next")) ?? fallback, url.origin),
  );
  for (const cookie of res.headers.getSetCookie()) response.headers.append("set-cookie", cookie);
  return response;
}

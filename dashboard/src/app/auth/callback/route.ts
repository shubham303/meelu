import { NextResponse, type NextRequest } from "next/server";
import { supabaseServer } from "@/lib/supabase/server";

const API = process.env.MEELU_API_URL ?? "http://localhost:8100";

const SAFE_PATH = /^\/(?![\/\\])[^\s\\]*$/;

function safeNext(value: string | null): string | null {
  return value && SAFE_PATH.test(value) ? value : null;
}

function redirectTo(path: string): NextResponse {
  return new NextResponse(null, { status: 303, headers: { Location: path } });
}

export async function GET(request: NextRequest) {
  const url = request.nextUrl;
  const code = url.searchParams.get("code");
  const failed = "/login?error=auth";
  if (!code) return redirectTo(failed);

  const supabase = await supabaseServer();
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);
  if (error || !data.session) return redirectTo(failed);

  const res = await fetch(`${API}/api/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accessToken: data.session.access_token }),
    cache: "no-store",
  });
  await supabase.auth.signOut({ scope: "local" });
  if (!res.ok) return redirectTo(failed);

  const body = (await res.json()) as { data?: { created?: boolean } };
  const fallback = body.data?.created ? "/onboarding" : "/dashboard";
  const response = redirectTo(safeNext(url.searchParams.get("next")) ?? fallback);
  for (const cookie of res.headers.getSetCookie()) response.headers.append("set-cookie", cookie);
  return response;
}

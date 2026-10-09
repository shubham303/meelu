import { NextResponse, type NextRequest } from "next/server";
import { isAppUserAgent } from "@/lib/app-mode";

const DOWNLOAD_URL = "https://meelu.tech/download";

export function proxy(request: NextRequest) {
  if (isAppUserAgent(request.headers.get("user-agent"))) return NextResponse.next();
  return new NextResponse(null, { status: 307, headers: { Location: DOWNLOAD_URL } });
}

export const config = {
  matcher: ["/((?!api/|auth/|_next|__next|favicon\\.ico|robots\\.txt).*)"],
};

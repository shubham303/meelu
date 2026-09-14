import { NextResponse, type NextRequest } from "next/server";
import { isAppUserAgent } from "@/lib/app-mode";

export function proxy(request: NextRequest) {
  if (isAppUserAgent(request.headers.get("user-agent"))) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/why", "/docs/:path*"],
};

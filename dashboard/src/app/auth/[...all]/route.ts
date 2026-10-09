import { toNextJsHandler } from "better-auth/next-js";
import { authServer } from "@/lib/auth-server";

export async function GET(request: Request) {
  return toNextJsHandler(authServer()).GET(request);
}

export async function POST(request: Request) {
  return toNextJsHandler(authServer()).POST(request);
}

import "server-only";

const API = process.env.MEELU_API_URL ?? "http://localhost:8100";

export async function sessionUserId(token: string | null | undefined): Promise<string | null> {
  if (!token) return null;
  try {
    const res = await fetch(`${API}/api/auth/me`, {
      headers: { cookie: `meelu_session=${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { data?: { id?: string } };
    return body.data?.id ?? null;
  } catch {
    return null;
  }
}

export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const { getMigrations } = await import("better-auth/db/migration");
  const { authOptions } = await import("@/lib/auth-server");
  const { runMigrations } = await getMigrations(authOptions());
  await runMigrations();
}

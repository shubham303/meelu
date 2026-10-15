import { ok, type Route } from "../core";
import { scopeResponse } from "../agent/scope";

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/agent\/scope$/, (_m, q) => ok(scopeResponse(q.get("action") ?? q.get("name") ?? "", q.get("desks") ?? ""))],
];

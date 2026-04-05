import { randomUUID } from "node:crypto";
import type { Context, Next } from "hono";
import type { AppEnv } from "../app.js";

export async function requestLogger(c: Context<AppEnv>, next: Next) {
  const requestId = randomUUID();
  c.set("requestId", requestId);

  const start = Date.now();
  const method = c.req.method;
  const path = c.req.path;

  await next();

  const duration = Date.now() - start;
  const status = c.res.status;
  const userId = c.get("userId") ?? "-";

  console.log(
    JSON.stringify({
      requestId,
      method,
      path,
      status,
      duration,
      userId,
      timestamp: new Date().toISOString(),
    }),
  );
}

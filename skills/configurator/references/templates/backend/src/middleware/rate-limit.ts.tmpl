import type { Context, Next } from "hono";
import { SETTINGS } from "../services/settings.js";

interface RateLimitEntry {
  count: number;
  resetAt: number;
}

const store = new Map<string, RateLimitEntry>();

// Cleanup stale entries periodically
setInterval(() => {
  const now = Date.now();
  for (const [key, entry] of store) {
    if (entry.resetAt < now) store.delete(key);
  }
}, 60_000);

export function rateLimit(maxRequests?: number) {
  const max = maxRequests ?? SETTINGS.RATE_LIMIT_MAX_REQUESTS;
  const windowMs = SETTINGS.RATE_LIMIT_WINDOW_MS;

  return async (c: Context, next: Next) => {
    const ip = c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
    const key = `${ip}:${c.req.path}`;
    const now = Date.now();

    let entry = store.get(key);

    if (!entry || entry.resetAt < now) {
      entry = { count: 0, resetAt: now + windowMs };
      store.set(key, entry);
    }

    entry.count++;

    c.header("X-RateLimit-Limit", String(max));
    c.header("X-RateLimit-Remaining", String(Math.max(0, max - entry.count)));
    c.header("X-RateLimit-Reset", String(Math.ceil(entry.resetAt / 1000)));

    if (entry.count > max) {
      return c.json(
        {
          type: "about:blank",
          title: "Too Many Requests",
          status: 429,
          detail: `Rate limit exceeded. Try again in ${Math.ceil((entry.resetAt - now) / 1000)} seconds.`,
        },
        429,
      );
    }

    await next();
  };
}

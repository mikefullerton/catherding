import type { Context, Next } from "hono";
import { verifyAccessToken } from "./session.js";
import type { AppEnv } from "../app.js";

export async function extractAuth(c: Context<AppEnv>, next: Next) {
  const authHeader = c.req.header("Authorization");

  if (authHeader?.startsWith("Bearer ")) {
    const token = authHeader.slice(7);
    try {
      const payload = await verifyAccessToken(token);
      c.set("userId", payload.sub);
      c.set("userEmail", payload.email);
      c.set("userRole", payload.role as "admin" | "user");
    } catch {
      // Token invalid — continue without auth
    }
  }

  await next();
}

export async function requireAuth(c: Context<AppEnv>, next: Next) {
  const authHeader = c.req.header("Authorization");

  if (!authHeader?.startsWith("Bearer ")) {
    return c.json({ type: "about:blank", title: "Unauthorized", status: 401 }, 401);
  }

  const token = authHeader.slice(7);
  try {
    const payload = await verifyAccessToken(token);
    c.set("userId", payload.sub);
    c.set("userEmail", payload.email);
    c.set("userRole", payload.role as "admin" | "user");
  } catch {
    return c.json({ type: "about:blank", title: "Invalid or expired token", status: 401 }, 401);
  }

  await next();
}

export async function requireAdmin(c: Context<AppEnv>, next: Next) {
  const authHeader = c.req.header("Authorization");

  if (!authHeader?.startsWith("Bearer ")) {
    return c.json({ type: "about:blank", title: "Unauthorized", status: 401 }, 401);
  }

  const token = authHeader.slice(7);
  try {
    const payload = await verifyAccessToken(token);
    c.set("userId", payload.sub);
    c.set("userEmail", payload.email);
    c.set("userRole", payload.role as "admin" | "user");
  } catch {
    return c.json({ type: "about:blank", title: "Invalid or expired token", status: 401 }, 401);
  }

  if (c.get("userRole") !== "admin") {
    return c.json({ type: "about:blank", title: "Forbidden", status: 403 }, 403);
  }

  await next();
}

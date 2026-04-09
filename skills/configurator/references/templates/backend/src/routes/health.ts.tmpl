import { Hono } from "hono";
import { db } from "../db/client.js";
import { sql } from "drizzle-orm";

export const health = new Hono();

// GET /api/health
health.get("/", (c) => {
  return c.json({
    status: "ok",
    timestamp: new Date().toISOString(),
    version: "1.0.0",
  });
});

// GET /api/health/live
health.get("/live", (c) => {
  return c.json({ status: "ok" });
});

// GET /api/health/ready
health.get("/ready", async (c) => {
  try {
    await db.execute(sql`SELECT 1`);
    return c.json({ status: "ok", database: "connected" });
  } catch {
    return c.json({ status: "error", database: "disconnected" }, 503);
  }
});

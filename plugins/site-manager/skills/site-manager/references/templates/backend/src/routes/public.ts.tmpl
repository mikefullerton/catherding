import { Hono } from "hono";
import { getAllFlags } from "../services/feature-flags.js";

export const publicRoutes = new Hono();

// GET /api/public/flags — returns enabled flags for client-side feature gating
publicRoutes.get("/flags", async (c) => {
  const flags = await getAllFlags();
  const enabledFlags = flags
    .filter((f) => f.enabled)
    .map((f) => ({ key: f.key, rules: f.rules }));

  return c.json({ flags: enabledFlags });
});

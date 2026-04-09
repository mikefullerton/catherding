import { Hono } from "hono";
import { z } from "zod";
import { requireAdmin } from "../../auth/middleware.js";
import {
  getAllFlags,
  getFlag,
  setFlag,
  deleteFlag,
} from "../../services/feature-flags.js";
import type { AppEnv } from "../../app.js";

export const adminFlags = new Hono<AppEnv>();
adminFlags.use("/*", requireAdmin);

const createFlagSchema = z.object({
  key: z.string().min(1).max(100).regex(/^[a-z0-9_-]+$/),
  description: z.string().optional(),
  enabled: z.boolean().default(false),
  rules: z.record(z.unknown()).optional(),
});

const updateFlagSchema = z.object({
  description: z.string().optional(),
  enabled: z.boolean().optional(),
  rules: z.record(z.unknown()).optional(),
});

// GET /api/admin/flags
adminFlags.get("/", async (c) => {
  const flags = await getAllFlags();
  return c.json({ flags });
});

// POST /api/admin/flags
adminFlags.post("/", async (c) => {
  const body = createFlagSchema.safeParse(await c.req.json());
  if (!body.success) {
    return c.json(
      { type: "about:blank", title: "Validation error", status: 400, errors: body.error.issues },
      400,
    );
  }

  const existing = await getFlag(body.data.key);
  if (existing) {
    return c.json({ type: "about:blank", title: "Flag already exists", status: 409 }, 409);
  }

  const flag = await setFlag(body.data);
  return c.json({ flag }, 201);
});

// PATCH /api/admin/flags/:key
adminFlags.patch("/:key", async (c) => {
  const key = c.req.param("key");
  const body = updateFlagSchema.safeParse(await c.req.json());
  if (!body.success) {
    return c.json(
      { type: "about:blank", title: "Validation error", status: 400, errors: body.error.issues },
      400,
    );
  }

  const existing = await getFlag(key);
  if (!existing) {
    return c.json({ type: "about:blank", title: "Flag not found", status: 404 }, 404);
  }

  const flag = await setFlag({ key, ...body.data });
  return c.json({ flag });
});

// DELETE /api/admin/flags/:key
adminFlags.delete("/:key", async (c) => {
  const key = c.req.param("key");

  const existing = await getFlag(key);
  if (!existing) {
    return c.json({ type: "about:blank", title: "Flag not found", status: 404 }, 404);
  }

  await deleteFlag(key);
  return c.json({ deleted: true });
});

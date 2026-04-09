import { Hono } from "hono";
import { z } from "zod";
import { db } from "../../db/client.js";
import { feedbackSubmissions } from "../../db/schema.js";
import { eq, desc, sql } from "drizzle-orm";
import { requireAdmin } from "../../auth/middleware.js";
import type { AppEnv } from "../../app.js";

export const adminFeedback = new Hono<AppEnv>();
adminFeedback.use("/*", requireAdmin);

const paginationSchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  status: z.enum(["new", "reviewed", "resolved", "archived"]).optional(),
});

const updateFeedbackSchema = z.object({
  status: z.enum(["new", "reviewed", "resolved", "archived"]).optional(),
  adminNotes: z.string().optional(),
});

// GET /api/admin/feedback
adminFeedback.get("/", async (c) => {
  const query = paginationSchema.safeParse(c.req.query());
  if (!query.success) {
    return c.json(
      { type: "about:blank", title: "Validation error", status: 400, errors: query.error.issues },
      400,
    );
  }

  const { page, limit, status } = query.data;
  const offset = (page - 1) * limit;

  const where = status ? eq(feedbackSubmissions.status, status) : undefined;

  const [results, countResult] = await Promise.all([
    db
      .select()
      .from(feedbackSubmissions)
      .where(where)
      .orderBy(desc(feedbackSubmissions.createdAt))
      .limit(limit)
      .offset(offset),
    db
      .select({ count: sql<number>`count(*)::int` })
      .from(feedbackSubmissions)
      .where(where),
  ]);
  const count = countResult[0]?.count ?? 0;

  return c.json({
    feedback: results.map((f) => ({
      id: f.id,
      userId: f.userId,
      email: f.email,
      category: f.category,
      subject: f.subject,
      body: f.body,
      status: f.status,
      adminNotes: f.adminNotes,
      createdAt: f.createdAt.toISOString(),
      updatedAt: f.updatedAt.toISOString(),
    })),
    pagination: { page, limit, total: count },
  });
});

// PATCH /api/admin/feedback/:id
adminFeedback.patch("/:id", async (c) => {
  const id = c.req.param("id");
  const body = updateFeedbackSchema.safeParse(await c.req.json());
  if (!body.success) {
    return c.json(
      { type: "about:blank", title: "Validation error", status: 400, errors: body.error.issues },
      400,
    );
  }

  const [existing] = await db
    .select()
    .from(feedbackSubmissions)
    .where(eq(feedbackSubmissions.id, id));

  if (!existing) {
    return c.json({ type: "about:blank", title: "Feedback not found", status: 404 }, 404);
  }

  const [updated] = await db
    .update(feedbackSubmissions)
    .set({ ...body.data, updatedAt: new Date() })
    .where(eq(feedbackSubmissions.id, id))
    .returning();
  if (!updated) throw new Error("Failed to update feedback");

  return c.json({
    id: updated.id,
    status: updated.status,
    adminNotes: updated.adminNotes,
    updatedAt: updated.updatedAt.toISOString(),
  });
});

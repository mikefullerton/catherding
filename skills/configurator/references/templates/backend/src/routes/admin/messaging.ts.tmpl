import { Hono } from "hono";
import { z } from "zod";
import { db } from "../../db/client.js";
import { messageLog } from "../../db/schema.js";
import { desc, sql } from "drizzle-orm";
import { requireAdmin } from "../../auth/middleware.js";
import { sendEmail, sendSms } from "../../services/messaging.js";
import type { AppEnv } from "../../app.js";

export const adminMessaging = new Hono<AppEnv>();
adminMessaging.use("/*", requireAdmin);

const sendEmailSchema = z.object({
  channel: z.literal("email"),
  to: z.string().email(),
  subject: z.string().min(1).max(500),
  body: z.string().min(1),
});

const sendSmsSchema = z.object({
  channel: z.literal("sms"),
  to: z.string().min(1),
  body: z.string().min(1),
});

const sendSchema = z.discriminatedUnion("channel", [sendEmailSchema, sendSmsSchema]);

const logPaginationSchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
});

// POST /api/admin/messaging/send
adminMessaging.post("/send", async (c) => {
  const body = sendSchema.safeParse(await c.req.json());
  if (!body.success) {
    return c.json(
      { type: "about:blank", title: "Validation error", status: 400, errors: body.error.issues },
      400,
    );
  }

  const data = body.data;

  if (data.channel === "email") {
    const result = await sendEmail(data.to, data.subject, data.body);
    return c.json(result, result.status === "sent" ? 200 : 500);
  } else {
    const result = await sendSms(data.to, data.body);
    return c.json(result, result.status === "sent" ? 200 : 500);
  }
});

// GET /api/admin/messaging/log
adminMessaging.get("/log", async (c) => {
  const query = logPaginationSchema.safeParse(c.req.query());
  if (!query.success) {
    return c.json(
      { type: "about:blank", title: "Validation error", status: 400, errors: query.error.issues },
      400,
    );
  }

  const { page, limit } = query.data;
  const offset = (page - 1) * limit;

  const [results, countResult] = await Promise.all([
    db
      .select()
      .from(messageLog)
      .orderBy(desc(messageLog.createdAt))
      .limit(limit)
      .offset(offset),
    db.select({ count: sql<number>`count(*)::int` }).from(messageLog),
  ]);
  const count = countResult[0]?.count ?? 0;

  return c.json({
    messages: results.map((m) => ({
      id: m.id,
      channel: m.channel,
      recipientEmail: m.recipientEmail,
      recipientPhone: m.recipientPhone,
      subject: m.subject,
      status: m.status,
      sentAt: m.sentAt?.toISOString() ?? null,
      createdAt: m.createdAt.toISOString(),
    })),
    pagination: { page, limit, total: count },
  });
});

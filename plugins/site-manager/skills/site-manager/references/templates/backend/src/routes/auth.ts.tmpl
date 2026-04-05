import { Hono } from "hono";
import { z } from "zod";
import { db } from "../db/client.js";
import { users } from "../db/schema.js";
import { eq } from "drizzle-orm";
import { hashPassword, verifyPassword } from "../auth/password.js";
import {
  createAccessToken,
  createRefreshToken,
  rotateRefreshToken,
  revokeRefreshToken,
} from "../auth/session.js";
import { requireAuth } from "../auth/middleware.js";
import type { AppEnv } from "../app.js";

export const auth = new Hono<AppEnv>();

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  displayName: z.string().min(1).max(255).optional(),
});

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string(),
});

const refreshSchema = z.object({
  refreshToken: z.string(),
});

// POST /api/auth/register
auth.post("/register", async (c) => {
  const body = registerSchema.safeParse(await c.req.json());
  if (!body.success) {
    return c.json(
      { type: "about:blank", title: "Validation error", status: 400, errors: body.error.issues },
      400,
    );
  }

  const { email, password, displayName } = body.data;

  const [existing] = await db.select().from(users).where(eq(users.email, email));
  if (existing) {
    return c.json({ type: "about:blank", title: "Email already registered", status: 409 }, 409);
  }

  const passwordHash = await hashPassword(password);
  const [user] = await db
    .insert(users)
    .values({ email, passwordHash, displayName })
    .returning();
  if (!user) throw new Error("Failed to create user");

  const accessToken = await createAccessToken({ sub: user.id, email: user.email, role: user.role });
  const refreshToken = await createRefreshToken(user.id);

  return c.json({ accessToken, refreshToken, user: { id: user.id, email: user.email, role: user.role } }, 201);
});

// POST /api/auth/login
auth.post("/login", async (c) => {
  const body = loginSchema.safeParse(await c.req.json());
  if (!body.success) {
    return c.json(
      { type: "about:blank", title: "Validation error", status: 400, errors: body.error.issues },
      400,
    );
  }

  const { email, password } = body.data;

  const [user] = await db.select().from(users).where(eq(users.email, email));
  if (!user || !user.passwordHash) {
    return c.json({ type: "about:blank", title: "Invalid credentials", status: 401 }, 401);
  }

  const valid = await verifyPassword(password, user.passwordHash);
  if (!valid) {
    return c.json({ type: "about:blank", title: "Invalid credentials", status: 401 }, 401);
  }

  const accessToken = await createAccessToken({ sub: user.id, email: user.email, role: user.role });
  const refreshToken = await createRefreshToken(user.id);

  return c.json({ accessToken, refreshToken, user: { id: user.id, email: user.email, role: user.role } });
});

// POST /api/auth/refresh
auth.post("/refresh", async (c) => {
  const body = refreshSchema.safeParse(await c.req.json());
  if (!body.success) {
    return c.json({ type: "about:blank", title: "Missing refresh token", status: 400 }, 400);
  }

  const { refreshToken: oldToken } = body.data;

  // We need the userId to rotate — decode from old access token or require it
  // For simplicity, require an Authorization header with the expired access token
  const authHeader = c.req.header("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return c.json({ type: "about:blank", title: "Authorization header required", status: 401 }, 401);
  }

  // Decode without verifying expiration to get the userId
  const tokenParts = authHeader.slice(7).split(".");
  if (tokenParts.length !== 3) {
    return c.json({ type: "about:blank", title: "Invalid token format", status: 401 }, 401);
  }

  let userId: string;
  try {
    const payload = JSON.parse(atob(tokenParts[1] ?? ""));
    userId = payload.sub;
  } catch {
    return c.json({ type: "about:blank", title: "Invalid token", status: 401 }, 401);
  }

  const newRefreshToken = await rotateRefreshToken(oldToken, userId);
  if (!newRefreshToken) {
    return c.json({ type: "about:blank", title: "Invalid or expired refresh token", status: 401 }, 401);
  }

  const [user] = await db.select().from(users).where(eq(users.id, userId));
  if (!user) {
    return c.json({ type: "about:blank", title: "User not found", status: 401 }, 401);
  }

  const accessToken = await createAccessToken({ sub: user.id, email: user.email, role: user.role });

  return c.json({ accessToken, refreshToken: newRefreshToken });
});

// POST /api/auth/logout
auth.post("/logout", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const refreshToken = (body as { refreshToken?: string }).refreshToken;
  if (refreshToken) {
    await revokeRefreshToken(refreshToken);
  }
  return c.json({ ok: true });
});

// GET /api/auth/me
auth.get("/me", requireAuth, async (c) => {
  const userId = c.get("userId");

  const [user] = await db.select().from(users).where(eq(users.id, userId));
  if (!user) {
    return c.json({ type: "about:blank", title: "User not found", status: 404 }, 404);
  }

  return c.json({
    id: user.id,
    email: user.email,
    role: user.role,
    displayName: user.displayName,
    avatarUrl: user.avatarUrl,
    createdAt: user.createdAt.toISOString(),
  });
});

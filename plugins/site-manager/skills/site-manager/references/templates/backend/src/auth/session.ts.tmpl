import { SignJWT, jwtVerify } from "jose";
import { randomBytes, createHash } from "node:crypto";
import { db } from "../db/client.js";
import { refreshTokens } from "../db/schema.js";
import { eq, and, isNull } from "drizzle-orm";
import { env } from "../config/env.js";

const secret = new TextEncoder().encode(env.JWT_SECRET);
const ACCESS_TOKEN_TTL = "15m";
const REFRESH_TOKEN_DAYS = 30;

export interface TokenPayload {
  sub: string;
  email: string;
  role: string;
}

export async function createAccessToken(payload: TokenPayload): Promise<string> {
  return new SignJWT({ email: payload.email, role: payload.role })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(payload.sub)
    .setIssuedAt()
    .setExpirationTime(ACCESS_TOKEN_TTL)
    .sign(secret);
}

export async function verifyAccessToken(token: string): Promise<TokenPayload> {
  const { payload } = await jwtVerify(token, secret);
  return {
    sub: payload.sub!,
    email: payload.email as string,
    role: payload.role as string,
  };
}

function hashToken(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

export async function createRefreshToken(userId: string): Promise<string> {
  const raw = randomBytes(32).toString("hex");
  const tokenHash = hashToken(raw);
  const expiresAt = new Date(Date.now() + REFRESH_TOKEN_DAYS * 24 * 60 * 60 * 1000);

  await db.insert(refreshTokens).values({ userId, tokenHash, expiresAt });

  return raw;
}

export async function rotateRefreshToken(
  oldRaw: string,
  userId: string,
): Promise<string | null> {
  const oldHash = hashToken(oldRaw);

  const [existing] = await db
    .select()
    .from(refreshTokens)
    .where(
      and(
        eq(refreshTokens.tokenHash, oldHash),
        eq(refreshTokens.userId, userId),
        isNull(refreshTokens.revokedAt),
      ),
    );

  if (!existing || existing.expiresAt < new Date()) {
    return null;
  }

  const newRaw = randomBytes(32).toString("hex");
  const newHash = hashToken(newRaw);
  const expiresAt = new Date(Date.now() + REFRESH_TOKEN_DAYS * 24 * 60 * 60 * 1000);

  const [newToken] = await db
    .insert(refreshTokens)
    .values({ userId, tokenHash: newHash, expiresAt })
    .returning();
  if (!newToken) throw new Error("Failed to create refresh token");

  await db
    .update(refreshTokens)
    .set({ revokedAt: new Date(), replacedByTokenId: newToken.id })
    .where(eq(refreshTokens.id, existing.id));

  return newRaw;
}

export async function revokeRefreshToken(raw: string): Promise<void> {
  const tokenHash = hashToken(raw);
  await db
    .update(refreshTokens)
    .set({ revokedAt: new Date() })
    .where(eq(refreshTokens.tokenHash, tokenHash));
}

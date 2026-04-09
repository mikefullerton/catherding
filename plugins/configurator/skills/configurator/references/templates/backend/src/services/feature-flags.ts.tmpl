import { db } from "../db/client.js";
import { featureFlags } from "../db/schema.js";
import { eq } from "drizzle-orm";

export interface FeatureFlag {
  id: string;
  key: string;
  description: string | null;
  enabled: boolean;
  rules: Record<string, unknown> | null;
  createdAt: Date;
  updatedAt: Date;
}

export async function getAllFlags(): Promise<FeatureFlag[]> {
  return db.select().from(featureFlags);
}

export async function getFlag(key: string): Promise<FeatureFlag | undefined> {
  const [flag] = await db.select().from(featureFlags).where(eq(featureFlags.key, key));
  return flag;
}

export async function setFlag(data: {
  key: string;
  description?: string;
  enabled?: boolean;
  rules?: Record<string, unknown>;
}): Promise<FeatureFlag> {
  const existing = await getFlag(data.key);

  if (existing) {
    const [updated] = await db
      .update(featureFlags)
      .set({
        ...(data.description !== undefined && { description: data.description }),
        ...(data.enabled !== undefined && { enabled: data.enabled }),
        ...(data.rules !== undefined && { rules: data.rules }),
        updatedAt: new Date(),
      })
      .where(eq(featureFlags.key, data.key))
      .returning();
    if (!updated) throw new Error("Failed to update feature flag");
    return updated;
  }

  const [created] = await db
    .insert(featureFlags)
    .values({
      key: data.key,
      description: data.description ?? null,
      enabled: data.enabled ?? false,
      rules: data.rules ?? null,
    })
    .returning();
  if (!created) throw new Error("Failed to create feature flag");
  return created;
}

export async function deleteFlag(key: string): Promise<void> {
  await db.delete(featureFlags).where(eq(featureFlags.key, key));
}

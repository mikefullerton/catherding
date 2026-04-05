import { db } from "./client.js";
import { users } from "./schema.js";
import { hashPassword } from "../auth/password.js";
import { eq } from "drizzle-orm";

async function seed() {
  const email = process.env.ADMIN_EMAIL;
  const password = process.env.ADMIN_PASSWORD;

  if (!email || !password) {
    console.error("ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required");
    process.exit(1);
  }

  if (password.length < 12) {
    console.error("ADMIN_PASSWORD must be at least 12 characters");
    process.exit(1);
  }

  const existing = await db.select().from(users).where(eq(users.email, email));

  if (existing.length > 0) {
    console.log(`Admin account ${email} already exists.`);
    process.exit(0);
  }

  const passwordHash = await hashPassword(password);

  await db.insert(users).values({
    email,
    passwordHash,
    role: "admin",
    displayName: "Admin",
    emailVerified: true,
  });

  console.log(`Admin account created: ${email}`);
  process.exit(0);
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});

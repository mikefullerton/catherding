import { cors } from "hono/cors";
import { env } from "../config/env.js";

const allowedOrigins = env.CORS_ORIGIN.split(",").map((url) => url.trim());

export const corsMiddleware = cors({
  origin: (origin) => {
    if (allowedOrigins.includes(origin)) return origin;
    if (env.NODE_ENV !== "production" && origin.startsWith("http://localhost:")) {
      return origin;
    }
    return null;
  },
  allowMethods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allowHeaders: ["Content-Type", "Authorization"],
  credentials: true,
  maxAge: 86400,
});

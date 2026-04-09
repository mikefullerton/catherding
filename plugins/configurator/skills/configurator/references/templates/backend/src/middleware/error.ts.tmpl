import type { Context } from "hono";
import type { StatusCode } from "hono/utils/http-status";

// RFC 9457 Problem Details
interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
}

export function errorHandler(err: Error, c: Context): Response {
  const requestId = c.get("requestId") as string | undefined;

  console.error(`[${requestId ?? "unknown"}] Unhandled error:`, err.message);

  const status: StatusCode = 500;
  const problem: ProblemDetails = {
    type: "about:blank",
    title: "Internal Server Error",
    status,
    ...(process.env.NODE_ENV !== "production" && { detail: err.message }),
    ...(requestId && { instance: `/errors/${requestId}` }),
  };

  return c.json(problem, status);
}

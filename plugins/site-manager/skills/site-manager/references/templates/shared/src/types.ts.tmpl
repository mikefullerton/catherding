// ── User ──────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  role: "admin" | "user";
  displayName: string | null;
  avatarUrl: string | null;
  emailVerified: boolean;
  createdAt: string;
}

// ── Auth ──────────────────────────────────────────────────────────────────

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  displayName?: string;
}

export interface AuthResponse extends AuthTokens {
  user: Pick<User, "id" | "email" | "role">;
}

// ── Feature Flags ────────────────────────────────────────────────────────

export interface FeatureFlag {
  id: string;
  key: string;
  description: string | null;
  enabled: boolean;
  rules: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface PublicFeatureFlag {
  key: string;
  rules: Record<string, unknown> | null;
}

// ── Messaging ────────────────────────────────────────────────────────────

export interface MessageLogEntry {
  id: string;
  channel: "email" | "sms";
  recipientEmail: string | null;
  recipientPhone: string | null;
  subject: string | null;
  status: "pending" | "sent" | "failed";
  sentAt: string | null;
  createdAt: string;
}

// ── Feedback ─────────────────────────────────────────────────────────────

export interface FeedbackSubmission {
  id: string;
  userId: string | null;
  email: string | null;
  category: string;
  subject: string | null;
  body: string;
  status: "new" | "reviewed" | "resolved" | "archived";
  adminNotes: string | null;
  createdAt: string;
  updatedAt: string;
}

// ── Pagination ───────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  pagination: {
    page: number;
    limit: number;
    total: number;
  };
  [key: string]: T[] | PaginatedResponse<T>["pagination"];
}

// ── API Error ────────────────────────────────────────────────────────────

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  errors?: Array<{ path: string[]; message: string }>;
}

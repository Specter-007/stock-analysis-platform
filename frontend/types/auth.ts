// Mirrors backend/app/auth/schemas.py, app/notifications/schemas.py,
// app/preferences/schemas.py, app/support/schemas.py.

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: "USER" | "ADMIN";
  email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface SessionInfo {
  id: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  user_agent: string | null;
  is_current: boolean;
}

export interface SessionListResponse {
  sessions: SessionInfo[];
}

export interface Preferences {
  timezone: string;
  default_benchmark: string;
  theme: "dark" | "light";
  email_notifications_enabled: boolean;
  research_notifications_enabled: boolean;
  marketing_consent: boolean;
  terms_accepted_at: string | null;
  privacy_accepted_at: string | null;
  onboarding_completed: boolean;
  onboarding_completed_at: string | null;
}

export interface Notification {
  id: string;
  type: "EXPERIMENT_COMPLETED" | "EXPERIMENT_FAILED" | "PAPER_PORTFOLIO_EVENT" | "SYSTEM";
  title: string;
  message: string;
  target_route: string | null;
  created_at: string;
  read_at: string | null;
}

export interface NotificationListResponse {
  notifications: Notification[];
  unread_count: number;
}

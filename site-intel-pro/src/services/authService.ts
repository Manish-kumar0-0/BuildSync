import type { User } from "@/app/types";
import { api, clearApiToken, hasApiToken, setApiToken, type ApiUser } from "./api";

export interface AuthCredentials {
  identifier: string;
  password: string;
}

export interface PasswordResetRequest {
  email: string;
}

const AUTH_STORAGE_KEY = "constructiq-auth";
const SESSION_STORAGE_KEY = "constructiq-session";
const ROLE_STORAGE_KEY = "constructiq-role";
const PROJECT_STORAGE_KEY = "constructiq-project";

function toRole(role: string): User["role"] {
  const roles: Record<string, User["role"]> = {
    WORKER: "Worker",
    FOREMAN: "Foreman",
    FIELD_ENGINEER: "Field Engineer",
    SITE_ENGINEER: "Site Engineer",
    SAFETY_OFFICER: "Safety Officer",
    QA_QC_ENGINEER: "QA/QC Engineer",
    MATERIAL_MANAGER: "Material Manager",
    DRIVER: "Driver",
    EQUIPMENT_MANAGER: "Equipment Manager",
    PROJECT_MANAGER: "Project Manager",
    ADMIN: "Admin",
  };
  return roles[role] ?? "Worker";
}

function toUser(user: ApiUser): User {
  const name = user.full_name || "BuildSync user";
  const firstName = name.split(/\s+/)[0] ?? name;
  return {
    id: String(user.id),
    name,
    email: user.email ?? "",
    phone: user.phone ?? "",
    role: toRole(user.role),
    firstName,
    status: "online",
  };
}

export const authService = {
  requestPasswordReset(email: string): Promise<{ message: string }> {
    return api.post("/api/auth/password-reset/request", { email });
  },
  verifyPasswordReset(email: string, otp: string): Promise<{ reset_token: string }> {
    return api.post("/api/auth/password-reset/verify", { email, otp });
  },
  completePasswordReset(email: string, resetToken: string, newPassword: string): Promise<{ message: string }> {
    return api.post("/api/auth/password-reset/complete", {
      email,
      reset_token: resetToken,
      new_password: newPassword,
    });
  },
  async signIn(credentials: AuthCredentials): Promise<User | null> {
    const response = await api.post<{ access_token: string; user: ApiUser }>("/api/auth/login", credentials);
    setApiToken(response.access_token);
    const currentUser = await api.get<ApiUser>("/api/auth/me");
    const authenticatedUser = toUser(currentUser);
    const projects = await api.get<Array<{ id: number }>>("/api/projects");
    authenticatedUser.projectId = projects[0] ? String(projects[0].id) : undefined;

    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(AUTH_STORAGE_KEY, "authenticated");
      window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(authenticatedUser));
      window.sessionStorage.setItem(ROLE_STORAGE_KEY, authenticatedUser.role);
      window.sessionStorage.setItem(PROJECT_STORAGE_KEY, authenticatedUser.projectId ?? "");
      window.localStorage.setItem(AUTH_STORAGE_KEY, "authenticated");
      window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(authenticatedUser));
      window.localStorage.setItem(ROLE_STORAGE_KEY, authenticatedUser.role);
      window.localStorage.setItem(PROJECT_STORAGE_KEY, authenticatedUser.projectId ?? "");
    }

    return authenticatedUser;
  },
  async restoreSession(): Promise<User | null> {
    if (!hasApiToken()) return null;
    const currentUser = await api.get<ApiUser>("/api/auth/me");
    const authenticatedUser = toUser(currentUser);
    const projects = await api.get<Array<{ id: number }>>("/api/projects");
    authenticatedUser.projectId = projects[0] ? String(projects[0].id) : undefined;

    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(AUTH_STORAGE_KEY, "authenticated");
      window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(authenticatedUser));
      window.sessionStorage.setItem(ROLE_STORAGE_KEY, authenticatedUser.role);
      window.sessionStorage.setItem(PROJECT_STORAGE_KEY, authenticatedUser.projectId ?? "");
      window.localStorage.setItem(AUTH_STORAGE_KEY, "authenticated");
      window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(authenticatedUser));
      window.localStorage.setItem(ROLE_STORAGE_KEY, authenticatedUser.role);
      window.localStorage.setItem(PROJECT_STORAGE_KEY, authenticatedUser.projectId ?? "");
    }
    return authenticatedUser;
  },
  logout(): void {
    if (typeof window === "undefined") return;
    [AUTH_STORAGE_KEY, SESSION_STORAGE_KEY, ROLE_STORAGE_KEY, PROJECT_STORAGE_KEY].forEach(key => {
      window.sessionStorage.removeItem(key);
      window.localStorage.removeItem(key);
    });
    clearApiToken();
  },
  async signOut(): Promise<void> {
    authService.logout();
  },
};

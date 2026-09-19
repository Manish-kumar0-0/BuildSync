const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").trim().replace(/\/$/, "");
const TOKEN_KEY = "buildsync-access-token";

export class ApiError extends Error {
  readonly status: number;
  readonly detail?: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY) ?? window.localStorage.getItem(TOKEN_KEY);
}

export function hasApiToken(): boolean {
  return getToken() !== null;
}

export function setApiToken(token: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearApiToken(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body && !(typeof FormData !== "undefined" && init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "BuildSync backend is unavailable");
  }

  const text = await response.text();
  let body: unknown = undefined;
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      body = text;
    }
  }
  if (!response.ok) {
    const rawDetail = typeof body === "object" && body !== null && "detail" in body
      ? body.detail
      : undefined;
    const detail = typeof rawDetail === "string" ? rawDetail : undefined;
    const message = response.status === 401
      ? "Your session has expired. Please sign in again."
      : response.status === 403
        ? "You are not authorized for this action."
        : response.status === 404
          ? "The requested record was not found."
          : response.status === 422
            ? detail ?? "Please check the submitted values."
            : detail ?? "The backend could not complete the request.";
    if (response.status === 401 && token) {
      clearApiToken();
      window.dispatchEvent(new Event("buildsync-auth-expired"));
    }
    throw new ApiError(response.status, message, detail);
  }
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  postForm: <T>(path: string, body: FormData) =>
    request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export interface ApiUser {
  id: number;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  role: string;
  is_active?: boolean;
}

export interface ApiProject {
  id: number;
  project_code: string;
  name: string;
  package_name?: string | null;
  location?: string | null;
  status: string;
  start_date: string;
  planned_end_date: string;
}

export interface AnalyticsOverview {
  project: { id: number; name: string; status: string };
  progress?: { overall_progress?: number; planned_progress?: number; variance?: number };
  activities?: { total?: number; completed?: number; in_progress?: number; delayed?: number };
  evidence?: Record<string, number>;
  workforce?: Record<string, number>;
  safety?: Record<string, number>;
  quality?: Record<string, number>;
  materials?: Record<string, number>;
  equipment?: Record<string, number>;
  disruptions?: Record<string, number>;
}

export interface AssistantResult {
  answer: string;
  intent?: string;
  confidence?: number;
  sources?: Array<{ id: string | number; type?: string; title?: string; summary?: string }>;
}

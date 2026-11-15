import type {
  AdminStats,
  AdminUser,
  Comment,
  MediaUpload,
  Me,
  Page,
  Post,
  PublicProfile,
  ReactionSummary,
  ReactionType,
  UserSummary,
} from "./types";

const API = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: { field: string; message: string }[],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "VALIDATION_ERROR" && error.details?.length) {
      return error.details.map((d) => `${d.field}: ${d.message}`).join(". ");
    }
    if (error.code === "RATE_LIMITED") return "Too many attempts. Please wait a moment and try again.";
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// One refresh at a time, shared by every request that hits a 401 at the same moment.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API}/auth/refresh`, { method: "POST", credentials: "include" })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  form?: FormData;
  /** Do not try to refresh the session on 401 (used by login/refresh themselves). */
  skipRefresh?: boolean;
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const data = await response.json();
    const error = data?.error;
    if (error) return new ApiError(response.status, error.code, error.message, error.details);
  } catch {
    /* body was not JSON */
  }
  return new ApiError(response.status, "HTTP_ERROR", response.statusText || "Request failed");
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const send = () =>
    fetch(`${API}${path}`, {
      method: options.method ?? "GET",
      credentials: "include",
      headers: options.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: options.form ?? (options.body !== undefined ? JSON.stringify(options.body) : undefined),
    });

  let response = await send();
  if (response.status === 401 && !options.skipRefresh) {
    const refreshed = await refreshSession();
    // If refresh failed, another browser tab may have just rotated the cookie: retry once anyway.
    if (!refreshed) await sleep(250);
    response = await send();
  }
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const authApi = {
  register: (data: { email: string; username: string; password: string }) =>
    request<Me>("/auth/register", { method: "POST", body: data, skipRefresh: true }),
  login: (data: { email: string; password: string }) =>
    request<Me>("/auth/login", { method: "POST", body: data, skipRefresh: true }),
  logout: () => request<void>("/auth/logout", { method: "POST", skipRefresh: true }),
  logoutAll: () => request<void>("/auth/logout-all", { method: "POST" }),
  me: () => request<Me>("/users/me"),
  verifyEmail: (token: string) =>
    request<{ message: string }>("/auth/verify-email", { method: "POST", body: { token }, skipRefresh: true }),
  resendVerification: (email: string) =>
    request<{ message: string }>("/auth/resend-verification", { method: "POST", body: { email }, skipRefresh: true }),
  forgotPassword: (email: string) =>
    request<{ message: string }>("/auth/forgot-password", { method: "POST", body: { email }, skipRefresh: true }),
  resetPassword: (token: string, new_password: string) =>
    request<{ message: string }>("/auth/reset-password", { method: "POST", body: { token, new_password }, skipRefresh: true }),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("/auth/change-password", { method: "POST", body: { current_password, new_password } }),
  deactivate: (password: string | null) =>
    request<void>("/auth/deactivate", { method: "POST", body: { password } }),
  deleteAccount: (password: string | null, confirm_username: string) =>
    request<void>("/auth/account", { method: "DELETE", body: { password, confirm_username } }),
  googleLoginUrl: `${API}/auth/google/login`,
};

export const usersApi = {
  profile: (username: string) => request<PublicProfile>(`/users/${encodeURIComponent(username)}`),
  update: (data: { display_name?: string; bio?: string }) =>
    request<Me>("/users/me", { method: "PATCH", body: data }),
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Me>("/users/me/avatar", { method: "POST", form });
  },
  search: (q: string) => request<UserSummary[]>(`/users/search${query({ q })}`),
  follow: (username: string) => request<void>(`/users/${encodeURIComponent(username)}/follow`, { method: "POST" }),
  unfollow: (username: string) => request<void>(`/users/${encodeURIComponent(username)}/follow`, { method: "DELETE" }),
  followers: (username: string, cursor: string | null) =>
    request<Page<UserSummary>>(`/users/${encodeURIComponent(username)}/followers${query({ cursor })}`),
  following: (username: string, cursor: string | null) =>
    request<Page<UserSummary>>(`/users/${encodeURIComponent(username)}/following${query({ cursor })}`),
};

export const postsApi = {
  create: (data: { content?: string | null; media_id?: string | null }) =>
    request<Post>("/posts", { method: "POST", body: data }),
  get: (id: string) => request<Post>(`/posts/${id}`),
  update: (id: string, content: string) => request<Post>(`/posts/${id}`, { method: "PATCH", body: { content } }),
  remove: (id: string) => request<void>(`/posts/${id}`, { method: "DELETE" }),
  feed: (cursor: string | null) => request<Page<Post>>(`/posts/feed${query({ cursor })}`),
  explore: (cursor: string | null) => request<Page<Post>>(`/posts/explore${query({ cursor })}`),
  byUser: (username: string, cursor: string | null) =>
    request<Page<Post>>(`/users/${encodeURIComponent(username)}/posts${query({ cursor })}`),
  react: (id: string, type: ReactionType) =>
    request<ReactionSummary>(`/posts/${id}/reaction`, { method: "PUT", body: { type } }),
  unreact: (id: string) => request<ReactionSummary>(`/posts/${id}/reaction`, { method: "DELETE" }),
};

export const commentsApi = {
  list: (postId: string, cursor: string | null) =>
    request<Page<Comment>>(`/posts/${postId}/comments${query({ cursor, order: "asc" })}`),
  create: (postId: string, content: string) =>
    request<Comment>(`/posts/${postId}/comments`, { method: "POST", body: { content } }),
  remove: (id: string) => request<void>(`/comments/${id}`, { method: "DELETE" }),
};

export const mediaApi = {
  uploadImage: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<MediaUpload>("/media/images", { method: "POST", form });
  },
};

export const adminApi = {
  stats: () => request<AdminStats>("/admin/stats"),
  users: (cursor: string | null) => request<Page<AdminUser>>(`/admin/users${query({ cursor })}`),
  updateUser: (id: string, data: { is_active?: boolean; role?: "user" | "admin" }) =>
    request<AdminUser>(`/admin/users/${id}`, { method: "PATCH", body: data }),
};

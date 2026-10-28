/**
 * Thin fetch wrapper for the FastAPI service. The caller passes a Supabase
 * JWT in `authToken`; in dev the API accepts an unverified decode (sub claim
 * only). TODO M7: full signature verification server-side.
 */

import type { Project, ProjectType } from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message);
  }
}

async function request<T>(
  method: string,
  path: string,
  authToken: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE}/v1${path}`, {
    method,
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${authToken}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    let code = "http_error";
    let message = res.statusText;
    try {
      const data = await res.json();
      code = data?.error?.code ?? code;
      message = data?.error?.message ?? message;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(code, message, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  projects: {
    list: (token: string) => request<Project[]>("GET", "/projects", token),
    get: (token: string, id: string) =>
      request<Project>("GET", `/projects/${id}`, token),
    create: (
      token: string,
      body: { name: string; project_type: ProjectType; style_preset?: Record<string, string> },
    ) => request<Project>("POST", "/projects", token, body),
    delete: (token: string, id: string) =>
      request<void>("DELETE", `/projects/${id}`, token),
  },
};

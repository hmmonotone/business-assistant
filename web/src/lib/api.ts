// web/src/lib/api.ts
export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://localhost:8000";

/** JSON helper (adds Bearer automatically) */
export async function api(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    ...(opts.headers || {}),
    ...(path.startsWith("/api") ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (!res.ok) throw new Error(await res.text());
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

/** Binary download with auth (for protected /download) */
export async function apiDownload(path: string): Promise<Blob> {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.blob();
}

/** Multipart upload with auth (do NOT set Content-Type) */
export async function upload(path: string, formData: FormData) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  // most of our upload endpoints return JSON
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

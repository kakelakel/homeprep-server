import type { ImageUploadResult } from "./types";

type ApiErrorBody = { error?: { code?: string; message?: string }; detail?: string };

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(body.error?.message ?? body.detail ?? `${response.status} ${response.statusText}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function uploadImage(file: File): Promise<ImageUploadResult> {
  const dataBase64 = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Unable to read image"));
    reader.onload = () => {
      const value = String(reader.result ?? "");
      resolve(value.includes(",") ? value.split(",", 2)[1] : value);
    };
    reader.readAsDataURL(file);
  });
  return request<ImageUploadResult>("/api/v1/media/images", {
    method: "POST",
    body: JSON.stringify({ filename: file.name, content_type: file.type, data_base64: dataBase64 }),
  });
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function dateOnly(value?: string | null): string {
  return value ? value.slice(0, 10) : "";
}

export function pretty(value?: string | null): string {
  if (!value) return "—";
  return value.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

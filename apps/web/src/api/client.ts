import type { DocumentDetail, DocumentSummary } from "../types";

const API_BASE = "http://localhost:8000";

let token: string | null = localStorage.getItem("speechify_token");

export function setToken(newToken: string | null): void {
  token = newToken;
  if (newToken) {
    localStorage.setItem("speechify_token", newToken);
  } else {
    localStorage.removeItem("speechify_token");
  }
}

export function getToken(): string | null {
  return token;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<void> {
  const data = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.access_token);
}

export function listDocuments(): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>("/documents");
}

export function createDocument(title: string, text: string): Promise<DocumentDetail> {
  return request<DocumentDetail>("/documents", {
    method: "POST",
    body: JSON.stringify({ title, text }),
  });
}

export function getDocument(documentId: number): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${documentId}`);
}

export function convertDocument(documentId: number): Promise<unknown> {
  return request(`/documents/${documentId}/convert`, { method: "POST" });
}

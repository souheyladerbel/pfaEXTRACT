import type {
  DashboardPayload,
  ExtractionBatchPayload,
  HistoryDetail,
  HistoryListPayload,
  MetaPayload,
  ModelsPayload
} from "@/lib/types";

const defaultApiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function getApiBaseUrl() {
  return defaultApiBase.replace(/\/$/, "");
}

export function resolveApiUrl(path: string) {
  return `${getApiBaseUrl()}${path}`;
}

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(resolveApiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchMeta() {
  return readJson<MetaPayload>("/api/meta");
}

export function fetchDashboard() {
  return readJson<DashboardPayload>("/api/dashboard");
}

export function fetchAnalyses() {
  return readJson<DashboardPayload>("/api/analyses");
}

export function fetchHistory(params: URLSearchParams) {
  return readJson<HistoryListPayload>(`/api/history?${params.toString()}`);
}

export function fetchHistoryDetail(entryKey: string) {
  return readJson<HistoryDetail>(`/api/history/${entryKey}`);
}

export function deleteHistoryEntry(entryKey: string) {
  return readJson<{ status: string; message: string }>(`/api/history/${entryKey}`, {
    method: "DELETE"
  });
}

export function fetchLatestResult() {
  return readJson<{ item: HistoryDetail | null }>("/api/results/latest");
}

export function fetchModels() {
  return readJson<ModelsPayload>("/api/models");
}

export async function uploadExtractions(
  formData: FormData
): Promise<ExtractionBatchPayload> {
  const response = await fetch(resolveApiUrl("/api/extractions"), {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return (await response.json()) as ExtractionBatchPayload;
}

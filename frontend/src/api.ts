const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Analysis {
  sentiment: "positive" | "neutral" | "negative";
  confidence: number;
  summary: string;
  themes: string[];
  severity: number;
  suggested_category: string;
}

export interface DraftResponse {
  resolution: string;
  sources: string[];
}

export interface AnalyzeResult {
  thread_id: string;
  status: string;
  draft_response: DraftResponse | null;
  analysis?: Analysis;
}

async function request<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ""}`);
  }
  return res.json();
}

export function analyzeReview(review: string): Promise<AnalyzeResult> {
  return request<AnalyzeResult>("/analyze", { review });
}

export function approveThread(thread_id: string, approved: boolean): Promise<AnalyzeResult> {
  return request<AnalyzeResult>("/approve", { thread_id, approved });
}

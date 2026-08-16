export type UploadedDocument = { document_id: string; source_type: string; segment_count: number };

export function apiBaseUrlFor(environment: string | undefined, configuredUrl: string | undefined): string {
  if (configuredUrl) return configuredUrl.replace(/\/$/, "");
  if (environment === "production") return "";
  return "http://127.0.0.1:8000";
}

const apiBaseUrl = apiBaseUrlFor(process.env.NODE_ENV, process.env.NEXT_PUBLIC_API_BASE_URL);

async function request<T>(path: string, init: RequestInit): Promise<T> {
  if (!apiBaseUrl) throw new Error("NEXT_PUBLIC_API_BASE_URL must be set for production deployments.");
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? "The request could not be completed. Please try again.");
  }
  return response.json() as Promise<T>;
}

export function uploadDocument(file: File): Promise<UploadedDocument> { const body = new FormData(); body.append("file", file); return request<UploadedDocument>("/documents", { method: "POST", body }); }
export function analyzeDocument(documentId: string): Promise<unknown> { return request(`/documents/${documentId}/analyze`, { method: "POST" }); }
export type Diagnosis = { document_signal_score: number; signal_ratio: number; redundancy_ratio: number; evidence_coverage: number; decision_completeness: number; gaps: string[] };
export type SemanticMap = { slots: Array<{ id: string; slot: string; text: string }> };
export function getDiagnosis(documentId: string): Promise<Diagnosis> { return request(`/documents/${documentId}/diagnosis`, { method: "GET" }); }
export function getSemanticMap(documentId: string): Promise<SemanticMap> { return request(`/documents/${documentId}/semantic-map`, { method: "GET" }); }
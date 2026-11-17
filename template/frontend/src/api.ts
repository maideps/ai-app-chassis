// Typed client for the backend (template/backend/src/app/main.py). The UI calls /api/*; the
// Vite dev server, or a reverse proxy in production, strips the prefix.

export interface Summary {
  summary: string;
  keywords: string[];
}

export interface Health {
  status: string;
  model: string;
}

export interface UsageStats {
  calls: number;
  failed: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms_p50: number;
  latency_ms_p95: number;
}

export interface Usage {
  total: UsageStats;
  by_step: Record<string, UsageStats>;
}

// A failed request, with the guardrail rule when the backend rejected the input (422).
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly rule: string | null = null,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (response.ok) return (await response.json()) as T;
  let detail: unknown = null;
  try {
    detail = ((await response.json()) as { detail?: unknown }).detail;
  } catch {
    // A body that is not JSON (a proxy error page, for example) keeps the generic message.
  }
  if (detail && typeof detail === "object" && "rule" in detail) {
    const { rule, message } = detail as { rule: string; message: string };
    throw new ApiError(response.status, message, rule);
  }
  const message = typeof detail === "string" ? detail : `request failed (HTTP ${response.status})`;
  throw new ApiError(response.status, message);
}

export const api = {
  health: () => request<Health>("/health"),
  usage: () => request<Usage>("/usage"),
  summarize: (text: string) =>
    request<Summary>("/summarize", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text }),
    }),
};

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://metricmind-backend-6qdz.onrender.com";

export const API_CHAT_URL =
  process.env.METRICMIND_API_URL ||
  process.env.NEXT_PUBLIC_METRICMIND_API_URL ||
  `${API_BASE_URL}/api/chat`;

export const API_URL = API_CHAT_URL;

export async function fetchHealth(): Promise<{ status: string; app: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchDatasetOverview() {
  const res = await fetch(`${API_BASE_URL}/api/dataset`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch dataset (${res.status})`);
  return await res.json();
}

export async function fetchSemanticMetrics() {
  const res = await fetch(`${API_BASE_URL}/api/metrics`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch metrics (${res.status})`);
  return await res.json();
}

export async function fetchIntegrations() {
  const res = await fetch(`${API_BASE_URL}/api/integrations`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch integrations (${res.status})`);
  return await res.json();
}

export async function fetchAnalyticsQuery(filters: Record<string, unknown>) {
  const res = await fetch(`${API_BASE_URL}/api/analytics/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Analytics query failed (${res.status})`);
  return await res.json();
}
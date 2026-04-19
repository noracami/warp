export interface Status {
  running: boolean;
  mockReady?: boolean;
  lat: number | null;
  lng: number | null;
  lastTeleportAt: number | null;
}

function normalizeBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

export async function teleport(
  baseUrl: string,
  lat: number,
  lng: number,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/teleport`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lat, lng }),
    signal,
  });
  if (!res.ok) {
    throw new Error(`teleport failed: HTTP ${res.status}`);
  }
}

export async function stopMock(baseUrl: string, signal?: AbortSignal): Promise<void> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/stop`, {
    method: "POST",
    signal,
  });
  if (!res.ok) {
    throw new Error(`stop failed: HTTP ${res.status}`);
  }
}

export async function getStatus(baseUrl: string, signal?: AbortSignal): Promise<Status> {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/status`, { signal });
  if (!res.ok) {
    throw new Error(`status failed: HTTP ${res.status}`);
  }
  return res.json();
}

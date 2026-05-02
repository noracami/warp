const KEY_BASE_URL = "warp.phoneBaseUrl";
const KEY_MAP_VIEW = "warp.mapView";
const KEY_RECENT_URLS = "warp.recentUrls";
const MAX_RECENT_URLS = 4; // 顯示時排除 current，所以實際顯示最多 3 個

export function loadBaseUrl(): string {
  return localStorage.getItem(KEY_BASE_URL) ?? "";
}

export function saveBaseUrl(url: string): void {
  localStorage.setItem(KEY_BASE_URL, url.trim());
}

export function loadRecentUrls(): string[] {
  const raw = localStorage.getItem(KEY_RECENT_URLS);
  if (!raw) return [];
  try {
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function saveRecentUrls(urls: string[]): void {
  localStorage.setItem(KEY_RECENT_URLS, JSON.stringify(urls));
}

export function pushRecentUrl(list: string[], url: string): string[] {
  const u = url.trim();
  if (!u) return list;
  return [u, ...list.filter((x) => x !== u)].slice(0, MAX_RECENT_URLS);
}

export interface MapView {
  lat: number;
  lng: number;
  zoom: number;
}

export function loadMapView(): MapView | null {
  const raw = localStorage.getItem(KEY_MAP_VIEW);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MapView;
  } catch {
    return null;
  }
}

export function saveMapView(view: MapView): void {
  localStorage.setItem(KEY_MAP_VIEW, JSON.stringify(view));
}

const KEY_BASE_URL = "warp.phoneBaseUrl";
const KEY_MAP_VIEW = "warp.mapView";

export function loadBaseUrl(): string {
  return localStorage.getItem(KEY_BASE_URL) ?? "";
}

export function saveBaseUrl(url: string): void {
  localStorage.setItem(KEY_BASE_URL, url.trim());
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

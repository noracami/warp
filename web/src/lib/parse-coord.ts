import type { LatLng } from "./geo";

const COORD_RE =
  /^\s*(?:lat[:=]?\s*)?(-?\d+(?:\.\d+)?)\s*[,\s/]\s*(?:lng[:=]?\s*|lon[:=]?\s*)?(-?\d+(?:\.\d+)?)\s*$/i;
const AT_RE = /@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/;
const PARAM_RE =
  /[?&](?:q|ll|query|center|daddr|saddr|destination|sll)=(-?\d+(?:\.\d+)?)(?:%2C|,)(-?\d+(?:\.\d+)?)/i;
const SHORT_HOSTS = ["maps.app.goo.gl", "goo.gl", "g.page"] as const;

export interface ParseResult {
  ok: boolean;
  coord: LatLng | null;
  reason?: "empty" | "out-of-range" | "short-url-unsupported" | "unrecognized";
}

export function parseCoord(raw: string): ParseResult {
  const s = (raw ?? "").trim();
  if (!s) return { ok: false, coord: null, reason: "empty" };

  const m = s.match(COORD_RE);
  if (m) return finalize(m[1], m[2]);

  const fromUrl = parseUrl(s);
  if (fromUrl) return finalize(String(fromUrl[0]), String(fromUrl[1]));

  if (SHORT_HOSTS.some((h) => s.includes(h))) {
    return { ok: false, coord: null, reason: "short-url-unsupported" };
  }
  return { ok: false, coord: null, reason: "unrecognized" };
}

function parseUrl(url: string): LatLng | null {
  const decoded = safeDecode(url);
  let m = decoded.match(AT_RE);
  if (m) return [parseFloat(m[1]), parseFloat(m[2])];
  m = decoded.match(PARAM_RE);
  if (m) return [parseFloat(m[1]), parseFloat(m[2])];
  return null;
}

function safeDecode(s: string): string {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}

function finalize(latStr: string, lngStr: string): ParseResult {
  const lat = parseFloat(latStr);
  const lng = parseFloat(lngStr);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { ok: false, coord: null, reason: "unrecognized" };
  }
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    return { ok: false, coord: null, reason: "out-of-range" };
  }
  return { ok: true, coord: [lat, lng] };
}

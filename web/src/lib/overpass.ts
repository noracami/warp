type Position = [number, number];
interface LineString {
  type: "LineString";
  coordinates: Position[];
}
interface Polygon {
  type: "Polygon";
  coordinates: Position[][];
}
interface Feature {
  type: "Feature";
  properties: Record<string, string>;
  geometry: LineString | Polygon;
}
export interface FeatureCollection {
  type: "FeatureCollection";
  features: Feature[];
}

export type Bbox = [south: number, west: number, north: number, east: number];

const ENDPOINT = "https://overpass-api.de/api/interpreter";
const cache = new Map<string, Promise<FeatureCollection>>();
const CACHE_LIMIT = 12;

interface OverpassWay {
  type: "way";
  id: number;
  geometry?: { lat: number; lon: number }[];
  tags?: Record<string, string>;
}

interface OverpassResponse {
  elements: OverpassWay[];
}

function bboxKey(bbox: Bbox): string {
  return bbox.map((n) => n.toFixed(3)).join(",");
}

function buildQuery(bbox: Bbox): string {
  const [s, w, n, e] = bbox;
  const b = `${s},${w},${n},${e}`;
  return `[out:json][timeout:25];
(
  way["waterway"="river"](${b});
  way["waterway"="stream"](${b});
  way["waterway"="canal"](${b});
  way["natural"="water"](${b});
);
out geom;`;
}

function toFeatureCollection(data: OverpassResponse): FeatureCollection {
  const features: Feature[] = [];
  for (const el of data.elements) {
    if (el.type !== "way" || !el.geometry || el.geometry.length < 2) continue;
    const coords = el.geometry.map((p) => [p.lon, p.lat] as [number, number]);
    const first = coords[0];
    const last = coords[coords.length - 1];
    const closed =
      coords.length >= 4 && first[0] === last[0] && first[1] === last[1];
    const isWaterArea = el.tags?.natural === "water";
    if (isWaterArea && closed) {
      features.push({
        type: "Feature",
        properties: el.tags ?? {},
        geometry: { type: "Polygon", coordinates: [coords] },
      });
    } else {
      features.push({
        type: "Feature",
        properties: el.tags ?? {},
        geometry: { type: "LineString", coordinates: coords },
      });
    }
  }
  return { type: "FeatureCollection", features };
}

export function fetchWaterFeatures(bbox: Bbox): Promise<FeatureCollection> {
  const key = bboxKey(bbox);
  const hit = cache.get(key);
  if (hit) return hit;

  const promise = (async () => {
    const body = "data=" + encodeURIComponent(buildQuery(bbox));
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) throw new Error(`Overpass HTTP ${res.status}`);
    const data = (await res.json()) as OverpassResponse;
    return toFeatureCollection(data);
  })();

  cache.set(key, promise);
  if (cache.size > CACHE_LIMIT) {
    const oldestKey = cache.keys().next().value;
    if (oldestKey !== undefined) cache.delete(oldestKey);
  }
  promise.catch(() => cache.delete(key));
  return promise;
}

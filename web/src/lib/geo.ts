export type LatLng = [number, number];

const METERS_PER_DEG_LAT = 111320;

function lngMetersPerDeg(latDeg: number): number {
  return METERS_PER_DEG_LAT * Math.cos((latDeg * Math.PI) / 180);
}

export function distanceMeters(a: LatLng, b: LatLng): number {
  const dLatM = (b[0] - a[0]) * METERS_PER_DEG_LAT;
  const dLngM = (b[1] - a[1]) * lngMetersPerDeg((a[0] + b[0]) / 2);
  return Math.hypot(dLatM, dLngM);
}

export function randomInCircle(center: LatLng, radiusMeters: number): LatLng {
  const r = radiusMeters * Math.sqrt(Math.random());
  const theta = 2 * Math.PI * Math.random();
  const dxM = r * Math.cos(theta);
  const dyM = r * Math.sin(theta);
  const lngPerDeg = lngMetersPerDeg(center[0]);
  return [center[0] + dyM / METERS_PER_DEG_LAT, center[1] + dxM / lngPerDeg];
}

export function moveTowards(from: LatLng, to: LatLng, stepMeters: number): LatLng {
  const d = distanceMeters(from, to);
  if (d <= stepMeters) return to;
  const ratio = stepMeters / d;
  return [from[0] + (to[0] - from[0]) * ratio, from[1] + (to[1] - from[1]) * ratio];
}

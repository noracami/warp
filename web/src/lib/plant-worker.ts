import { distanceMeters, moveTowards, randomInCircle, type LatLng } from "./geo";
import { teleport } from "./api";

interface StartMsg {
  type: "start";
  baseUrl: string;
  center: LatLng;
  radius: number;
  speedMps: number;
  tickMs: number;
  initial: LatLng | null;
}

interface UpdateMsg {
  type: "update";
  speedMps?: number;
  center?: LatLng;
}

interface StopMsg {
  type: "stop";
}

type In = StartMsg | UpdateMsg | StopMsg;

export interface TickOut {
  type: "tick";
  pos: LatLng;
  stepDist: number;
  ok: boolean;
  error?: string;
  at: number;
}

export interface ReadyOut {
  type: "ready";
}

export interface FatalOut {
  type: "fatal";
  error: string;
}

export type Out = TickOut | ReadyOut | FatalOut;

let timer: ReturnType<typeof setInterval> | null = null;
let baseUrl = "";
let center: LatLng | null = null;
let radius = 0;
let speedMps = 0;
let tickMs = 1000;
let current: LatLng | null = null;
let target: LatLng | null = null;

self.onmessage = (e: MessageEvent<In>) => {
  try {
    const msg = e.data;
    if (msg.type === "start") {
      if (timer != null) clearInterval(timer);
      baseUrl = msg.baseUrl;
      center = msg.center;
      radius = msg.radius;
      speedMps = msg.speedMps;
      tickMs = msg.tickMs;
      current = msg.initial ?? msg.center;
      target = null;
      timer = setInterval(tick, tickMs);
      tick();
    } else if (msg.type === "update") {
      if (msg.speedMps != null) speedMps = msg.speedMps;
      if (msg.center != null) {
        center = msg.center;
        target = null;
      }
    } else if (msg.type === "stop") {
      if (timer != null) clearInterval(timer);
      timer = null;
      current = null;
      target = null;
    }
  } catch (err) {
    postFatal(err);
  }
};

post({ type: "ready" });

async function tick() {
  if (!center || !current) return;
  const stepM = speedMps * (tickMs / 1000);
  if (!target || distanceMeters(current, target) <= stepM) {
    target = randomInCircle(center, radius);
  }
  const next = moveTowards(current, target, stepM);
  const stepDist = distanceMeters(current, next);
  current = next;
  try {
    await teleport(baseUrl, next[0], next[1]);
    post({ type: "tick", pos: next, stepDist, ok: true, at: Date.now() });
  } catch (err) {
    post({
      type: "tick",
      pos: next,
      stepDist,
      ok: false,
      error: err instanceof Error ? err.message : String(err),
      at: Date.now(),
    });
  }
}

function post(msg: Out) {
  (self as unknown as Worker).postMessage(msg);
}

function postFatal(err: unknown) {
  post({ type: "fatal", error: err instanceof Error ? `${err.name}: ${err.message}` : String(err) });
}

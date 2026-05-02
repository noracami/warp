type Level = "log" | "info" | "warn" | "error" | "event";

function stringify(args: unknown[]): string {
  return args
    .map((a) => {
      if (a instanceof Error) {
        return `${a.name}: ${a.message}${a.stack ? "\n" + a.stack : ""}`;
      }
      if (typeof a === "object" && a !== null) {
        try {
          return JSON.stringify(a);
        } catch {
          return String(a);
        }
      }
      return String(a);
    })
    .join(" ");
}

function send(level: Level, args: unknown[]): void {
  try {
    fetch("/__log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level, message: stringify(args) }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    // logger must never throw
  }
}

export function installDevLog(): void {
  const orig = {
    log: console.log.bind(console),
    info: console.info.bind(console),
    warn: console.warn.bind(console),
    error: console.error.bind(console),
  } as const;

  (["log", "info", "warn", "error"] as const).forEach((lvl) => {
    console[lvl] = (...args: unknown[]) => {
      orig[lvl](...args);
      send(lvl, args);
    };
  });

  window.addEventListener("error", (e) => {
    send("event", [
      "window.error",
      e.message,
      `${e.filename}:${e.lineno}:${e.colno}`,
      e.error,
    ]);
  });

  window.addEventListener("unhandledrejection", (e) => {
    send("event", ["unhandledrejection", e.reason]);
  });

  send("event", ["dev-log installed", navigator.userAgent]);
}

export function attachWorkerLogging(worker: Worker, label: string): void {
  worker.addEventListener("error", (e) => {
    send("event", [
      `worker[${label}].error`,
      e.message,
      `${e.filename}:${e.lineno}:${e.colno}`,
    ]);
  });
  worker.addEventListener("messageerror", () => {
    send("event", [`worker[${label}].messageerror`]);
  });
}

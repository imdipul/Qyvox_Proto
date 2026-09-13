"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ServiceState = "operational" | "unavailable";
type StatusPayload = {
  status: "operational" | "degraded";
  api: ServiceState;
  verifier: ServiceState;
  database: ServiceState;
};

export function SystemStatus() {
  const [status, setStatus] = useState<StatusPayload | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function check() {
      try {
        const response = await fetch(`${API_URL}/status`, { signal: controller.signal, cache: "no-store" });
        if (!response.ok) throw new Error("Status unavailable");
        setStatus((await response.json()) as StatusPayload);
      } catch {
        if (!controller.signal.aborted) {
          setStatus({ status: "degraded", api: "unavailable", verifier: "unavailable", database: "unavailable" });
        }
      }
    }
    void check();
    const timer = window.setInterval(check, 30_000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, []);

  const healthy = status?.status === "operational";
  return (
    <div className={`system-status ${healthy ? "status-healthy" : "status-degraded"}`} title={status ? `API: ${status.api}; verifier: ${status.verifier}; database: ${status.database}` : "Checking system status"}>
      <span aria-hidden="true" />
      {status === null ? "Checking systems" : healthy ? "All systems operational" : "Configuration attention"}
    </div>
  );
}

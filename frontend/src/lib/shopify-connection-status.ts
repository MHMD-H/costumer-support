import { API_BASE_URL } from "./api";
import { getAccessToken } from "./auth";

export type ConnectionStatus = "pending" | "connected" | "signed-out" | "forbidden" | "unavailable";

export async function readShopifyConnectionStatus(signal?: AbortSignal): Promise<ConnectionStatus> {
  try {
    const token = await getAccessToken();
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    if (!token) return "signed-out";

    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal,
    });
    if (response.status === 401) return "signed-out";
    if (response.status === 403) return "forbidden";
    if (!response.ok) return "unavailable";

    const user: unknown = await response.json();
    if (!user || typeof user !== "object" || !("role" in user) || !("tenant_id" in user)) {
      return "unavailable";
    }
    if (user.role !== "store_owner") return "forbidden";
    if (user.tenant_id === null) return "pending";
    return typeof user.tenant_id === "string" && user.tenant_id.length > 0 ? "connected" : "unavailable";
  } catch (error) {
    if (signal?.aborted) throw error;
    return "unavailable";
  }
}

const MAX_ATTEMPTS = 7;
const POLL_INTERVAL_MS = 4000;

function waitForNextAttempt(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, POLL_INTERVAL_MS);
    function abort() {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    }
    signal.addEventListener("abort", abort, { once: true });
  });
}

export async function pollShopifyConnection(
  signal: AbortSignal,
  onStatus: (status: ConnectionStatus | "timeout") => void,
  readStatus: (signal: AbortSignal) => Promise<ConnectionStatus> = readShopifyConnectionStatus,
): Promise<void> {
  try {
    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
      if (signal.aborted) return;
      const status = await readStatus(signal);
      if (signal.aborted) return;
      if (status !== "pending") {
        onStatus(status);
        return;
      }
      onStatus("pending");
      if (attempt < MAX_ATTEMPTS - 1) await waitForNextAttempt(signal);
    }
    if (!signal.aborted) onStatus("timeout");
  } catch {
    if (!signal.aborted) onStatus("unavailable");
  }
}

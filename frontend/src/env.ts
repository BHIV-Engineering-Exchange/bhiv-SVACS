const truthy = (v: string | undefined) => v === "true" || v === "1";
const rawApiUrl = import.meta.env.VITE_API_URL ?? "";
const apiUrl = rawApiUrl.replace(/\/+$/, "");

const rawUseMock = import.meta.env.VITE_USE_MOCK;
const isExplicitMock = truthy(rawUseMock);
const isExplicitReal = rawUseMock === "false" || rawUseMock === "0";

// Default to mock only if no API URL is provided and not explicitly set to false
const useMock = isExplicitMock || (!apiUrl && !isExplicitReal);

export const env = {
  useMock,
  api: {
    signal: (import.meta.env.VITE_SIGNAL_API ?? apiUrl).replace(/\/+$/, ""),
    perception: (import.meta.env.VITE_PERCEPTION_API ?? apiUrl).replace(/\/+$/, ""),
    intelligence: (import.meta.env.VITE_INTELLIGENCE_API ?? apiUrl).replace(/\/+$/, ""),
    state: (import.meta.env.VITE_STATE_API ?? apiUrl).replace(/\/+$/, ""),
    bucket: (import.meta.env.VITE_BUCKET_API ?? apiUrl).replace(/\/+$/, ""),
    telemetryWs: import.meta.env.VITE_TELEMETRY_WS ?? "",
  },
  pollIntervalMs: Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 2000),
} as const;

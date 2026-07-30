const truthy = (v: string | undefined) => v === "true" || v === "1";
const apiUrl = import.meta.env.VITE_API_URL ?? "";

export const env = {
  useMock: truthy(import.meta.env.VITE_USE_MOCK as string | undefined) || !import.meta.env.VITE_USE_MOCK,
  api: {
    signal: import.meta.env.VITE_SIGNAL_API ?? apiUrl,
    perception: import.meta.env.VITE_PERCEPTION_API ?? apiUrl,
    intelligence: import.meta.env.VITE_INTELLIGENCE_API ?? apiUrl,
    state: import.meta.env.VITE_STATE_API ?? apiUrl,
    bucket: import.meta.env.VITE_BUCKET_API ?? apiUrl,
    telemetryWs: import.meta.env.VITE_TELEMETRY_WS ?? "",
  },
  pollIntervalMs: Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 2000),
} as const;

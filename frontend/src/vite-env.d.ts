/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USE_MOCK?: string;
  readonly VITE_SIGNAL_API?: string;
  readonly VITE_PERCEPTION_API?: string;
  readonly VITE_INTELLIGENCE_API?: string;
  readonly VITE_STATE_API?: string;
  readonly VITE_BUCKET_API?: string;
  readonly VITE_TELEMETRY_WS?: string;
  readonly VITE_POLL_INTERVAL_MS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

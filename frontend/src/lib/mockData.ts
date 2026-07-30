import type {
  SignalChunk,
  PerceptionEvent,
  IntelligenceEvent,
  StateEvent,
  Alert,
  VesselSummary,
  StageMetric,
  BucketStatus,
  SystemHealthFrame,
} from "@/domain/types";

let seed = 1337;
const rand = () => {
  seed = (seed * 9301 + 49297) % 233280;
  return seed / 233280;
};
const pick = <T>(arr: T[]) => arr[Math.floor(rand() * arr.length)] as T;
const range = (n: number) => Array.from({ length: n }, (_, i) => i);

const SOURCES = ["AIS", "RADAR", "ACOUSTIC", "OTHER"] as const;
const VESSEL_IDS = range(24).map((i) => `Vessel_${String(i + 1).padStart(2, "0")}`);
const STATES = ["NORMAL", "WATCH", "ALERT", "TRANSIT", "DOCKED"];
const VALIDATIONS = ["ALLOW", "FLAG", "DENY"] as const;
const KINDS = ["vessel_detection", "object_track", "noise_filter", "echo_match"];
const ALERT_KINDS = [
  "Spoofing Flag",
  "Anomaly Detected",
  "Identity Mismatch",
  "RF Interference",
  "Unusual Behaviour",
  "Validation Failure",
  "Trace Continuity Gap",
];
const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;

const isoMinusSec = (s: number) => new Date(Date.now() - s * 1000).toISOString();

const traceId = (i: number) => `trc_${(i + 1000000).toString(36)}_${(rand() * 1e6).toFixed(0)}`;

export const generateSignals = (n = 60): SignalChunk[] =>
  range(n).map((i) => ({
    trace_id: traceId(i),
    chunk_id: `sig_${i + 1}`,
    vessel_id: rand() > 0.05 ? pick(VESSEL_IDS) : null,
    source: pick(SOURCES as unknown as string[]) as SignalChunk["source"],
    ts_utc: isoMinusSec(i * 4 + Math.floor(rand() * 3)),
    frequency_band: `${(rand() * 100 + 50).toFixed(1)} kHz`,
  }));

export const generatePerception = (n = 60): PerceptionEvent[] =>
  range(n).map((i) => ({
    trace_id: traceId(i),
    parent_chunk_id: `sig_${i + 1}`,
    vessel_id: rand() > 0.04 ? pick(VESSEL_IDS) : null,
    confidence: 0.55 + rand() * 0.45,
    kind: pick(KINDS),
    ts_utc: isoMinusSec(i * 4 + 1),
  }));

export const generateIntelligence = (n = 60): IntelligenceEvent[] =>
  range(n).map((i) => {
    const r = rand();
    const validation = r > 0.89 ? "DENY" : r > 0.78 ? "FLAG" : "ALLOW";
    return {
      trace_id: traceId(i),
      vessel_id: pick(VESSEL_IDS),
      validation: validation as IntelligenceEvent["validation"],
      reasons:
        validation === "ALLOW"
          ? ["pattern_match_ok", "identity_verified"]
          : validation === "FLAG"
            ? ["confidence_below_threshold", "track_discontinuity"]
            : ["spoofing_signature", "deny_listed_id"],
      confidence: 0.5 + rand() * 0.5,
      ts_utc: isoMinusSec(i * 4 + 2),
    };
  });

export const generateStateEvents = (n = 60): StateEvent[] =>
  range(n).map((i) => ({
    trace_id: traceId(i),
    vessel_id: pick(VESSEL_IDS),
    from_state: pick(STATES),
    to_state: pick(STATES),
    validation: pick(VALIDATIONS as unknown as string[]) as StateEvent["validation"],
    confidence: 0.5 + rand() * 0.5,
    ts_utc: isoMinusSec(i * 4 + 3),
  }));

export const generateAlerts = (n = 14): Alert[] =>
  range(n)
    .map((i) => ({
      id: `alert_${i + 1}`,
      ts_utc: isoMinusSec(60 + i * 180 + Math.floor(rand() * 90)),
      vessel_id: pick(VESSEL_IDS),
      kind: pick(ALERT_KINDS),
      severity: pick(SEVERITIES as unknown as string[]) as Alert["severity"],
      message: "Detected operational anomaly in upstream pipeline",
      trace_id: traceId(i),
      acknowledged: rand() > 0.7,
    }))
    .sort((a, b) => (a.ts_utc < b.ts_utc ? 1 : -1));

export const generateVessels = (): VesselSummary[] =>
  VESSEL_IDS.map((id) => {
    const signal = 700 + Math.floor(rand() * 800);
    return {
      vessel_id: id,
      signal_count: signal,
      perception_count: signal - Math.floor(rand() * 80),
      intelligence_count: signal - Math.floor(rand() * 120),
      state_count: signal - Math.floor(rand() * 160),
      last_state: pick(STATES),
      last_seen_utc: isoMinusSec(Math.floor(rand() * 600)),
      status: pick(["NORMAL", "WATCH", "ALERT"] as const),
    };
  }).sort((a, b) => b.signal_count - a.signal_count);

export const generateStageMetrics = (): StageMetric[] => [
  {
    stage: "signal",
    events_per_sec: 18 + rand() * 6,
    total_events: 12842,
    p50_latency_ms: 12,
    p95_latency_ms: 36,
    error_rate: 0.002,
    status: "live",
  },
  {
    stage: "perception",
    events_per_sec: 17 + rand() * 5,
    total_events: 12618,
    p50_latency_ms: 28,
    p95_latency_ms: 78,
    error_rate: 0.004,
    status: "live",
  },
  {
    stage: "intelligence",
    events_per_sec: 16 + rand() * 5,
    total_events: 12356,
    p50_latency_ms: 41,
    p95_latency_ms: 110,
    error_rate: 0.011,
    status: "live",
  },
  {
    stage: "state",
    events_per_sec: 15 + rand() * 4,
    total_events: 12210,
    p50_latency_ms: 22,
    p95_latency_ms: 64,
    error_rate: 0.003,
    status: "live",
  },
  {
    stage: "bucket",
    events_per_sec: 14 + rand() * 4,
    total_events: 12210,
    p50_latency_ms: 18,
    p95_latency_ms: 52,
    error_rate: 0,
    status: "live",
  },
];

export const generateBucketStatus = (): BucketStatus => ({
  sync_percent: 1.0,
  stages_synced: ["signal", "perception", "intelligence", "state"],
  last_sync_utc: isoMinusSec(8),
  pending_writes: 0,
  failed_writes: 0,
});

export const generateHealthFrame = (): SystemHealthFrame => ({
  ingestion_rate: 18.4,
  processing_latency_ms: 41,
  error_count_60s: 3,
  uptime_seconds: 3600 * 4 + 1280,
  ws_connected: true,
  last_telemetry_utc: new Date().toISOString(),
});

export const generateEventsOverTime = (points = 24) =>
  range(points).map((i) => {
    const t = new Date(Date.now() - (points - i) * 60 * 60 * 1000);
    const base = 480 + Math.sin(i / 3) * 60 + rand() * 80;
    return {
      ts: t.toISOString(),
      label: t.toISOString().slice(11, 16),
      signal: Math.round(base + rand() * 20),
      perception: Math.round(base - 10 + rand() * 18),
      intelligence: Math.round(base - 30 + rand() * 16),
      state: Math.round(base - 50 + rand() * 14),
    };
  });

export const validationBreakdown = () => ({
  total: 12356,
  allow: 10982,
  flag: 1374,
  deny: 0,
});

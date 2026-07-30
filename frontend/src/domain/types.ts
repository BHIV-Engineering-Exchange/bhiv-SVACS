import { z } from "zod";

export const TraceId = z.string().min(4);

export const Severity = z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]);
export type Severity = z.infer<typeof Severity>;

export const Validation = z.enum(["ALLOW", "FLAG", "DENY"]);
export type Validation = z.infer<typeof Validation>;

export const StageId = z.enum(["signal", "perception", "intelligence", "state", "bucket"]);
export type StageId = z.infer<typeof StageId>;

export const SignalChunk = z.object({
  trace_id: TraceId,
  chunk_id: z.string(),
  vessel_id: z.string().nullable(),
  source: z.enum(["AIS", "RADAR", "ACOUSTIC", "OTHER"]),
  ts_utc: z.string(),
  frequency_band: z.string().optional(),
  payload: z.record(z.unknown()).optional(),
});
export type SignalChunk = z.infer<typeof SignalChunk>;

export const PerceptionEvent = z.object({
  trace_id: TraceId,
  parent_chunk_id: z.string(),
  vessel_id: z.string().nullable(),
  confidence: z.number().min(0).max(1),
  kind: z.string(),
  ts_utc: z.string(),
});
export type PerceptionEvent = z.infer<typeof PerceptionEvent>;

export const IntelligenceEvent = z.object({
  trace_id: TraceId,
  vessel_id: z.string().nullable(),
  validation: Validation,
  reasons: z.array(z.string()),
  confidence: z.number().min(0).max(1),
  ts_utc: z.string(),
});
export type IntelligenceEvent = z.infer<typeof IntelligenceEvent>;

export const StateEvent = z.object({
  trace_id: TraceId,
  vessel_id: z.string().nullable(),
  from_state: z.string(),
  to_state: z.string(),
  validation: Validation,
  confidence: z.number().min(0).max(1),
  ts_utc: z.string(),
});
export type StateEvent = z.infer<typeof StateEvent>;

export const Alert = z.object({
  id: z.string(),
  ts_utc: z.string(),
  vessel_id: z.string(),
  kind: z.string(),
  severity: Severity,
  message: z.string(),
  trace_id: TraceId.optional(),
  acknowledged: z.boolean().default(false),
});
export type Alert = z.infer<typeof Alert>;

export const VesselSummary = z.object({
  vessel_id: z.string(),
  signal_count: z.number(),
  perception_count: z.number(),
  intelligence_count: z.number(),
  state_count: z.number(),
  last_state: z.string(),
  last_seen_utc: z.string(),
  status: z.enum(["NORMAL", "WATCH", "ALERT"]),
});
export type VesselSummary = z.infer<typeof VesselSummary>;

export const StageMetric = z.object({
  stage: StageId,
  events_per_sec: z.number(),
  total_events: z.number(),
  p50_latency_ms: z.number(),
  p95_latency_ms: z.number(),
  error_rate: z.number(),
  status: z.enum(["live", "degraded", "stale", "down"]),
});
export type StageMetric = z.infer<typeof StageMetric>;

export const BucketStatus = z.object({
  sync_percent: z.number(),
  stages_synced: z.array(StageId),
  last_sync_utc: z.string(),
  pending_writes: z.number(),
  failed_writes: z.number(),
});
export type BucketStatus = z.infer<typeof BucketStatus>;

export const SystemHealthFrame = z.object({
  ingestion_rate: z.number(),
  processing_latency_ms: z.number(),
  error_count_60s: z.number(),
  uptime_seconds: z.number(),
  ws_connected: z.boolean(),
  last_telemetry_utc: z.string(),
});
export type SystemHealthFrame = z.infer<typeof SystemHealthFrame>;

export interface TraceLifecycle {
  trace_id: string;
  signal?: SignalChunk;
  perception?: PerceptionEvent;
  intelligence?: IntelligenceEvent;
  state?: StateEvent;
  missing: StageId[];
}

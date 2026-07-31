import { clients } from "./client";

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
  TraceLifecycle,
} from "@/domain/types";

import {
  generateSignals,
  generatePerception,
  generateIntelligence,
  generateStateEvents,
  generateAlerts,
  generateVessels,
  generateHealthFrame,
} from "@/lib/mockData";

import { env } from "@/env";

/* =========================================================
   INTERFACE
========================================================= */

export interface SvacsAdapter {
  fetchSignals(): Promise<SignalChunk[]>;
  fetchPerception(): Promise<PerceptionEvent[]>;
  fetchIntelligence(): Promise<IntelligenceEvent[]>;
  fetchStateEvents(): Promise<StateEvent[]>;
  fetchAlerts(): Promise<Alert[]>;
  fetchVessels(): Promise<VesselSummary[]>;
  fetchStageMetrics(): Promise<StageMetric[]>;
  fetchBucketStatus(): Promise<BucketStatus>;
  fetchHealth(): Promise<SystemHealthFrame>;
  fetchEventsOverTime(): Promise<any[]>;
  fetchValidationBreakdown(): Promise<any>;
  fetchTrace(traceId: string): Promise<TraceLifecycle>;
}

const wait = (ms: number) =>
  new Promise((r) => setTimeout(r, ms));

/* =========================================================
   MOCK ADAPTER
========================================================= */

class MockAdapter implements SvacsAdapter {
  async fetchSignals(): Promise<any[]> {
    await wait(50);
    return generateSignals();
  }

  async fetchPerception(): Promise<any[]> {
    await wait(50);
    return generatePerception();
  }

  async fetchIntelligence(): Promise<any[]> {
    await wait(50);

    return generateIntelligence().map(
      (x: any, i: number) => ({
        ...x,

        ts_utc:
          x.ts_utc ||
          new Date(
            Date.now() - i * 60000
          ).toISOString(),

        validation:
          x.validation ||
          (i % 3 === 0
            ? "ALLOW"
            : i % 3 === 1
            ? "FLAG"
            : "DENY"),

        confidence:
          x.confidence || 0.72 + i * 0.03,

        reasons:
          x.reasons || [
            "Pattern Match",
            "Route Deviation",
          ],
      })
    );
  }

  async fetchStateEvents(): Promise<any[]> {
    await wait(50);

    const states = [
      "TRACKING",
      "MONITORING",
      "ESCORT",
      "INVESTIGATING",
      "TRANSIT",
    ];

    return generateStateEvents().map(
      (x: any, i: number) => ({
        ...x,

        ts_utc:
          x.ts_utc ||
          new Date(
            Date.now() - i * 60000
          ).toISOString(),

        vessel_id:
          x.vessel_id ||
          `Vessel_0${i + 1}`,

        to_state:
          x.to_state ||
          states[i % states.length],

        validation:
          x.validation ||
          (i % 4 === 0
            ? "DENY"
            : i % 2 === 0
            ? "ALLOW"
            : "FLAG"),

        confidence:
          x.confidence ||
          Number((0.72 + i * 0.05).toFixed(2)),
      })
    );
  }

  async fetchAlerts(): Promise<any[]> {
    await wait(50);

    return [
      {
        id: "alert-1",
        vessel_id: "Vessel_08",
        kind: "Anomaly Detected",
        severity: "LOW",
        ts_utc: new Date().toISOString(),
      },

      {
        id: "alert-2",
        vessel_id: "Vessel_13",
        kind: "Trace Continuity Gap",
        severity: "MEDIUM",
        ts_utc: new Date(
          Date.now() - 180000
        ).toISOString(),
      },

      {
        id: "alert-3",
        vessel_id: "Vessel_15",
        kind: "Unusual Behaviour",
        severity: "CRITICAL",
        ts_utc: new Date(
          Date.now() - 300000
        ).toISOString(),
      },
    ];
  }

  async fetchVessels(): Promise<any[]> {
    await wait(50);

    return [
      {
        trace_id: "TRC-001",
        vessel_id: "368084090",
        lat: 18.92,
        lon: 72.83,
        speed: 12,
        vessel_class: "Cargo",
        signal_count: 12,
        perception_count: 10,
        intelligence_count: 9,
        state_count: 8,
      },

      {
        trace_id: "TRC-002",
        vessel_id: "368084147",
        lat: 18.95,
        lon: 72.84,
        speed: 15,
        vessel_class: "Fishing",
        signal_count: 15,
        perception_count: 13,
        intelligence_count: 11,
        state_count: 10,
      },

      {
        trace_id: "TRC-003",
        vessel_id: "368084204",
        lat: 18.97,
        lon: 72.87,
        speed: 18,
        vessel_class: "Cargo",
        signal_count: 18,
        perception_count: 16,
        intelligence_count: 13,
        state_count: 12,
      },

      {
        trace_id: "TRC-004",
        vessel_id: "368084261",
        lat: 18.99,
        lon: 72.89,
        speed: 21,
        vessel_class: "Patrol",
        signal_count: 21,
        perception_count: 19,
        intelligence_count: 15,
        state_count: 14,
      },

      {
        trace_id: "TRC-005",
        vessel_id: "368084318",
        lat: 19.01,
        lon: 72.91,
        speed: 24,
        vessel_class: "Tanker",
        signal_count: 24,
        perception_count: 22,
        intelligence_count: 17,
        state_count: 16,
      },
    ];
  }

  async fetchStageMetrics(): Promise<any[]> {
    await wait(50);

    return [
      {
        stage: "signal",
        total_events: 60,
        events_per_sec: 120,
        p50_latency_ms: 45,
        p95_latency_ms: 90,
        error_rate: 0.01,
        status: "live",
      },

      {
        stage: "perception",
        total_events: 58,
        events_per_sec: 110,
        p50_latency_ms: 40,
        p95_latency_ms: 85,
        error_rate: 0.02,
        status: "live",
      },

      {
        stage: "intelligence",
        total_events: 54,
        events_per_sec: 105,
        p50_latency_ms: 38,
        p95_latency_ms: 75,
        error_rate: 0.01,
        status: "live",
      },

      {
        stage: "state",
        total_events: 51,
        events_per_sec: 98,
        p50_latency_ms: 50,
        p95_latency_ms: 100,
        error_rate: 0.03,
        status: "live",
      },

      {
        stage: "bucket",
        total_events: 51,
        events_per_sec: 98,
        p50_latency_ms: 20,
        p95_latency_ms: 40,
        error_rate: 0,
        status: "live",
      },
    ];
  }

  async fetchBucketStatus(): Promise<any> {
    await wait(50);

    return {
      sync_percent: 1,

      stages_synced: [
        "signal",
        "perception",
        "intelligence",
        "state",
      ],

      last_sync_utc:
        new Date().toISOString(),
    };
  }

  async fetchHealth(): Promise<any> {
    await wait(50);

    return {
      status: "ONLINE",
      service: "SVACS",
      ws_connected: true,
      ingestion_rate: 118.4,
      processing_latency_ms: 52,
      uptime_seconds: 86400,
      error_count_60s: 2,
      last_telemetry_utc:
        new Date().toISOString(),
    };
  }

  async fetchEventsOverTime(): Promise<any[]> {
    await wait(50);

    return [
      {
        time: "10:00",
        signal: 100,
        perception: 90,
        intelligence: 80,
        state: 70,
      },

      {
        time: "10:05",
        signal: 120,
        perception: 110,
        intelligence: 100,
        state: 90,
      },

      {
        time: "10:10",
        signal: 140,
        perception: 120,
        intelligence: 110,
        state: 100,
      },

      {
        time: "10:15",
        signal: 160,
        perception: 140,
        intelligence: 120,
        state: 110,
      },

      {
        time: "10:20",
        signal: 180,
        perception: 150,
        intelligence: 130,
        state: 120,
      },
    ];
  }

  async fetchValidationBreakdown(): Promise<any> {
    await wait(50);

    return {
      total: 100,
      allow: 80,
      flag: 15,
      deny: 5,
    };
  }

  async fetchTrace(
    traceId: string
  ): Promise<any> {
    await wait(50);

    return {
      trace_id: traceId,

      signal: {
        trace_id: traceId,
      },

      perception: {
        trace_id: traceId,
      },

      intelligence: {
        trace_id: traceId,
      },

      state: {
        trace_id: traceId,
      },

      missing: [],
    };
  }
}

/* =========================================================
   REAL ADAPTER
========================================================= */

class RealAdapter implements SvacsAdapter {
  private get base() {
    return env.api.signal.replace(/\/+$/, "");
  }

  async fetchSignals(): Promise<SignalChunk[]> {
    const r = await fetch(`${this.base}/signals`);
    if (!r.ok) return [];
    return r.json();
  }

  async fetchPerception(): Promise<PerceptionEvent[]> {
    const r = await fetch(`${this.base}/perception`);
    if (!r.ok) return [];
    return r.json();
  }

  async fetchIntelligence(): Promise<IntelligenceEvent[]> {
    const r = await fetch(`${this.base}/intelligence`);
    if (!r.ok) return [];
    return r.json();
  }

  async fetchStateEvents(): Promise<StateEvent[]> {
    const r = await fetch(`${this.base}/state-events`);
    if (!r.ok) return [];
    return r.json();
  }

  async fetchAlerts(): Promise<Alert[]> {
    const r = await fetch(`${this.base}/alerts`);
    if (!r.ok) return [];
    return r.json();
  }

  async fetchVessels(): Promise<VesselSummary[]> {
    const r = await fetch(`${this.base}/vessels`);
    if (!r.ok) return [];
    return r.json();
  }

  async fetchStageMetrics(): Promise<StageMetric[]> {
    const r = await fetch(`${this.base}/stage-metrics`);
    if (!r.ok) return [];
    return r.json();
  }

  async fetchBucketStatus(): Promise<BucketStatus> {
    const r = await fetch(`${this.base}/bucket/status`);
    if (!r.ok) throw new Error("Failed to fetch bucket status");
    return r.json();
  }

  async fetchHealth(): Promise<SystemHealthFrame> {
    const r = await fetch(`${this.base}/health`);
    if (!r.ok) throw new Error("Failed to fetch system health");
    return r.json();
  }

  async fetchEventsOverTime(): Promise<any[]> {
    const r = await fetch(`${this.base}/events-over-time`);
    if (!r.ok) return [];
    return r.json();
  }

  async fetchValidationBreakdown(): Promise<any> {
    const r = await fetch(`${this.base}/validation-breakdown`);
    if (!r.ok) return { total: 0, allow: 0, flag: 0, deny: 0 };
    return r.json();
  }

  async fetchTrace(traceId: string): Promise<TraceLifecycle> {
    const r = await fetch(`${this.base}/trace/${traceId}`);
    if (!r.ok) throw new Error("Trace not found");
    return r.json();
  }
}

/* =========================================================
   EXPORT
========================================================= */

export const adapter: SvacsAdapter =
  env.useMock
    ? new MockAdapter()
    : new RealAdapter();
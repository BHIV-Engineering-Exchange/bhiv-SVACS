import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";

import Panel from "@/components/primitives/Panel";
import StatusDot from "@/components/shell/StatusDot";
import EventsOverTime from "@/components/charts/EventsOverTime";

import { fmtMs } from "@/lib/format";
import { fmtUtcDate } from "@/lib/time";

const fmtUptime = (s?: number) => {
  if (typeof s !== "number") {
    return "0h 0m";
  }

  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);

  return `${h}h ${m}m`;
};

export default function SystemHealth() {
  const hQ = useQuery({
    queryKey: ["health"],
    queryFn: () => adapter.fetchHealth(),
    refetchInterval: 2000,
  });

  const sQ = useQuery({
    queryKey: ["stages"],
    queryFn: () => adapter.fetchStageMetrics(),
    refetchInterval: 3000,
  });

  const eQ = useQuery({
    queryKey: ["eot"],
    queryFn: () =>
      adapter.fetchEventsOverTime(),
    refetchInterval: 6000,
  });

  const h = hQ.data;

  const stages = sQ.data ?? [];

  const errors = stages.reduce(
    (acc, s) =>
      acc +
      (Number(s.error_rate || 0) *
        Number(s.events_per_sec || 0) *
        60),
    0
  );

  const errCount =
    h?.error_count_60s ??
    Math.round(errors);

  return (
    <div className="space-y-4">
      {/* STATS */}
      <div className="grid grid-cols-12 gap-3">
        <Stat
          label="WS Connected"
          value={
            h?.ws_connected
              ? "YES"
              : "NO"
          }
          ok={!!h?.ws_connected}
        />

        <Stat
          label="Ingestion Rate"
          value={
            typeof h?.ingestion_rate ===
            "number"
              ? `${h.ingestion_rate.toFixed(
                  1
                )} ev/s`
              : "0.0 ev/s"
          }
        />

        <Stat
          label="Processing Latency"
          value={
            typeof h?.processing_latency_ms ===
            "number"
              ? fmtMs(
                  h.processing_latency_ms
                )
              : "0 ms"
          }
          ok={
            !h ||
            (typeof h.processing_latency_ms ===
              "number" &&
              h.processing_latency_ms < 80)
          }
        />

        <Stat
          label="Errors (60s)"
          value={String(errCount)}
          bad={errCount > 5}
        />

        <Stat
          label="Uptime"
          value={fmtUptime(
            h?.uptime_seconds
          )}
        />

        <Stat
          label="Last Telemetry"
          value={
            h?.last_telemetry_utc
              ? fmtUtcDate(
                  h.last_telemetry_utc
                )
              : "N/A"
          }
          mono
        />
      </div>

      {/* STAGE HEALTH */}
      <Panel title="Stage Health">
        <ul className="space-y-2">
          {stages.length === 0 ? (
            <li className="text-sm text-fg-2">
              No stage health data
              available
            </li>
          ) : (
            stages.map((s) => (
              <li
                key={s.stage}
                className="flex items-center gap-3 text-sm"
              >
                <StatusDot
                  status={
                    s.status || "live"
                  }
                />

                <span className="w-28 capitalize text-fg-0">
                  {s.stage}
                </span>

                <span className="font-mono text-fg-1">
                  {typeof s.events_per_sec ===
                  "number"
                    ? s.events_per_sec.toFixed(
                        1
                      )
                    : "0.0"}{" "}
                  ev/s
                </span>

                <span className="font-mono text-fg-2">
                  p50{" "}
                  {fmtMs(
                    Number(
                      s.p50_latency_ms || 0
                    )
                  )}{" "}
                  · p95{" "}
                  {fmtMs(
                    Number(
                      s.p95_latency_ms || 0
                    )
                  )}
                </span>

                <span
                  className={`ml-auto font-mono ${
                    Number(
                      s.error_rate || 0
                    ) > 0.01
                      ? "text-err"
                      : "text-fg-1"
                  }`}
                >
                  err{" "}
                  {(
                    Number(
                      s.error_rate || 0
                    ) * 100
                  ).toFixed(2)}
                  %
                </span>
              </li>
            ))
          )}
        </ul>
      </Panel>

      {/* THROUGHPUT */}
      <Panel title="Throughput">
        {eQ.data ? (
          <EventsOverTime
            data={eQ.data}
          />
        ) : (
          <div className="text-sm text-fg-2">
            No throughput data
          </div>
        )}
      </Panel>
    </div>
  );
}

function Stat({
  label,
  value,
  ok,
  bad,
  mono,
}: {
  label: string;
  value: string;
  ok?: boolean;
  bad?: boolean;
  mono?: boolean;
}) {
  return (
    <div className="panel col-span-6 p-4 md:col-span-4 xl:col-span-2">
      <div className="text-2xs uppercase tracking-[0.18em] text-fg-2">
        {label}
      </div>

      <div
        className={`mt-1 ${
          mono ? "text-base" : "text-2xl"
        } font-mono font-semibold tabular-nums ${
          bad
            ? "text-err"
            : ok
            ? "text-ok"
            : "text-fg-0"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
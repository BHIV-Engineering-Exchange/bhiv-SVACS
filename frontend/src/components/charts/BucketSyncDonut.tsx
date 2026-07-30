import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import StatusDot from "@/components/shell/StatusDot";
import type { BucketStatus, StageId } from "@/domain/types";
import { fmtUtc } from "@/lib/time";

const STAGE_LABEL: Record<StageId, string> = {
  signal: "Signal Chunks",
  perception: "Perception Events",
  intelligence: "Intelligence Events",
  state: "State Events",
  bucket: "Bucket Writes",
};

export default function BucketSyncDonut({
  status,
}: {
  status: BucketStatus;
}) {

  // =====================================================
  // SAFE FALLBACKS
  // =====================================================

  const syncPercent =
    typeof status?.sync_percent === "number"
      ? status.sync_percent
      : 0;

  const stagesSynced = Array.isArray(status?.stages_synced)
    ? status.stages_synced
    : [];

  const lastSyncUtc =
    status?.last_sync_utc || new Date().toISOString();

  // =====================================================
  // PIE CALCULATION
  // =====================================================

  const pct = Math.max(0, Math.min(1, syncPercent));

  const remaining = 1 - pct;

  const data = [
    {
      name: "synced",
      value: pct,
      color: "#22c55e",
    },
    {
      name: "pending",
      value: remaining,
      color: "#1c2530",
    },
  ];

  // =====================================================
  // UI
  // =====================================================

  return (
    <div className="chart-surface flex h-full min-h-[260px] w-full flex-col items-center justify-center gap-4 xl:flex-row">

      {/* ========================= */}
      {/* DONUT CHART */}
      {/* ========================= */}

      <div className="relative h-[140px] w-[140px] shrink-0">

        <ResponsiveContainer width="100%" height="100%">

          <PieChart>

            <Pie
              data={data}
              dataKey="value"
              cx="50%"
              cy="50%"
              innerRadius={46}
              outerRadius={66}
              startAngle={90}
              endAngle={-270}
              stroke="none"
            >

              {data.map((d, i) => (
                <Cell
                  key={i}
                  fill={d.color}
                />
              ))}

            </Pie>

          </PieChart>

        </ResponsiveContainer>

        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">

          <span className="font-mono text-2xl font-semibold tabular-nums text-fg-0">
            {(pct * 100).toFixed(0)}%
          </span>

        </div>

      </div>

      {/* ========================= */}
      {/* STATUS LIST */}
      {/* ========================= */}

      <div className="flex flex-col gap-1 text-xs">

        <div className="font-semibold text-fg-0">
          All stages in sync
        </div>

        <ul className="mt-1 space-y-1">

          {(
            [
              "signal",
              "perception",
              "intelligence",
              "state",
            ] as StageId[]
          ).map((s) => {

            const isSynced = stagesSynced.includes(s);

            return (
              <li
                key={s}
                className="flex items-center gap-2"
              >

                <StatusDot
                  status={isSynced ? "live" : "down"}
                  size={6}
                  pulse={false}
                />

                <span className="text-fg-1">
                  {STAGE_LABEL[s]}
                </span>

              </li>
            );
          })}

        </ul>

        <div className="mt-2 text-2xs text-fg-2">

          Last Sync:{" "}

          <span className="font-mono text-fg-1">
            {fmtUtc(lastSyncUtc)}
          </span>

        </div>

      </div>

    </div>
  );
}
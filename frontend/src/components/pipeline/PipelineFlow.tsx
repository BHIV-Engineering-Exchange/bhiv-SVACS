import { Radio, Eye, Brain, Flag, Database, Activity } from "lucide-react";
import StatusDot from "@/components/shell/StatusDot";
import type { StageMetric } from "@/domain/types";
import { fmtNum } from "@/lib/format";
import clsx from "clsx";

const stageStyle: Record<
  string,
  {
    icon: typeof Radio;
    ring: string;
    text: string;
    glow: string;
    label: string;
    sub: string;
  }
> = {
  signal: {
    icon: Radio,
    ring: "border-cyan-500/60",
    text: "text-cyan-400",
    glow: "shadow-[0_0_30px_-8px_rgba(34,211,238,0.6)]",
    label: "Signal Ingestion",
    sub: "RAW INPUT",
  },
  perception: {
    icon: Eye,
    ring: "border-blue-500/60",
    text: "text-blue-400",
    glow: "shadow-[0_0_30px_-8px_rgba(96,165,250,0.6)]",
    label: "Perception",
    sub: "LAYER 2",
  },
  intelligence: {
    icon: Brain,
    ring: "border-violet-500/60",
    text: "text-violet-400",
    glow: "shadow-[0_0_30px_-8px_rgba(167,139,250,0.6)]",
    label: "Intelligence",
    sub: "NICAI",
  },
  state: {
    icon: Flag,
    ring: "border-amber-500/60",
    text: "text-amber-400",
    glow: "shadow-[0_0_30px_-8px_rgba(251,191,36,0.6)]",
    label: "State Engine",
    sub: "EXECUTION",
  },
  bucket: {
    icon: Database,
    ring: "border-emerald-500/60",
    text: "text-emerald-400",
    glow: "shadow-[0_0_30px_-8px_rgba(16,185,129,0.6)]",
    label: "Bucket",
    sub: "TRUTH STORE",
  },
};

interface Props {
  metrics: StageMetric[];
  bucketSyncPct?: number;
  compact?: boolean;
}

export default function PipelineFlow({
  metrics,
  bucketSyncPct = 1,
  compact = false,
}: Props) {
  const order: StageMetric["stage"][] = [
    "signal",
    "perception",
    "intelligence",
    "state",
    "bucket",
  ];

  const map = new Map(metrics.map((m) => [m.stage, m]));

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div
        className={clsx(
          "flex shrink-0 items-center justify-between gap-3",
          compact ? "mb-3" : "mb-4",
        )}
      >
        <p className="truncate text-xs text-fg-2">
          Signal → Perception → Intelligence → State → Bucket
        </p>

        <div className="flex shrink-0 items-center gap-2">
          <div className="flex items-center gap-2 rounded-full border border-accent-green/30 bg-accent-green/10 px-2.5 py-0.5">
            <Activity className="h-3.5 w-3.5 text-accent-green" />
            <span className="text-2xs font-semibold uppercase tracking-[0.14em] text-accent-green">
              Live
            </span>
          </div>
          {compact && (
            <span className="hidden rounded-full bg-accent-green/10 px-2 py-0.5 text-2xs font-medium text-accent-green sm:inline">
              Healthy
            </span>
          )}
        </div>
      </div>

      {compact ? (
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
          {order.map((stageId, idx) => (
            <StageCard
              key={stageId}
              idx={idx}
              def={stageStyle[stageId]}
              value={
                stageId === "bucket"
                  ? `${(bucketSyncPct * 100).toFixed(0)}% Sync`
                  : fmtNum(map.get(stageId)?.total_events ?? 0)
              }
              compact
            />
          ))}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-3 lg:flex-row lg:items-stretch">
          {order.map((stageId, idx) => {
            const def = stageStyle[stageId];
            const value =
              stageId === "bucket"
                ? `${(bucketSyncPct * 100).toFixed(0)}% Sync`
                : fmtNum(map.get(stageId)?.total_events ?? 0);

            return (
              <div key={stageId} className="flex min-h-0 min-w-0 flex-1 items-stretch">
                <StageCard idx={idx} def={def} value={value} />
                {idx < order.length - 1 && <PipeArrow color={def.text} />}
              </div>
            );
          })}
        </div>
      )}

      {!compact && (
        <div className="mt-4 flex shrink-0 flex-wrap items-center gap-3 border-t border-line pt-3">
          <StatusDot status="live" />
          <span className="text-xs text-fg-2">Pipeline Status:</span>
          <span className="rounded-full bg-accent-green/10 px-2.5 py-0.5 text-xs font-medium text-accent-green">
            Healthy
          </span>
          <span className="ml-auto text-2xs text-fg-2">
            Deterministic Runtime Active
          </span>
        </div>
      )}
    </div>
  );
}

function StageCard({
  idx,
  def,
  value,
  compact = false,
}: {
  idx: number;
  def: (typeof stageStyle)[string];
  value: string;
  compact?: boolean;
}) {
  const Icon = def.icon;

  return (
    <div
      className={clsx(
        "relative flex h-full min-w-0 flex-col items-center rounded-lg border border-line bg-bg-2/80 transition-colors hover:border-line/80 hover:bg-bg-2",
        compact ? "px-1.5 pb-2.5 pt-4" : "min-w-0 flex-1 p-4 pt-5",
      )}
    >
      <div
        className={clsx(
          "absolute left-1/2 flex h-5 w-5 -translate-x-1/2 items-center justify-center rounded-full border border-line bg-bg-1 text-[10px] font-bold",
          compact ? "-top-2.5" : "-top-3 h-6 w-6 text-[11px]",
          def.text,
        )}
      >
        {idx + 1}
      </div>

      <div
        className={clsx(
          "flex shrink-0 items-center justify-center rounded-full border-2 bg-bg-1",
          compact ? "h-10 w-10" : "h-14 w-14",
          def.ring,
          def.glow,
        )}
      >
        <Icon
          size={compact ? 18 : 24}
          strokeWidth={1.8}
          className={def.text}
        />
      </div>

      <div
        className={clsx(
          "mt-1.5 flex w-full flex-col items-center justify-center text-center",
          compact ? "min-h-[2.25rem]" : "min-h-[3rem]",
        )}
      >
        <div className="text-[11px] font-semibold leading-tight text-fg-0 xl:text-xs">
          {compact && def.label === "Signal Ingestion" ? "Signal" : def.label}
        </div>
        {!compact && (
          <div className="mt-0.5 text-[10px] uppercase tracking-[0.16em] text-fg-2">
            {def.sub}
          </div>
        )}
      </div>

      <div
        className={clsx(
          "mt-auto w-full text-center font-mono font-bold tabular-nums text-fg-0",
          compact ? "pt-1 text-xs" : "pt-3 text-base",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function PipeArrow({ color }: { color: string }) {
  return (
    <div className="hidden w-5 shrink-0 items-center px-0.5 lg:flex">
      <div
        className={clsx(
          "h-[2px] flex-1 bg-gradient-to-r from-transparent via-current to-current opacity-70",
          color,
        )}
      />
      <svg className={clsx("h-3 w-3 shrink-0", color)} viewBox="0 0 12 12" fill="currentColor">
        <path d="M0 1 L10 6 L0 11 Z" opacity="0.9" />
      </svg>
    </div>
  );
}

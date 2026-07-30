import { AlertTriangle } from "lucide-react";
import type { Alert } from "@/domain/types";
import { fmtUtc } from "@/lib/time";
import SeverityChip from "@/components/primitives/SeverityChip";
import clsx from "clsx";

const sevColor = (s?: string) => {
  if (!s) return "text-info";

  if (s === "CRITICAL" || s === "HIGH") {
    return "text-err";
  }

  if (s === "MEDIUM") {
    return "text-warn";
  }

  return "text-info";
};

export default function AlertSummary({
  alerts,
}: {
  alerts: Alert[];
}) {
  return (
    <ul className="divide-y divide-line/60">
      {alerts.length === 0 ? (
        <li className="px-4 py-6 text-center text-sm text-fg-2">
          No active alerts
        </li>
      ) : (
        alerts.map((a, idx) => (
          <li
            key={a.id || idx}
            className="flex flex-col gap-1.5 px-4 py-3 transition-colors hover:bg-bg-2/40 sm:grid sm:grid-cols-[1rem_4.5rem_4.5rem_minmax(0,1fr)_auto] sm:items-center sm:gap-x-3 sm:py-2.5"
          >
            <AlertTriangle
              size={14}
              className={clsx("shrink-0", sevColor(a.severity))}
            />

            <span className="font-mono text-xs tabular-nums text-fg-1">
              {a.ts_utc ? fmtUtc(a.ts_utc) : "N/A"}
            </span>

            <span className="truncate font-mono text-xs text-fg-0">
              {a.vessel_id || "UNKNOWN"}
            </span>

            <span className="truncate text-xs text-fg-1">
              {a.message || a.kind || "Alert Triggered"}
            </span>

            <SeverityChip severity={a.severity || "LOW"} />
          </li>
        ))
      )}
    </ul>
  );
}
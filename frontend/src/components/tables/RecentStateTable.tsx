import type { StateEvent } from "@/domain/types";
import { fmtUtc } from "@/lib/time";
import { fmtConfidence } from "@/lib/format";
import ValidationChip from "@/components/primitives/ValidationChip";
import clsx from "clsx";

const stateColor = (s?: string) => {
  if (!s) return "text-fg-1";

  if (s === "ALERT") return "text-err";
  if (s === "WATCH") return "text-warn";
  if (s === "NORMAL") return "text-ok";

  return "text-fg-1";
};

export default function RecentStateTable({
  rows,
}: {
  rows: StateEvent[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-2xs font-semibold uppercase tracking-[0.14em] text-fg-2">
            <th className="px-4 py-2">Time</th>
            <th className="px-4 py-2">Vessel ID</th>
            <th className="px-4 py-2">State</th>
            <th className="px-4 py-2">Validation</th>
            <th className="px-4 py-2 text-right">Confidence</th>
          </tr>
        </thead>

        <tbody className="font-mono">
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={5}
                className="px-4 py-6 text-center text-fg-2"
              >
                No recent state events
              </td>
            </tr>
          ) : (
            rows.map((r, idx) => (
              <tr
                key={r.trace_id || idx}
                className="border-t border-line/60 transition-colors hover:bg-bg-2/40"
              >
                {/* TIME */}
                <td className="px-4 py-2 tabular-nums text-fg-1">
                  {r.ts_utc ? fmtUtc(r.ts_utc) : "N/A"}
                </td>

                {/* VESSEL */}
                <td className="px-4 py-2 text-fg-0">
                  {r.vessel_id || "UNKNOWN"}
                </td>

                {/* STATE */}
                <td
                  className={clsx(
                    "px-4 py-2 font-semibold",
                    stateColor(r.to_state),
                  )}
                >
                  {r.to_state || "NORMAL"}
                </td>

                {/* VALIDATION */}
                <td className="px-4 py-2">
                  <ValidationChip
                    validation={
                      r.validation || "ALLOW"
                    }
                  />
                </td>

                {/* CONFIDENCE */}
                <td className="px-4 py-2 text-right tabular-nums text-fg-0">
                  {typeof r.confidence === "number"
                    ? fmtConfidence(r.confidence)
                    : "0.50"}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
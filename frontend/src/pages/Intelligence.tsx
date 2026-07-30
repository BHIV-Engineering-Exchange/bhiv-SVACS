import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";

import Panel from "@/components/primitives/Panel";
import ValidationDonut from "@/components/charts/ValidationDonut";
import ValidationChip from "@/components/primitives/ValidationChip";

import { fmtUtc } from "@/lib/time";
import { fmtConfidence, truncId } from "@/lib/format";

export default function Intelligence() {
  const iQ = useQuery({
    queryKey: ["intelligence"],
    queryFn: () => adapter.fetchIntelligence(),
    refetchInterval: 3000,
  });

  const valQ = useQuery({
    queryKey: ["validation"],
    queryFn: () =>
      adapter.fetchValidationBreakdown(),
    refetchInterval: 6000,
  });

  const rows = iQ.data ?? [];

  return (
    <div className="space-y-4">
      {/* TOP PANELS */}
      <div className="grid grid-cols-12 gap-3">
        <Panel
          title="Validation Breakdown (NICAI)"
          className="col-span-12 lg:col-span-5"
        >
          {valQ.data && (
            <ValidationDonut
              total={valQ.data.total}
              allow={valQ.data.allow}
              flag={valQ.data.flag}
              deny={valQ.data.deny}
            />
          )}
        </Panel>

        <Panel
          title="Top Reasons (Last 100)"
          className="col-span-12 lg:col-span-7"
          noPad
        >
          <ReasonList rows={rows} />
        </Panel>
      </div>

      {/* TABLE */}
      <Panel title="Intelligence Events" noPad>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-2xs uppercase tracking-[0.14em] text-fg-2">
                <th className="px-4 py-2">
                  Time (UTC)
                </th>

                <th className="px-4 py-2">
                  Trace ID
                </th>

                <th className="px-4 py-2">
                  Vessel
                </th>

                <th className="px-4 py-2">
                  Validation
                </th>

                <th className="px-4 py-2">
                  Reasons
                </th>

                <th className="px-4 py-2 text-right">
                  Confidence
                </th>
              </tr>
            </thead>

            <tbody className="font-mono">
              {rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-6 text-center text-fg-2"
                  >
                    No intelligence events
                  </td>
                </tr>
              ) : (
                rows.map((r, i) => (
                  <tr
                    key={
                      r.trace_id || `intel-${i}`
                    }
                    className="border-t border-line/60 hover:bg-bg-2/40"
                  >
                    {/* TIME */}
                    <td className="px-4 py-2 tabular-nums text-fg-1">
                      {r.ts_utc ? fmtUtc(r.ts_utc) : "N/A"}
                    </td>

                    {/* TRACE */}
                    <td className="px-4 py-2 text-accent-cyan">
                      {r.trace_id
                        ? truncId(r.trace_id)
                        : "N/A"}
                    </td>

                    {/* VESSEL */}
                    <td className="px-4 py-2 text-fg-0">
                      {r.vessel_id || "UNKNOWN"}
                    </td>

                    {/* VALIDATION */}
                    <td className="px-4 py-2">
                      <ValidationChip
                        validation={
                          r.validation ||
                          "ALLOW"
                        }
                      />
                    </td>

                    {/* REASONS */}
                    <td className="px-4 py-2 text-fg-1">
                      {Array.isArray(
                        r.reasons
                      ) &&
                      r.reasons.length > 0
                        ? r.reasons.join(", ")
                        : "No reasons"}
                    </td>

                    {/* CONFIDENCE */}
                    <td className="px-4 py-2 text-right tabular-nums text-fg-0">
                      {typeof r.confidence ===
                      "number"
                        ? fmtConfidence(
                            r.confidence
                          )
                        : "0.50"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

/* ======================================================
   REASON LIST
====================================================== */

function ReasonList({
  rows,
}: {
  rows: {
    reasons?: string[];
    validation?: string;
  }[];
}) {
  const counts = new Map<string, number>();

  for (const r of rows) {
    if (!Array.isArray(r.reasons))
      continue;

    for (const reason of r.reasons) {
      counts.set(
        reason,
        (counts.get(reason) ?? 0) + 1
      );
    }
  }

  const sorted = [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);

  const max = sorted[0]?.[1] ?? 1;

  return (
    <ul className="divide-y divide-line/60">
      {sorted.length === 0 ? (
        <li className="px-4 py-6 text-center text-fg-2">
          No intelligence reasons available
        </li>
      ) : (
        sorted.map(([reason, count]) => (
          <li
            key={reason}
            className="px-4 py-2.5"
          >
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-fg-1">
                {reason}
              </span>

              <span className="font-mono tabular-nums text-fg-0">
                {count}
              </span>
            </div>

            <div className="mt-1 h-1 rounded bg-bg-2">
              <div
                className="h-full rounded bg-accent-violet/70"
                style={{
                  width: `${
                    (count / max) * 100
                  }%`,
                }}
              />
            </div>
          </li>
        ))
      )}
    </ul>
  );
}
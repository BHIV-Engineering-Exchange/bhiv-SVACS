import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";
import Panel from "@/components/primitives/Panel";
import SeverityChip from "@/components/primitives/SeverityChip";
import { fmtUtc } from "@/lib/time";
import { truncId } from "@/lib/format";
import type { Severity } from "@/domain/types";
import { Search } from "lucide-react";

const SEVS: ("ALL" | Severity)[] = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function Alerts() {
  const [q, setQ] = useState("");
  const [sev, setSev] = useState<"ALL" | Severity>("ALL");
  const alertsQ = useQuery({ queryKey: ["alerts"], queryFn: () => adapter.fetchAlerts(), refetchInterval: 4000 });

  const rows = useMemo(() => {
    return (alertsQ.data ?? [])
      .filter((a) => sev === "ALL" || a.severity === sev)
      .filter(
        (a) =>
          !q ||
          a.kind.toLowerCase().includes(q.toLowerCase()) ||
          a.vessel_id.toLowerCase().includes(q.toLowerCase()),
      );
  }, [alertsQ.data, sev, q]);

  return (
    <Panel
      title={`Alerts (${rows.length})`}
      noPad
      right={
        <div className="flex items-center gap-2">
          <select
            value={sev}
            onChange={(e) => setSev(e.target.value as "ALL" | Severity)}
            className="input"
          >
            {SEVS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <div className="relative">
            <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-fg-2" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filter by kind or vessel"
              className="input pl-7"
            />
          </div>
        </div>
      }
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-2xs uppercase tracking-[0.14em] text-fg-2">
            <th className="px-4 py-2">Time (UTC)</th>
            <th className="px-4 py-2">Severity</th>
            <th className="px-4 py-2">Kind</th>
            <th className="px-4 py-2">Vessel</th>
            <th className="px-4 py-2">Trace</th>
            <th className="px-4 py-2">Message</th>
            <th className="px-4 py-2">Ack</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((a) => (
            <tr key={a.id} className="border-t border-line/60 hover:bg-bg-2/40">
              <td className="px-4 py-2 tabular-nums text-fg-1">{fmtUtc(a.ts_utc)}</td>
              <td className="px-4 py-2">
                <SeverityChip severity={a.severity} />
              </td>
              <td className="px-4 py-2 text-fg-0">{a.kind}</td>
              <td className="px-4 py-2 text-fg-0">{a.vessel_id}</td>
              <td className="px-4 py-2 text-accent-cyan">
                {a.trace_id ? truncId(a.trace_id) : "—"}
              </td>
              <td className="px-4 py-2 text-fg-1">{a.message}</td>
              <td className="px-4 py-2 text-fg-2">{a.acknowledged ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

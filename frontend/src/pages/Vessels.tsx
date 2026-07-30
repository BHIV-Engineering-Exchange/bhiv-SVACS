import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";
import Panel from "@/components/primitives/Panel";
import { fmtNum } from "@/lib/format";
import { ageFrom } from "@/lib/time";
import { Search } from "lucide-react";
import clsx from "clsx";

const statusCls = (s: string) =>
  s === "ALERT"
    ? "border-err/40 text-err bg-err/10"
    : s === "WATCH"
      ? "border-warn/40 text-warn bg-warn/10"
      : "border-ok/40 text-ok bg-ok/10";

export default function Vessels() {
  const [q, setQ] = useState("");
  const vQ = useQuery({ queryKey: ["vessels"], queryFn: () => adapter.fetchVessels(), refetchInterval: 5000 });
  const rows = (vQ.data ?? []).filter((v) => v.vessel_id.toLowerCase().includes(q.toLowerCase()));

  return (
    <Panel
      title={`Vessels (${rows.length})`}
      noPad
      right={
        <div className="relative">
          <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-fg-2" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter vessel id"
            className="input pl-7"
          />
        </div>
      }
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-2xs uppercase tracking-[0.14em] text-fg-2">
            <th className="px-4 py-2">Vessel ID</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Last State</th>
            <th className="px-4 py-2 text-right">Signals</th>
            <th className="px-4 py-2 text-right">Perception</th>
            <th className="px-4 py-2 text-right">Intelligence</th>
            <th className="px-4 py-2 text-right">State Events</th>
            <th className="px-4 py-2 text-right">Last Seen</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((v) => (
            <tr key={v.vessel_id} className="border-t border-line/60 hover:bg-bg-2/40">
              <td className="px-4 py-2 text-fg-0">{v.vessel_id}</td>
              <td className="px-4 py-2">
                <span className={clsx("chip", statusCls(v.status))}>{v.status}</span>
              </td>
              <td className="px-4 py-2 text-fg-1">{v.last_state}</td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-0">{fmtNum(v.signal_count)}</td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-1">{fmtNum(v.perception_count)}</td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-1">{fmtNum(v.intelligence_count)}</td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-1">{fmtNum(v.state_count)}</td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-2">{ageFrom(v.last_seen_utc)} ago</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

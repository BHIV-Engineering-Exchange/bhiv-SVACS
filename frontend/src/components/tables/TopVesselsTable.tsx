import type { VesselSummary } from "@/domain/types";
import { fmtNum } from "@/lib/format";

export default function TopVesselsTable({ rows }: { rows: VesselSummary[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-2xs font-semibold uppercase tracking-[0.14em] text-fg-2">
            <th className="px-4 py-2">Vessel ID</th>
            <th className="px-4 py-2 text-right">Signal</th>
            <th className="px-4 py-2 text-right">Perception</th>
            <th className="px-4 py-2 text-right">Intelligence</th>
            <th className="px-4 py-2 text-right">State</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((v) => (
            <tr
              key={v.vessel_id}
              className="border-t border-line/60 transition-colors hover:bg-bg-2/40"
            >
              <td className="px-4 py-2 text-fg-0">{v.vessel_id}</td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-0">
                {fmtNum(v.signal_count)}
              </td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-1">
                {fmtNum(v.perception_count)}
              </td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-1">
                {fmtNum(v.intelligence_count)}
              </td>
              <td className="px-4 py-2 text-right tabular-nums text-fg-1">
                {fmtNum(v.state_count)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

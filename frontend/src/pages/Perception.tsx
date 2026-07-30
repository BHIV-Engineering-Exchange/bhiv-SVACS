import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";
import Panel from "@/components/primitives/Panel";
import { fmtUtc } from "@/lib/time";
import { fmtConfidence, truncId } from "@/lib/format";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

const histogram = (vals: number[]) => {
  const buckets = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9];
  return buckets.map((b, i) => ({
    range: `${b.toFixed(1)}–${(b + 0.1).toFixed(1)}`,
    count: vals.filter((v) => v >= b && v < (i === buckets.length - 1 ? 1.001 : b + 0.1)).length,
  }));
};

export default function Perception() {
  const pQ = useQuery({ queryKey: ["perception"], queryFn: () => adapter.fetchPerception(), refetchInterval: 3000 });
  const rows = pQ.data ?? [];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-12 gap-3">
        <Panel title="Confidence Histogram" className="col-span-12 lg:col-span-5">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={histogram(rows.map((r) => r.confidence))}>
              <CartesianGrid stroke="#1c2530" strokeDasharray="2 4" vertical={false} />
              <XAxis
                dataKey="range"
                stroke="#5e6b76"
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                stroke="#5e6b76"
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                axisLine={false}
                tickLine={false}
                width={32}
              />
              <Tooltip
                contentStyle={{
                  background: "#0b1014",
                  border: "1px solid #1c2530",
                  borderRadius: 6,
                  fontSize: 11,
                  fontFamily: "JetBrains Mono",
                }}
              />
              <Bar dataKey="count" fill="#4ade80" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Detection Stats" className="col-span-12 lg:col-span-7">
          <div className="grid grid-cols-3 gap-3">
            <Stat
              label="Total Events"
              value={rows.length.toLocaleString()}
              accent="text-accent-green"
            />
            <Stat
              label="Avg Confidence"
              value={
                rows.length
                  ? fmtConfidence(rows.reduce((a, b) => a + b.confidence, 0) / rows.length)
                  : "—"
              }
              accent="text-accent-cyan"
            />
            <Stat
              label="High Conf (>0.85)"
              value={rows.filter((r) => r.confidence > 0.85).length.toLocaleString()}
              accent="text-accent-violet"
            />
          </div>
        </Panel>
      </div>

      <Panel title="Perception Events" noPad>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-2xs uppercase tracking-[0.14em] text-fg-2">
              <th className="px-4 py-2">Time (UTC)</th>
              <th className="px-4 py-2">Trace ID</th>
              <th className="px-4 py-2">Vessel</th>
              <th className="px-4 py-2">Kind</th>
              <th className="px-4 py-2 text-right">Confidence</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {rows.map((r) => (
              <tr key={r.trace_id + r.parent_chunk_id} className="border-t border-line/60 hover:bg-bg-2/40">
                <td className="px-4 py-2 tabular-nums text-fg-1">{fmtUtc(r.ts_utc)}</td>
                <td className="px-4 py-2 text-accent-cyan">{truncId(r.trace_id)}</td>
                <td className="px-4 py-2 text-fg-0">{r.vessel_id ?? "—"}</td>
                <td className="px-4 py-2 text-fg-1">{r.kind}</td>
                <td className="px-4 py-2 text-right tabular-nums text-fg-0">
                  {fmtConfidence(r.confidence)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="rounded-md border border-line bg-bg-2/40 p-4">
      <div className="text-2xs uppercase tracking-[0.18em] text-fg-2">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${accent}`}>
        {value}
      </div>
    </div>
  );
}

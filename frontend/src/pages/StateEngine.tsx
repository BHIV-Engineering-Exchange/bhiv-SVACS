import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";
import Panel from "@/components/primitives/Panel";
import RecentStateTable from "@/components/tables/RecentStateTable";

export default function StateEngine() {
  const stateQ = useQuery({ queryKey: ["state"], queryFn: () => adapter.fetchStateEvents(), refetchInterval: 3000 });
  const rows = stateQ.data ?? [];

  const transitions = new Map<string, number>();
  for (const r of rows) {
    const k = `${r.from_state} → ${r.to_state}`;
    transitions.set(k, (transitions.get(k) ?? 0) + 1);
  }
  const top = [...transitions.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
  const max = top[0]?.[1] ?? 1;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-12 gap-3">
        <Panel
          title="Top Transitions"
          className="col-span-12 lg:col-span-5"
          noPad
        >
          <ul className="divide-y divide-line/60">
            {top.map(([k, count]) => (
              <li key={k} className="px-4 py-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-fg-0">{k}</span>
                  <span className="font-mono tabular-nums text-fg-1">{count}</span>
                </div>
                <div className="mt-1 h-1 rounded bg-bg-2">
                  <div
                    className="h-full rounded bg-accent-amber/70"
                    style={{ width: `${(count / max) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel
          title="State Stats"
          className="col-span-12 lg:col-span-7"
        >
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Total Transitions" value={rows.length.toLocaleString()} accent="text-accent-amber" />
            <Stat
              label="ALERT-bound"
              value={rows.filter((r) => r.to_state === "ALERT").length.toLocaleString()}
              accent="text-err"
            />
            <Stat
              label="NORMAL-bound"
              value={rows.filter((r) => r.to_state === "NORMAL").length.toLocaleString()}
              accent="text-ok"
            />
          </div>
        </Panel>
      </div>

      <Panel title="Recent State Events" noPad>
        <RecentStateTable rows={rows} />
      </Panel>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="rounded-md border border-line bg-bg-2/40 p-4">
      <div className="text-2xs uppercase tracking-[0.18em] text-fg-2">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${accent}`}>{value}</div>
    </div>
  );
}

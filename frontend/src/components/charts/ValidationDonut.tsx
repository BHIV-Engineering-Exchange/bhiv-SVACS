import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { fmtNum, fmtPct } from "@/lib/format";

interface Props {
  total: number;
  allow: number;
  flag: number;
  deny?: number;
}

export default function ValidationDonut({ total, allow, flag, deny = 0 }: Props) {
  const data = [
    { name: "ALLOW", value: allow, color: "#22c55e" },
    { name: "FLAG", value: flag, color: "#f59e0b" },
    ...(deny > 0 ? [{ name: "DENY", value: deny, color: "#ef4444" }] : []),
  ];

  const allowPct = total > 0 ? allow / total : 0;
  const flagPct = total > 0 ? flag / total : 0;

  return (
    <div className="chart-surface flex h-full min-h-[260px] w-full flex-col items-center justify-center gap-4 sm:flex-row">
      <div className="relative h-[132px] w-[132px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              cx="50%"
              cy="50%"
              innerRadius={46}
              outerRadius={66}
              paddingAngle={2}
              stroke="none"
            >
              {data.map((d, i) => (
                <Cell key={i} fill={d.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-semibold tabular-nums text-fg-0">
            {fmtNum(total)}
          </span>
          <span className="text-2xs uppercase tracking-[0.16em] text-fg-2">Total</span>
        </div>
      </div>

      <div className="flex flex-col gap-3 text-sm">
        <LegendRow color="#22c55e" label="ALLOW" value={allow} pct={allowPct} />
        <LegendRow color="#f59e0b" label="FLAG" value={flag} pct={flagPct} />
        {deny > 0 && (
          <LegendRow color="#ef4444" label="DENY" value={deny} pct={deny / total} />
        )}
      </div>
    </div>
  );
}

function LegendRow({
  color,
  label,
  value,
  pct,
}: {
  color: string;
  label: string;
  value: number;
  pct: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{ background: color, boxShadow: `0 0 10px ${color}55` }}
      />
      <div className="flex flex-col leading-tight">
        <span className="text-2xs font-semibold uppercase tracking-[0.18em] text-fg-1">
          {label}
        </span>
        <span className="font-mono text-xs tabular-nums text-fg-0">
          {fmtNum(value)} ({fmtPct(pct)})
        </span>
      </div>
    </div>
  );
}

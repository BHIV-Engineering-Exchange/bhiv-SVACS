import Panel from "@/components/primitives/Panel";

const rows = [
  { label: "TTG Status", value: "ACTIVE" },
  { label: "Simulator Link", value: "CONNECTED" },
  { label: "Runtime Visibility", value: "ENABLED" },
  { label: "Operational Sync", value: "VERIFIED" },
];

export default function TTGCard() {
  return (
    <Panel title="TTG Runtime">
      <dl className="space-y-2.5">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex items-baseline justify-between gap-3 text-sm">
            <dt className="shrink-0 text-fg-2">{label}</dt>
            <dd className="text-right font-mono text-xs font-medium text-accent-cyan">{value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}

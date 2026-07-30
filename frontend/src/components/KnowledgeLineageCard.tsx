import Panel from "@/components/primitives/Panel";

const rows = [
  { label: "Jane's Registry", value: "CONNECTED" },
  { label: "AIS Runtime", value: "VERIFIED" },
  { label: "Replay Continuity", value: "VERIFIED" },
  { label: "Lineage Hash", value: "ACTIVE" },
];

export default function KnowledgeLineageCard() {
  return (
    <Panel title="Knowledge Lineage">
      <dl className="space-y-2.5">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex items-baseline justify-between gap-3 text-sm">
            <dt className="shrink-0 text-fg-2">{label}</dt>
            <dd className="text-right font-mono text-xs font-medium text-accent-green">{value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}

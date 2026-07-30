import Panel from "@/components/primitives/Panel";

const rows = [
  { label: "Vessel", value: "Vessel_004" },
  { label: "Class", value: "Destroyer" },
  { label: "Threat", value: "Medium" },
  { label: "Confidence", value: "92%" },
  { label: "Source", value: "Jane's Fighting Ships" },
];

export default function MaritimeIntelligenceCard() {
  return (
    <Panel title="Maritime Intelligence">
      <dl className="space-y-2.5">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex items-baseline justify-between gap-3 text-sm">
            <dt className="shrink-0 text-fg-2">{label}</dt>
            <dd className="text-right font-medium text-fg-0">{value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}

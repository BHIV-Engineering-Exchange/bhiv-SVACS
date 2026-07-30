import Panel from "@/components/primitives/Panel";

const rows = [
  { label: "AIS", value: "ACTIVE" },
  { label: "Radar", value: "ACTIVE" },
  { label: "Metadata Fusion", value: "VERIFIED" },
  { label: "Classification Confidence", value: "88%" },
];

export default function SensorFusionCard() {
  return (
    <Panel title="Sensor Fusion">
      <dl className="space-y-2.5">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex items-baseline justify-between gap-3 text-sm">
            <dt className="shrink-0 text-fg-2">{label}</dt>
            <dd className="text-right font-mono text-xs font-medium text-fg-0">{value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}

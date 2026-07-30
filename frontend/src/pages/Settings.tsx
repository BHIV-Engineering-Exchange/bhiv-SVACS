import Panel from "@/components/primitives/Panel";
import { env } from "@/env";

export default function Settings() {
  const rows: Array<[string, string]> = [
    ["Mock adapter", env.useMock ? "ENABLED (development only)" : "DISABLED (using real APIs)"],
    ["Signal API", env.api.signal || "—"],
    ["Perception API", env.api.perception || "—"],
    ["Intelligence API", env.api.intelligence || "—"],
    ["State API", env.api.state || "—"],
    ["Bucket API", env.api.bucket || "—"],
    ["Telemetry WS", env.api.telemetryWs || "—"],
    ["Poll interval (ms)", String(env.pollIntervalMs)],
  ];

  return (
    <div className="space-y-4">
      <Panel title="Runtime Configuration">
        <table className="w-full text-sm">
          <tbody className="font-mono">
            {rows.map(([k, v]) => (
              <tr key={k} className="border-t border-line/60 first:border-t-0">
                <td className="px-3 py-2 text-fg-2">{k}</td>
                <td className="px-3 py-2 text-fg-0">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="About">
        <div className="space-y-2 text-sm text-fg-1">
          <p>
            <span className="text-fg-0">SVACS Dashboard</span> — Operational
            Intelligence Interface. The dashboard is a frontend application that
            consumes the real signal, perception, intelligence, state, and
            bucket APIs from the SVACS backend services.
          </p>
          <p className="text-fg-2">
            Configure backend endpoints via <span className="font-mono">.env.local</span>.
            Set <span className="font-mono">VITE_USE_MOCK=false</span> for the
            final integration demo.
          </p>
        </div>
      </Panel>
    </div>
  );
}

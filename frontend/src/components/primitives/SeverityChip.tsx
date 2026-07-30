import clsx from "clsx";
import type { Severity } from "@/domain/types";

const map: Record<Severity, string> = {
  LOW: "border-info/40 text-info bg-info/10",
  MEDIUM: "border-warn/40 text-warn bg-warn/10",
  HIGH: "border-err/40 text-err bg-err/10",
  CRITICAL: "border-err/60 text-err bg-err/20",
};

export default function SeverityChip({ severity }: { severity: Severity }) {
  return (
    <span className={clsx("chip uppercase", map[severity])}>
      {severity === "CRITICAL" ? "Critical" : severity[0] + severity.slice(1).toLowerCase()}
    </span>
  );
}

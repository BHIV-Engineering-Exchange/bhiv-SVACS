import clsx from "clsx";
import type { Validation } from "@/domain/types";

const map: Record<string, string> = {
  ALLOW:
    "border-emerald-500/40 text-emerald-400 bg-emerald-500/10",

  FLAG:
    "border-amber-500/40 text-amber-400 bg-amber-500/10",

  DENY:
    "border-red-500/40 text-red-400 bg-red-500/10",

  UNKNOWN:
    "border-zinc-500/40 text-zinc-300 bg-zinc-500/10",
};

export default function ValidationChip({
  validation,
}: {
  validation?: Validation | string;
}) {
  const value =
    validation?.toUpperCase?.() || "UNKNOWN";

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]",
        map[value] || map.UNKNOWN
      )}
    >
      {value}
    </span>
  );
}
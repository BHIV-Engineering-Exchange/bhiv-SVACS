import clsx from "clsx";

type Status = "live" | "degraded" | "stale" | "down";

const colorMap: Record<Status, string> = {
  live: "bg-ok shadow-ok/40",
  degraded: "bg-warn shadow-warn/40",
  stale: "bg-fg-2 shadow-fg-2/40",
  down: "bg-err shadow-err/40",
};

export default function StatusDot({
  status = "live",
  pulse = true,
  size = 8,
}: {
  status?: Status;
  pulse?: boolean;
  size?: number;
}) {
  return (
    <span
      className={clsx(
        "inline-block rounded-full shadow-[0_0_8px]",
        colorMap[status],
        pulse && status === "live" && "animate-pulse-soft",
      )}
      style={{ width: size, height: size }}
    />
  );
}

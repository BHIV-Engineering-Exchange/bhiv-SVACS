import { useLocation } from "react-router-dom";
import {
  ChevronDown,
  Calendar,
  RefreshCw,
  X,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import StatusDot from "./StatusDot";
import { useFilterStore } from "@/store/filterStore";
import { useHealthStore } from "@/store/healthStore";
import { useShellStore } from "@/store/shellStore";

const titleFor = (path: string): { title: string; subtitle: string } => {
  const map: Record<string, { title: string; subtitle: string }> = {
    "/": {
      title: "SVACS Dashboard",
      subtitle: "Signal → Intelligence → State Execution",
    },
    "/pipeline": {
      title: "Live Pipeline",
      subtitle: "End-to-end stage flow with latency telemetry",
    },
    "/signals": { title: "Signals", subtitle: "Raw signal_chunk stream" },
    "/perception": { title: "Perception", subtitle: "Layer-2 detections + confidence" },
    "/intelligence": { title: "Intelligence (NICAI)", subtitle: "Validation + reasoning" },
    "/state": { title: "State Engine", subtitle: "State transitions + execution" },
    "/vessels": { title: "Vessels", subtitle: "Per-vessel activity + last known state" },
    "/alerts": { title: "Alerts", subtitle: "Anomaly + validation failures" },
    "/trace": { title: "Trace Explorer", subtitle: "Inspect lifecycle by trace_id" },
    "/bucket": { title: "Bucket Status", subtitle: "Truth Store sync + verification" },
    "/health": {
      title: "System Health",
      subtitle: "Throughput, latency, ingestion, errors",
    },
    "/settings": { title: "Settings", subtitle: "Operator preferences" },
  };
  return map[path] ?? map["/"];
};

export default function Topbar() {
  const { pathname } = useLocation();
  const { vesselId, fromUtc, toUtc, setVessel, setRange } = useFilterStore();
  const wsConnected = useHealthStore((s) => s.wsConnected);
  const { title, subtitle } = titleFor(pathname);
  const toggleMobile = useShellStore((s) => s.toggleMobile);
  const toggleCollapsed = useShellStore((s) => s.toggleCollapsed);
  const collapsed = useShellStore((s) => s.collapsed);

  return (
    <header className="shrink-0 border-b border-line bg-bg-1/40 backdrop-blur-xl">
      <div className="flex h-14 items-center gap-2 px-3 sm:h-16 sm:gap-3 sm:px-4 lg:px-6">
        <button
          type="button"
          onClick={toggleMobile}
          className="btn shrink-0 p-2 lg:hidden"
          aria-label="Open navigation menu"
        >
          <Menu size={18} />
        </button>

        <button
          type="button"
          onClick={toggleCollapsed}
          className="btn hidden shrink-0 p-2 lg:inline-flex"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>

        <div className="flex min-w-0 flex-1 flex-col leading-tight">
          <span className="truncate text-sm font-semibold tracking-wide text-fg-0 sm:text-base">
            {title}
          </span>
          <span className="hidden truncate text-[11px] text-fg-2 sm:block">{subtitle}</span>
        </div>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <div className="relative hidden md:block">
            <select
              value={vesselId}
              onChange={(e) => setVessel(e.target.value)}
              className="input appearance-none pr-8 text-xs sm:text-sm"
            >
              <option value="ALL">All Vessels</option>
              {Array.from({ length: 24 }).map((_, i) => {
                const id = `Vessel_${String(i + 1).padStart(2, "0")}`;
                return (
                  <option key={id} value={id}>
                    {id}
                  </option>
                );
              })}
            </select>
            <ChevronDown
              size={14}
              className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-fg-2"
            />
          </div>

          <button type="button" className="btn p-2" title="Refresh now">
            <RefreshCw size={14} />
          </button>

          <div className="flex items-center gap-1.5 rounded-md border border-line bg-bg-2 px-2 py-1.5 sm:gap-2 sm:px-3">
            <StatusDot status={wsConnected ? "live" : "down"} />
            <span className="hidden text-2xs font-semibold uppercase tracking-[0.18em] text-fg-1 sm:inline">
              {wsConnected ? "Live" : "Offline"}
            </span>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-line/60 px-3 py-2 md:hidden">
        <div className="relative min-w-0 flex-1">
          <select
            value={vesselId}
            onChange={(e) => setVessel(e.target.value)}
            className="input w-full appearance-none pr-8 text-xs"
          >
            <option value="ALL">All Vessels</option>
            {Array.from({ length: 24 }).map((_, i) => {
              const id = `Vessel_${String(i + 1).padStart(2, "0")}`;
              return (
                <option key={id} value={id}>
                  {id}
                </option>
              );
            })}
          </select>
          <ChevronDown
            size={14}
            className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-fg-2"
          />
        </div>

        <div className="flex w-full items-center gap-1 rounded-md border border-line bg-bg-2 px-2 py-1.5">
          <Calendar size={14} className="shrink-0 text-fg-2" />
          <input
            value={fromUtc}
            onChange={(e) => setRange(e.target.value, toUtc)}
            className="min-w-0 flex-1 bg-transparent font-mono text-[11px] text-fg-0 focus:outline-none"
            placeholder="From"
          />
          <span className="text-fg-2">–</span>
          <input
            value={toUtc}
            onChange={(e) => setRange(fromUtc, e.target.value)}
            className="min-w-0 flex-1 bg-transparent font-mono text-[11px] text-fg-0 focus:outline-none"
            placeholder="To"
          />
          <button
            type="button"
            onClick={() => setRange("", "")}
            className="shrink-0 text-fg-2 hover:text-fg-0"
            title="Clear range"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      <div className="hidden items-center gap-2 border-t border-line/60 px-4 py-2 md:flex lg:px-6">
        <div className="flex items-center gap-1 rounded-md border border-line bg-bg-2 px-2 py-1.5">
          <Calendar size={14} className="text-fg-2" />
          <input
            value={fromUtc}
            onChange={(e) => setRange(e.target.value, toUtc)}
            className="w-28 bg-transparent font-mono text-xs text-fg-0 focus:outline-none lg:w-32"
            placeholder="YYYY-MM-DD HH:mm"
          />
          <span className="px-1 text-fg-2">to</span>
          <input
            value={toUtc}
            onChange={(e) => setRange(fromUtc, e.target.value)}
            className="w-28 bg-transparent font-mono text-xs text-fg-0 focus:outline-none lg:w-32"
            placeholder="YYYY-MM-DD HH:mm"
          />
          <button
            type="button"
            onClick={() => setRange("", "")}
            className="ml-1 text-fg-2 hover:text-fg-0"
            title="Clear range"
          >
            <X size={14} />
          </button>
        </div>
      </div>
    </header>
  );
}

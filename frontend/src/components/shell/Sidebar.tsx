import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Activity,
  Radio,
  Eye,
  Brain,
  Flag,
  Ship,
  AlertTriangle,
  Search,
  Database,
  HeartPulse,
  Settings as SettingsIcon,
  X,
} from "lucide-react";
import clsx from "clsx";
import StatusDot from "./StatusDot";
import { nowUtcDisplay } from "@/lib/time";
import { useEffect, useState } from "react";
import { useShellStore } from "@/store/shellStore";

const items = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/pipeline", label: "Live Pipeline", icon: Activity },
  { to: "/signals", label: "Signals", icon: Radio },
  { to: "/perception", label: "Perception", icon: Eye },
  { to: "/intelligence", label: "Intelligence", icon: Brain },
  { to: "/state", label: "State Engine", icon: Flag },
  { to: "/vessels", label: "Vessels", icon: Ship },
  { to: "/alerts", label: "Alerts", icon: AlertTriangle },
  { to: "/trace", label: "Traces", icon: Search },
  { to: "/bucket", label: "Bucket Status", icon: Database },
  { to: "/health", label: "System Health", icon: HeartPulse },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function Sidebar() {
  const [now, setNow] = useState(nowUtcDisplay());
  const { pathname } = useLocation();
  const collapsed = useShellStore((s) => s.collapsed);
  const mobileOpen = useShellStore((s) => s.mobileOpen);
  const closeMobile = useShellStore((s) => s.closeMobile);

  useEffect(() => {
    const id = setInterval(() => setNow(nowUtcDisplay()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    closeMobile();
  }, [pathname, closeMobile]);

  return (
    <aside
      className={clsx(
        "fixed inset-y-0 left-0 z-50 flex h-screen flex-col border-r border-line bg-bg-1/95 backdrop-blur-xl transition-[width,transform] duration-300 ease-in-out lg:static lg:translate-x-0",
        collapsed ? "w-[4.5rem]" : "w-64",
        mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
      )}
    >
      <div
        className={clsx(
          "flex items-center border-b border-line/60 lg:border-b-0",
          collapsed ? "justify-center px-2 pt-5 pb-4" : "gap-2 px-4 pt-5 pb-4",
        )}
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-accent-cyan/40 bg-accent-cyan/10">
          <span className="font-mono text-[11px] font-bold tracking-wider text-accent-cyan">
            SV
          </span>
        </div>

        {!collapsed && (
          <div className="flex min-w-0 flex-1 flex-col leading-tight">
            <span className="text-sm font-semibold tracking-wide text-fg-0">SVACS</span>
            <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-fg-2">
              Truth. Layered. Actionable.
            </span>
          </div>
        )}

        <button
          type="button"
          onClick={closeMobile}
          className="ml-auto rounded-md p-1.5 text-fg-2 hover:bg-bg-2 hover:text-fg-0 lg:hidden"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-4 lg:px-3">
        <ul className="space-y-0.5">
          {items.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                title={collapsed ? label : undefined}
                className={({ isActive }) =>
                  clsx(
                    "nav-item",
                    collapsed && "nav-item-collapsed justify-center px-2",
                    isActive && "nav-item-active",
                  )
                }
              >
                <Icon size={16} strokeWidth={1.75} className="shrink-0" />
                {!collapsed && <span className="truncate">{label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {!collapsed && (
        <div className="border-t border-line px-4 py-3">
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-fg-2">
            UTC Time
          </div>
          <div className="font-mono text-xs text-fg-0">{now}</div>
          <div className="mt-3 text-[10px] font-medium uppercase tracking-[0.18em] text-fg-2">
            User
          </div>
          <div className="flex items-center gap-2 font-mono text-xs text-fg-0">
            <StatusDot status="live" size={6} />
            svacs_admin
          </div>
        </div>
      )}

      {collapsed && (
        <div className="flex justify-center border-t border-line py-3">
          <StatusDot status="live" size={8} />
        </div>
      )}
    </aside>
  );
}

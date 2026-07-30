import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useShellStore } from "@/store/shellStore";

export default function AppShell() {
  const mobileOpen = useShellStore((s) => s.mobileOpen);
  const closeMobile = useShellStore((s) => s.closeMobile);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-bg-0 text-fg-0">
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={closeMobile}
        />
      )}

      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-auto px-4 py-4 sm:px-5 lg:px-6 lg:py-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

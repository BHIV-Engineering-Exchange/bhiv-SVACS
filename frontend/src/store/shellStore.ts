import { create } from "zustand";

interface ShellState {
  mobileOpen: boolean;
  collapsed: boolean;
  openMobile: () => void;
  closeMobile: () => void;
  toggleMobile: () => void;
  toggleCollapsed: () => void;
}

export const useShellStore = create<ShellState>((set) => ({
  mobileOpen: false,
  collapsed: false,
  openMobile: () => set({ mobileOpen: true }),
  closeMobile: () => set({ mobileOpen: false }),
  toggleMobile: () => set((s) => ({ mobileOpen: !s.mobileOpen })),
  toggleCollapsed: () => set((s) => ({ collapsed: !s.collapsed })),
}));

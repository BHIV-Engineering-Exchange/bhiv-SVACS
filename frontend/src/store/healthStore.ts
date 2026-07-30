import { create } from "zustand";

interface HealthState {
  wsConnected: boolean;
  lastTelemetryAt: string | null;
  setWsConnected: (v: boolean) => void;
  ping: () => void;
}

export const useHealthStore = create<HealthState>((set) => ({
  wsConnected: true,
  lastTelemetryAt: new Date().toISOString(),
  setWsConnected: (v) => set({ wsConnected: v }),
  ping: () => set({ lastTelemetryAt: new Date().toISOString() }),
}));

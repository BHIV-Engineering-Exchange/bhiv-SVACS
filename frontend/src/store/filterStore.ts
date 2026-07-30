import { create } from "zustand";

export interface FilterState {
  vesselId: string | "ALL";
  fromUtc: string;
  toUtc: string;
  setVessel: (id: string | "ALL") => void;
  setRange: (from: string, to: string) => void;
}

const today = new Date();
const aWeekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
const fmt = (d: Date) =>
  `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;

export const useFilterStore = create<FilterState>((set) => ({
  vesselId: "ALL",
  fromUtc: `${fmt(aWeekAgo)} 00:00`,
  toUtc: `${fmt(today)} 23:59`,
  setVessel: (id) => set({ vesselId: id }),
  setRange: (fromUtc, toUtc) => set({ fromUtc, toUtc }),
}));

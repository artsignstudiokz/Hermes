import { create } from "zustand";

interface SystemState {
  online: boolean;
  setOnline: (v: boolean) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  online: true,
  setOnline: (v) => set({ online: v }),
}));

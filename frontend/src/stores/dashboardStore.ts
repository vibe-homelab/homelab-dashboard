import { create } from 'zustand';
import type { ServiceStatus, SystemOverview } from '../types';

interface DashboardState {
  services: Map<string, ServiceStatus>;
  systemOverview: SystemOverview | null;
  wsConnected: boolean;
  lastUpdate: number | null;

  // Actions
  setServices: (services: ServiceStatus[]) => void;
  updateService: (service: ServiceStatus) => void;
  setSystemOverview: (overview: SystemOverview) => void;
  setWsConnected: (connected: boolean) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  services: new Map(),
  systemOverview: null,
  wsConnected: false,
  lastUpdate: null,

  setServices: (services) =>
    set({
      services: new Map(services.map((s) => [s.service_id, s])),
      lastUpdate: Date.now(),
    }),

  updateService: (service) =>
    set((state) => ({
      services: new Map(state.services).set(service.service_id, service),
      lastUpdate: Date.now(),
    })),

  setSystemOverview: (overview) => set({ systemOverview: overview }),

  setWsConnected: (connected) => set({ wsConnected: connected }),
}));

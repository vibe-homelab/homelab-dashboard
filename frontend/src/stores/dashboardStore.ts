import { create } from 'zustand';
import type { GpuPoolState, QueueState, ServiceState, FullStateData } from '../types';

interface DashboardState {
  gpus: GpuPoolState | null;
  queue: QueueState | null;
  services: Record<string, ServiceState>;
  wsConnected: boolean;
  lastUpdate: number | null;

  // Actions
  setFullState: (data: FullStateData) => void;
  setGpuState: (gpus: GpuPoolState) => void;
  setQueueState: (queue: QueueState) => void;
  setServiceState: (serviceId: string, state: ServiceState) => void;
  setAllServices: (services: Record<string, ServiceState>) => void;
  setWsConnected: (connected: boolean) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  gpus: null,
  queue: null,
  services: {},
  wsConnected: false,
  lastUpdate: null,

  setFullState: (data) =>
    set({
      gpus: data.gpus,
      queue: data.queue,
      services: data.services,
      lastUpdate: Date.now(),
    }),

  setGpuState: (gpus) =>
    set({ gpus, lastUpdate: Date.now() }),

  setQueueState: (queue) =>
    set({ queue, lastUpdate: Date.now() }),

  setServiceState: (serviceId, state) =>
    set((prev) => ({
      services: { ...prev.services, [serviceId]: state },
      lastUpdate: Date.now(),
    })),

  setAllServices: (services) =>
    set({ services, lastUpdate: Date.now() }),

  setWsConnected: (connected) => set({ wsConnected: connected }),
}));

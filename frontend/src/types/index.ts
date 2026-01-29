export interface GatewayStatus {
  reachable: boolean;
  latency_ms?: number;
  error?: string;
}

export interface WorkerStatus {
  alias: string;
  name: string;
  type: string;
  status: 'running' | 'stopped' | 'starting' | 'error' | 'unknown';
  port?: number;
  memory_gb?: number;
  uptime_seconds?: number;
  idle_seconds?: number;
}

export interface ServiceStatus {
  service_id: string;
  name: string;
  description: string;
  icon: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  gateway: GatewayStatus;
  workers: WorkerStatus[];
}

export interface MemoryStatus {
  total_gb: number;
  available_gb: number;
  used_gb: number;
  used_percent: number;
}

export interface WorkerManagerStatus {
  service_id: string;
  reachable: boolean;
  workers_count: number;
  memory?: MemoryStatus;
  error?: string;
}

export interface SystemOverview {
  timestamp: number;
  services_count: number;
  healthy_services: number;
  unhealthy_services: number;
  total_workers: number;
  running_workers: number;
  worker_managers: WorkerManagerStatus[];
}

export interface WorkerActionResponse {
  success: boolean;
  message: string;
  worker_alias: string;
  action: string;
  data?: Record<string, unknown>;
}

// WebSocket message types
export interface WSMessage {
  type: string;
  timestamp: number;
  data: unknown;
}

export interface WSServiceUpdate extends WSMessage {
  type: 'services_update';
  data: ServiceStatus;
}

export interface WSWorkerUpdate extends WSMessage {
  type: 'workers_update';
  data: WorkerStatus;
}

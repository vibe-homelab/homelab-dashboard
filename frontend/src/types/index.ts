// GPU Types
export interface GpuInfo {
  gpu_id: number;
  status: 'free' | 'allocated' | 'starting' | 'error';
  allocated_to: string | null;
  allocated_at: string | null;
}

export interface GpuPoolState {
  gpus: GpuInfo[];
  total: number;
  free: number;
  allocated: number;
}

// Queue Types
export interface QueueEntry {
  id: string;
  service_id: string;
  status: 'pending' | 'dispatched' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'timeout';
  created_at: string;
  dispatched_at: string | null;
  completed_at: string | null;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown> | null;
  error_message: string | null;
  position: number | null;
  gpu_ids: number[];
}

export interface QueueState {
  entries: QueueEntry[];
  total_pending: number;
  total_processing: number;
  total_completed: number;
}

// Service Types
export interface ServiceState {
  service_id: string;
  display_name: string;
  status: 'stopped' | 'starting' | 'healthy' | 'unhealthy' | 'stopping' | 'error';
  gpu_ids: number[];
  port: number | null;
  pid: number | null;
  container_id: string | null;
  started_at: string | null;
  last_request_at: string | null;
  active_requests: number;
  total_requests_served: number;
  idle_seconds: number;
  error_message: string | null;
  // Extended fields from API
  description?: string;
  icon?: string;
  gpu_requirement?: {
    min_gpus: number;
    max_gpus: number;
    exclusive: boolean;
  };
  idle_timeout_sec?: number;
}

// System Overview
export interface SystemOverview {
  timestamp: number;
  gpu: {
    total: number;
    free: number;
    allocated: number;
  };
  queue: {
    pending: number;
    processing: number;
    completed: number;
  };
  services: {
    total: number;
    running: number;
    stopped: number;
  };
}

// WebSocket Types
export interface WSMessage {
  type: string;
  timestamp: number;
  data: unknown;
}

export interface FullStateData {
  gpus: GpuPoolState;
  queue: QueueState;
  services: Record<string, ServiceState>;
}

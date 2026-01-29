import type { ServiceStatus, SystemOverview, WorkerActionResponse } from '../types';

const API_BASE = '/api/v1';

export async function fetchServices(): Promise<{ services: ServiceStatus[]; timestamp: number }> {
  const response = await fetch(`${API_BASE}/services`);
  if (!response.ok) {
    throw new Error(`Failed to fetch services: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchService(serviceId: string): Promise<ServiceStatus> {
  const response = await fetch(`${API_BASE}/services/${serviceId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch service: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchSystemOverview(): Promise<SystemOverview> {
  const response = await fetch(`${API_BASE}/system/overview`);
  if (!response.ok) {
    throw new Error(`Failed to fetch system overview: ${response.statusText}`);
  }
  return response.json();
}

export async function spawnWorker(
  serviceId: string,
  alias: string
): Promise<WorkerActionResponse> {
  const response = await fetch(
    `${API_BASE}/services/${serviceId}/workers/${alias}/spawn`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to spawn worker: ${response.statusText}`);
  }
  return response.json();
}

export async function stopWorker(
  serviceId: string,
  alias: string
): Promise<WorkerActionResponse> {
  const response = await fetch(
    `${API_BASE}/services/${serviceId}/workers/${alias}/stop`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to stop worker: ${response.statusText}`);
  }
  return response.json();
}

export async function evictWorker(
  serviceId: string,
  alias: string
): Promise<WorkerActionResponse> {
  const response = await fetch(
    `${API_BASE}/services/${serviceId}/workers/${alias}/evict`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to evict worker: ${response.statusText}`);
  }
  return response.json();
}

export async function stopAllWorkers(serviceId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${API_BASE}/system/worker-manager/${serviceId}/stop-all`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to stop all workers: ${response.statusText}`);
  }
  return response.json();
}

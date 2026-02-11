import type { SystemOverview } from '../types';

const API_BASE = '/api/v1';

export async function fetchServices() {
  const res = await fetch(`${API_BASE}/services`);
  if (!res.ok) throw new Error(`Failed to fetch services: ${res.statusText}`);
  return res.json();
}

export async function fetchSystemOverview(): Promise<SystemOverview> {
  const res = await fetch(`${API_BASE}/system/overview`);
  if (!res.ok) throw new Error(`Failed to fetch overview: ${res.statusText}`);
  return res.json();
}

export async function fetchGpuState() {
  const res = await fetch(`${API_BASE}/system/gpus`);
  if (!res.ok) throw new Error(`Failed to fetch GPUs: ${res.statusText}`);
  return res.json();
}

export async function fetchQueue(includeHistory = false) {
  const res = await fetch(`${API_BASE}/queue?include_history=${includeHistory}`);
  if (!res.ok) throw new Error(`Failed to fetch queue: ${res.statusText}`);
  return res.json();
}

export async function submitRequest(serviceId: string, payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/queue/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service_id: serviceId, payload }),
  });
  if (!res.ok) throw new Error(`Failed to submit: ${res.statusText}`);
  return res.json();
}

export async function cancelRequest(entryId: string) {
  const res = await fetch(`${API_BASE}/queue/${entryId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to cancel: ${res.statusText}`);
  return res.json();
}

export async function stopService(serviceId: string) {
  const res = await fetch(`${API_BASE}/services/${serviceId}/stop`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to stop service: ${res.statusText}`);
  return res.json();
}

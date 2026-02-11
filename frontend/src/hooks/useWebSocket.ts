import { useEffect, useRef, useCallback } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const setFullState = useDashboardStore((s) => s.setFullState);
  const setGpuState = useDashboardStore((s) => s.setGpuState);
  const setQueueState = useDashboardStore((s) => s.setQueueState);
  const setServiceState = useDashboardStore((s) => s.setServiceState);
  const setWsConnected = useDashboardStore((s) => s.setWsConnected);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
      ws.send(JSON.stringify({ type: 'subscribe', channel: 'all' }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case 'full_state':
            setFullState(msg.data);
            break;
          case 'gpu_state_changed':
            setGpuState(msg.data);
            break;
          case 'queue_updated':
            setQueueState(msg.data);
            break;
          case 'service_state_changed': {
            const { service_id, ...rest } = msg.data;
            setServiceState(service_id, { service_id, ...rest });
            break;
          }
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWsConnected(false);
      wsRef.current = null;
      reconnectTimeoutRef.current = window.setTimeout(() => connect(), 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [setFullState, setGpuState, setQueueState, setServiceState, setWsConnected]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return { connected: useDashboardStore((s) => s.wsConnected) };
}

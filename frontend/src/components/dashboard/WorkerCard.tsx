import { useState } from 'react';
import { Play, Square, Trash2, Clock, HardDrive } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import type { WorkerStatus } from '../../types';
import { spawnWorker, stopWorker, evictWorker } from '../../services/api';

interface WorkerCardProps {
  worker: WorkerStatus;
  serviceId: string;
  onRefresh: () => void;
}

export function WorkerCard({ worker, serviceId, onRefresh }: WorkerCardProps) {
  const [loading, setLoading] = useState(false);

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined) return '-';
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const handleSpawn = async () => {
    setLoading(true);
    try {
      await spawnWorker(serviceId, worker.alias);
      onRefresh();
    } catch (e) {
      console.error('Failed to spawn worker:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopWorker(serviceId, worker.alias);
      onRefresh();
    } catch (e) {
      console.error('Failed to stop worker:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleEvict = async () => {
    if (!confirm(`Force evict worker "${worker.name}"?`)) return;
    setLoading(true);
    try {
      await evictWorker(serviceId, worker.alias);
      onRefresh();
    } catch (e) {
      console.error('Failed to evict worker:', e);
    } finally {
      setLoading(false);
    }
  };

  const isRunning = worker.status === 'running';

  return (
    <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h4 className="font-medium text-gray-900">{worker.name}</h4>
          <p className="text-xs text-gray-500">{worker.alias}</p>
        </div>
        <StatusBadge status={worker.status} size="sm" />
      </div>

      {isRunning && (
        <div className="grid grid-cols-2 gap-2 mb-3 text-xs text-gray-600">
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Uptime: {formatDuration(worker.uptime_seconds)}</span>
          </div>
          <div className="flex items-center gap-1">
            <HardDrive className="w-3 h-3" />
            <span>
              {worker.memory_gb !== undefined
                ? `${worker.memory_gb.toFixed(1)} GB`
                : '-'}
            </span>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        {!isRunning ? (
          <button
            onClick={handleSpawn}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
          >
            <Play className="w-3 h-3" />
            Start
          </button>
        ) : (
          <>
            <button
              onClick={handleStop}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 disabled:opacity-50"
            >
              <Square className="w-3 h-3" />
              Stop
            </button>
            <button
              onClick={handleEvict}
              disabled={loading}
              className="flex items-center justify-center px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
              title="Force Evict"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

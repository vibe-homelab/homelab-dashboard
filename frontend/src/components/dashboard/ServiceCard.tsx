import { Brain, Image, Mic, Volume2, Server, Square } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { stopService } from '../../services/api';
import type { ServiceState } from '../../types';

interface ServiceCardProps {
  service: ServiceState;
}

const iconMap: Record<string, typeof Server> = {
  brain: Brain,
  image: Image,
  mic: Mic,
  'volume-2': Volume2,
  server: Server,
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const min = Math.floor(seconds / 60);
  if (min < 60) return `${min}m ${Math.floor(seconds % 60)}s`;
  return `${Math.floor(min / 60)}h ${min % 60}m`;
}

function formatUptime(startedAt: string | null): string {
  if (!startedAt) return '-';
  const ms = Date.now() - new Date(startedAt).getTime();
  return formatDuration(ms / 1000);
}

export function ServiceCard({ service }: ServiceCardProps) {
  const Icon = iconMap[service.icon || 'server'] || Server;
  const isRunning = ['healthy', 'starting'].includes(service.status);

  const handleStop = async () => {
    try {
      await stopService(service.service_id);
    } catch (e) {
      console.error('Failed to stop service:', e);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Icon className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{service.display_name}</h3>
              {service.description && (
                <p className="text-xs text-gray-500">{service.description}</p>
              )}
            </div>
          </div>
          <StatusBadge status={service.status} />
        </div>
      </div>

      <div className="p-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-500">GPUs:</span>{' '}
            <span className="font-medium">
              {service.gpu_ids.length > 0 ? service.gpu_ids.join(', ') : '-'}
            </span>
            {service.gpu_requirement?.exclusive && (
              <span className="text-xs text-orange-500 ml-1">(exclusive)</span>
            )}
          </div>
          <div>
            <span className="text-gray-500">Port:</span>{' '}
            <span className="font-medium">{service.port || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Uptime:</span>{' '}
            <span className="font-medium">{formatUptime(service.started_at)}</span>
          </div>
          <div>
            <span className="text-gray-500">Requests:</span>{' '}
            <span className="font-medium">
              {service.active_requests} active / {service.total_requests_served} total
            </span>
          </div>
          {isRunning && service.idle_timeout_sec && (
            <div className="col-span-2">
              <span className="text-gray-500">Idle:</span>{' '}
              <span className="font-medium">
                {formatDuration(service.idle_seconds)} / {formatDuration(service.idle_timeout_sec)}
              </span>
              <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-yellow-400 rounded-full transition-all"
                  style={{
                    width: `${Math.min(100, (service.idle_seconds / service.idle_timeout_sec) * 100)}%`,
                  }}
                />
              </div>
            </div>
          )}
          {service.error_message && (
            <div className="col-span-2 text-xs text-red-500 bg-red-50 p-2 rounded">
              {service.error_message}
            </div>
          )}
        </div>

        {isRunning && (
          <button
            onClick={handleStop}
            className="mt-3 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
          >
            <Square className="w-3.5 h-3.5" />
            Force Stop
          </button>
        )}
      </div>
    </div>
  );
}

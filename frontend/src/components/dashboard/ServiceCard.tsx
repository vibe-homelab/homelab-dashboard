import { Eye, Mic, Server, RefreshCw } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { WorkerCard } from './WorkerCard';
import type { ServiceStatus } from '../../types';

interface ServiceCardProps {
  service: ServiceStatus;
  onRefresh: () => void;
}

const iconMap: Record<string, typeof Server> = {
  eye: Eye,
  microphone: Mic,
  server: Server,
};

export function ServiceCard({ service, onRefresh }: ServiceCardProps) {
  const Icon = iconMap[service.icon] || Server;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Icon className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{service.name}</h3>
              <p className="text-sm text-gray-500">{service.description}</p>
            </div>
          </div>
          <StatusBadge status={service.status} />
        </div>

        {/* Gateway Status */}
        <div className="mt-3 flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Gateway:</span>
            {service.gateway.reachable ? (
              <span className="text-green-600">
                {service.gateway.latency_ms?.toFixed(0)}ms
              </span>
            ) : (
              <span className="text-red-600">
                {service.gateway.error || 'Unreachable'}
              </span>
            )}
          </div>
          <button
            onClick={onRefresh}
            className="ml-auto p-1 text-gray-400 hover:text-gray-600 rounded"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Workers */}
      <div className="p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">
          Workers ({service.workers.filter((w) => w.status === 'running').length}/
          {service.workers.length})
        </h4>
        <div className="space-y-2">
          {service.workers.map((worker) => (
            <WorkerCard
              key={worker.alias}
              worker={worker}
              serviceId={service.service_id}
              onRefresh={onRefresh}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

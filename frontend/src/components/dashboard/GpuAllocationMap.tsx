import { Cpu } from 'lucide-react';
import { useDashboardStore } from '../../stores/dashboardStore';
import type { GpuInfo } from '../../types';

const statusColors: Record<string, { bg: string; border: string; text: string }> = {
  free: { bg: 'bg-green-50', border: 'border-green-300', text: 'text-green-700' },
  allocated: { bg: 'bg-blue-50', border: 'border-blue-300', text: 'text-blue-700' },
  starting: { bg: 'bg-yellow-50', border: 'border-yellow-300', text: 'text-yellow-700' },
  error: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-700' },
};

function GpuCard({ gpu }: { gpu: GpuInfo }) {
  const colors = statusColors[gpu.status] || statusColors.free;

  return (
    <div className={`${colors.bg} ${colors.border} border-2 rounded-lg p-3 text-center`}>
      <div className="flex items-center justify-center gap-1 mb-1">
        <Cpu className={`w-4 h-4 ${colors.text}`} />
        <span className={`font-bold ${colors.text}`}>GPU {gpu.gpu_id}</span>
      </div>
      <div className={`text-xs font-medium ${colors.text} uppercase`}>
        {gpu.status}
      </div>
      {gpu.allocated_to && (
        <div className="text-xs text-gray-500 mt-1 truncate">
          {gpu.allocated_to}
        </div>
      )}
    </div>
  );
}

export function GpuAllocationMap() {
  const gpus = useDashboardStore((s) => s.gpus);

  if (!gpus) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <h3 className="font-semibold text-gray-900 mb-3">GPU Allocation</h3>
        <div className="animate-pulse h-20 bg-gray-100 rounded" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">GPU Allocation</h3>
        <span className="text-sm text-gray-500">
          {gpus.free}/{gpus.total} free
        </span>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {gpus.gpus.map((gpu) => (
          <GpuCard key={gpu.gpu_id} gpu={gpu} />
        ))}
      </div>
    </div>
  );
}

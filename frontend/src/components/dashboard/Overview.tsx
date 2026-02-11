import { useEffect, useState } from 'react';
import { Server, Cpu, ListOrdered, Activity } from 'lucide-react';
import { fetchSystemOverview } from '../../services/api';
import type { SystemOverview } from '../../types';

export function Overview() {
  const [overview, setOverview] = useState<SystemOverview | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setOverview(await fetchSystemOverview());
      } catch (e) {
        console.error('Failed to load overview:', e);
      }
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!overview) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg p-4 animate-pulse">
            <div className="h-20 bg-gray-200 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const stats = [
    {
      label: 'Services',
      value: overview.services.total,
      sub: `${overview.services.running} running`,
      icon: Server,
      bg: 'bg-blue-100',
      text: 'text-blue-600',
    },
    {
      label: 'GPUs',
      value: `${overview.gpu.free}/${overview.gpu.total}`,
      sub: 'free',
      icon: Cpu,
      bg: 'bg-green-100',
      text: 'text-green-600',
    },
    {
      label: 'Queue',
      value: overview.queue.pending,
      sub: `${overview.queue.processing} processing`,
      icon: ListOrdered,
      bg: 'bg-purple-100',
      text: 'text-purple-600',
    },
    {
      label: 'Completed',
      value: overview.queue.completed,
      sub: 'requests served',
      icon: Activity,
      bg: 'bg-yellow-100',
      text: 'text-yellow-600',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-xs text-gray-400">{stat.sub}</p>
            </div>
            <div className={`p-3 ${stat.bg} rounded-full`}>
              <stat.icon className={`w-6 h-6 ${stat.text}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

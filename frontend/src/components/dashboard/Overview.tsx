import { useEffect, useState } from 'react';
import { Server, Activity, Cpu, HardDrive } from 'lucide-react';
import { MemoryGauge } from './MemoryGauge';
import { fetchSystemOverview } from '../../services/api';
import type { SystemOverview } from '../../types';

export function Overview() {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchSystemOverview();
        setOverview(data);
      } catch (e) {
        console.error('Failed to load overview:', e);
      } finally {
        setLoading(false);
      }
    };

    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
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

  if (!overview) return null;

  const stats = [
    {
      label: 'Services',
      value: overview.services_count,
      subValue: `${overview.healthy_services} healthy`,
      icon: Server,
      color: 'blue',
    },
    {
      label: 'Workers Running',
      value: overview.running_workers,
      subValue: `of ${overview.total_workers} total`,
      icon: Activity,
      color: 'green',
    },
    {
      label: 'Worker Managers',
      value: overview.worker_managers.filter((wm) => wm.reachable).length,
      subValue: `of ${overview.worker_managers.length} total`,
      icon: Cpu,
      color: 'purple',
    },
  ];

  const memory = overview.worker_managers.find((wm) => wm.memory)?.memory;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-white rounded-lg p-4 border border-gray-200"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-xs text-gray-400">{stat.subValue}</p>
            </div>
            <div className={`p-3 bg-${stat.color}-100 rounded-full`}>
              <stat.icon className={`w-6 h-6 text-${stat.color}-600`} />
            </div>
          </div>
        </div>
      ))}

      {/* Memory Card */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm text-gray-500">System Memory</p>
            {memory && (
              <p className="text-2xl font-bold text-gray-900">
                {memory.used_percent.toFixed(0)}%
              </p>
            )}
          </div>
          <div className="p-3 bg-yellow-100 rounded-full">
            <HardDrive className="w-6 h-6 text-yellow-600" />
          </div>
        </div>
        {memory && (
          <MemoryGauge
            usedPercent={memory.used_percent}
            usedGb={memory.used_gb}
            totalGb={memory.total_gb}
          />
        )}
      </div>
    </div>
  );
}
